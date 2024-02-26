import discord
from discord.ext import commands
import requests
from dataclasses import dataclass
import os
import logging.handlers
from string import Template

import fitz

from eligibility_checking.check import get_grades, Eligibility


LOGGER = logging.getLogger('transcript_bot')
LOGGER.setLevel(logging.INFO)

HANDLER = logging.handlers.RotatingFileHandler(
    filename='log.jsonl',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,
    backupCount=1
)

FORMATTER = logging.Formatter(
    '{"level": "%(levelname)s", "name": "%(name)s", "date": "%(asctime)s", "message": "%(message)s"}',
    "%m/%d/%Y %I:%M:%S %p %Z"
)
HANDLER.setFormatter(FORMATTER)
LOGGER.addHandler(HANDLER)

DISCLAIMER = 'If you believe this is an error, please reach out to an officer'

STATUS_MESSAGES = {
    Eligibility.ELIGIBLE: 'Eligible :white_check_mark:',
    Eligibility.PROBATION: f'Probation :warning: \n {DISCLAIMER}',
    Eligibility.INELIGIBLE: f'Ineligible :no_entry_sign: \n {DISCLAIMER}'
}


@dataclass
class DirectMessage:

    full_name: str
    username: str
    message: str

    def __repr__(self):
        return f'Transcript received!\n' \
               f'Name: {self.full_name}\n' \
               f'Username: {self.username}\n' \
               f'Status: {self.message}'


CHANNEL_ID = int(os.environ['CHANNEL_ID'])
BOT_API_KEY = os.environ['BOT_API_KEY']


def main():

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix='+', intents=intents)

    @bot.event
    async def on_ready():
        LOGGER.info('Bot is online')

    @bot.event
    async def on_message(message: discord.message.Message):

        if message.author == bot.user:
            return
        if len(message.attachments) == 0:
            await message.channel.send('please send a PDF')
            return
        if len(message.attachments) > 1:
            await message.channel.send('please only send one PDF')
            return

        channel = bot.get_channel(CHANNEL_ID)

        url = message.attachments[0].url
        response = requests.get(url)

        doc = fitz.open(stream=response.content, filetype='pdf')
        grades = get_grades(doc)
        try:
            msg = STATUS_MESSAGES[grades.eligibility]
        except KeyError:
            await message.channel.send('eligibility not properly calculated, please reach out to an officer')
            return

        with open('direct_message_template.txt', 'r') as file:
            src = Template(file.read())
            direct_message = src.substitute({
                'full_name': grades.full_name,
                'student_type': grades.student_type.name.title(),
                'username': message.author,
                'status': msg
            })

        await message.channel.send(direct_message)
        await channel.send(f'-----\n{direct_message}')

        LOGGER.info(f'transcript received from {grades.full_name} ({message.author}). '
                    f'{grades.student_type=}, {grades.eligibility=}')

    bot.run(BOT_API_KEY)


if __name__ == '__main__':

    main()
