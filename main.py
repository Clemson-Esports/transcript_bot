import discord
from discord.ext import commands
import requests
from dataclasses import dataclass
import os
import logging.handlers
from string import Template
import fitz

from eligibility_checking.check import get_grades, Eligibility


__version__ = '2.0.0'
__last_updated__ = '02/26/2024'
__authors__ = [
    'Jacob Jeffries (haydnsdad)'
]


LOGGER = logging.getLogger(f'transcript_bot_{__version__}')
LOGGER.setLevel(logging.INFO)

HANDLER = logging.handlers.RotatingFileHandler(
    filename='log.jsonl',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,
    backupCount=1
)

FORMATTER = logging.Formatter(
    '{"level": "%(levelname)s", "message": "%(message)s", "date": "%(asctime)s", "name": "%(name)s"}',
    "%m/%d/%Y %I:%M:%S %p %Z"
)
HANDLER.setFormatter(FORMATTER)
LOGGER.addHandler(HANDLER)

DISCLAIMER = 'If you believe this is an error, please create a ModMail ticket'

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

    def __str__(self):
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
        LOGGER.info('the bot has been turned online')

    @bot.event
    async def on_message(message: discord.message.Message):

        if message.author == bot.user:
            return

        if message.content.startswith('+version'):
            await message.channel.send(f'My version number is {__version__}, last updated {__last_updated__}')
            return

        if message.content.startswith('+ping'):
            await message.channel.send(f'pong :ping_pong: ({bot.latency * 1.0e+3:.1f} ms)')
            return

        if message.content.startswith('+authors'):
            await message.channel.send(f"My authors are {', '.join(__authors__)}")
            return

        if not isinstance(message.channel, discord.channel.DMChannel):
            return

        if len(message.attachments) == 0:
            await message.channel.send('please send a PDF')
            LOGGER.error(f'{message.author} sent a message without an attachment: {message.content}')
            return
        if len(message.attachments) > 1:
            await message.channel.send('please only send one PDF')
            LOGGER.error(f'{message.author} sent {len(message.attachments):.0f} attachments')
            return

        channel = bot.get_channel(CHANNEL_ID)

        url = message.attachments[0].url
        response = requests.get(url)

        doc = fitz.open(stream=response.content, filetype='pdf')
        if 'PDF' not in doc.metadata['format']:
            await message.channel.send('document is not recognized as a PDF')
            LOGGER.error(f'{message.author} sent a non-PDF document with name {message.attachments[0].filename}')
            return
        try:
            grades = get_grades(doc)
        except Exception as e:
            await message.channel.send('grade information not properly found in document. please create a ModMail '
                                       'ticket with the message below')
            await message.channel.send(f'```\n{e}\n```')
            LOGGER.error(f"{message.author}'s query threw error '{e}'")
            return

        msg = STATUS_MESSAGES[grades.eligibility]

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

        LOGGER.info(f'transcript received from {grades.full_name} ({message.author}). {grades.eligibility=}')

    bot.run(BOT_API_KEY)


if __name__ == '__main__':

    main()
