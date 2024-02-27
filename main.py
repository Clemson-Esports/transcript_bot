"""
Script for launching the bot
"""

from dataclasses import dataclass
import os
import logging.handlers
from string import Template

import discord
from discord.ext import commands
import fitz

from eligibility_checking.check import get_grades, Eligibility

# metadata
__version__ = "2.0.0"
__last_updated__ = "02/26/2024"
__authors__ = ["Jacob Jeffries (haydnsdad)"]

# create a logger
LOGGER = logging.getLogger(f"transcript_bot_{__version__}")
LOGGER.setLevel(logging.INFO)

HANDLER = logging.handlers.RotatingFileHandler(
    filename="log.jsonl", encoding="utf-8", maxBytes=32 * 1024 * 1024, backupCount=1
)

# JSON Lines format
FORMATTER = logging.Formatter(
    '{"level": "%(levelname)s", "message": "%(message)s", "date": "%(asctime)s", "name": "%(name)s"}',
    "%m/%d/%Y %I:%M:%S %p %Z",
)
HANDLER.setFormatter(FORMATTER)
LOGGER.addHandler(HANDLER)

DISCLAIMER = "If you believe this is an error, please create a ModMail ticket"

# status messages for each eligibility type
STATUS_MESSAGES = {
    Eligibility.ELIGIBLE: "Eligible :white_check_mark:",
    Eligibility.PROBATION: f"Probation :warning: \n {DISCLAIMER}",
    Eligibility.INELIGIBLE: f"Ineligible :no_entry_sign: \n {DISCLAIMER}",
}


@dataclass
class DirectMessage:

    """
    small class for creating a direct message
    """

    full_name: str
    username: str
    message: str

    def __str__(self):
        return (
            f"Transcript received!\n"
            f"Name: {self.full_name}\n"
            f"Username: {self.username}\n"
            f"Status: {self.message}"
        )


# hidden variables - bot sends eligibility messages to CHANNEL_ID and to user DMs, API key defines bot
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
BOT_API_KEY = os.environ["BOT_API_KEY"]


def main():

    # initialize the bot
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="+", intents=intents)

    # log when the bot has been turned on
    @bot.event
    async def on_ready():
        LOGGER.info("the bot has been turned online")

    # perform various types of events when a message is sent
    @bot.event
    async def on_message(message: discord.message.Message):

        # ignore the message if the message is sent by the bot
        if message.author == bot.user:
            return

        # send out the version info when prompted
        if message.content.startswith("+version"):
            await message.channel.send(
                f"My version number is {__version__}, last updated {__last_updated__}"
            )
            return

        # respond to a ping
        if message.content.startswith("+ping"):
            await message.channel.send(
                f"pong :ping_pong: ({bot.latency * 1.0e+3:.1f} ms)"
            )
            return

        # send out the authors when prompted
        if message.content.startswith("+authors"):
            await message.channel.send(f"My authors are {', '.join(__authors__)}")
            return

        # do not attempt to read attachments unless channel is a DM channel
        if not isinstance(message.channel, discord.channel.DMChannel):
            return

        # if no attachments added, log the contents
        if len(message.attachments) == 0:
            await message.channel.send("please send a PDF")
            LOGGER.error(
                f"{message.author} sent a message without an attachment: {message.content}"
            )
            return
        # if more than one attachment added, log the number of attachments
        if len(message.attachments) > 1:
            await message.channel.send("please only send one PDF")
            LOGGER.error(
                f"{message.author} sent {len(message.attachments):.0f} attachments"
            )
            return

        # open the attachment as a stream of bytes
        stream = await message.attachments[0].read()
        doc = fitz.open(stream=stream, filetype="pdf")

        # if not a PDF, log that the user tried to send a non-PDF document
        if "PDF" not in doc.metadata["format"]:
            await message.channel.send("document is not recognized as a PDF")
            LOGGER.error(
                f"{message.author} sent a non-PDF document with name {message.attachments[0].filename}"
            )
            return

        # try to calculate grades, send user traceback if something not currently checked breaks
        try:
            grades = get_grades(doc)
        except Exception as e:
            await message.channel.send(
                "grade information not properly found in document. please create a ModMail "
                "ticket with the message below"
            )
            await message.channel.send(f"```\n{e}\n```")
            LOGGER.error(f"{message.author}'s query threw error '{e}'")
            return

        # get the appropriate status message for the corresponding eligibility
        msg = STATUS_MESSAGES[grades.eligibility]

        # create and send the right DM from the pre-written template
        with open("direct_message_template.txt", "r") as file:
            src = Template(file.read())
            direct_message = src.substitute(
                {
                    "full_name": grades.full_name,
                    "student_type": grades.student_type.name.title(),
                    "username": message.author,
                    "status": msg,
                }
            )
        await message.channel.send(direct_message)

        # also send the message to a channel the admin team can see
        channel = bot.get_channel(CHANNEL_ID)
        await channel.send(f"-----\n{direct_message}")

        # log the transcript submission and the corresponding eligibility
        LOGGER.info(
            f"transcript received from {grades.full_name} ({message.author}). {grades.eligibility=}"
        )

    # run the bot
    bot.run(BOT_API_KEY)


if __name__ == "__main__":

    main()
