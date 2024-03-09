"""
Script for launching the bot
"""

import os
import logging.handlers
from string import Template
from io import BytesIO

import discord
from discord.ext import commands
from dotenv import load_dotenv
from hotpdf import HotPdf
from pdfminer.pdfparser import PDFSyntaxError

from eligibility_checking.check import Eligibility, get_grades

# metadata
__version__ = "2.2.0"
__last_updated__ = "03/07/2024"
__authors__ = ["Jacob Jeffries (haydnsdad)", "Jay Adusumilli (therealj4y)"]

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

# Get the environment variables from the .env file.
load_dotenv("bot.env")

# hidden variables - bot sends eligibility messages to CHANNEL_ID and to user DMs, API key defines bot
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
BOT_API_KEY = str(os.getenv("BOT_API_KEY"))

# README link for tutorial
README = "https://github.com/Clemson-Esports/transcript_bot/blob/main/README.md"

# victim getting pinged... poor guy
PONG_VICTIM = "<@289901600078692352>"


def main():

    # initialize the bot
    intents = discord.Intents.default()
    intents.message_content = True

    help_command = commands.DefaultHelpCommand(
        no_category="Commands",
        sort_commands=False,
    )
    bot = commands.Bot(command_prefix="+", intents=intents, help_command=help_command)

    # log when the bot has been turned on
    @bot.event
    async def on_ready():
        LOGGER.info("the bot has been turned online")

    # +tutorial command, redirects user to README.md in repo
    @bot.command(help="sends link to transcript submission tutorial")
    async def tutorial(ctx):
        await ctx.reply(f"See the transcript submission tutorial at {README}")

    # +version command
    @bot.command(help="prints out version")
    async def version(ctx):
        await ctx.reply(
            f"My version number is {__version__}, last updated {__last_updated__}"
        )

    # +ping command
    @bot.command(help="pings the bot to see if it's online")
    async def ping(ctx):
        await ctx.reply(f"pong :ping_pong: ({bot.latency * 1.0e+3:.1f} ms)")

    # +pong command (pings don 😂)
    @bot.command(help="does something devious ")
    async def pong(ctx):
        await ctx.reply(f"eat shit {PONG_VICTIM}")

    # +authors command
    @bot.command(help="prints out authors")
    async def authors(ctx):
        await ctx.reply(f"My authors are {', '.join(__authors__)}")

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.errors.CommandNotFound):
            await ctx.reply(
                f"Not a valid command :frowning:\nSend '{bot.command_prefix}help' to see valid commands"
            )
        else:
            raise error

    # perform various types of events when a message is sent
    @bot.event
    async def on_message(message: discord.message.Message):

        # on_message blocks prior commands without this line
        await bot.process_commands(message)

        if bot.user.mentioned_in(message):
            await message.reply(
                f"Send '{bot.command_prefix}help' to see valid commands"
            )

        # ignore the message if the message is sent by the bot or if not in a DM
        is_sent_by_bot = message.author == bot.user
        is_dm = isinstance(message.channel, discord.channel.DMChannel)
        if is_sent_by_bot or not is_dm:
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

        try:
            doc = HotPdf(BytesIO(stream))
        except PDFSyntaxError:
            await message.channel.send(
                "document not detected as PDF! if you believe this is an error, please create a ModMail ticket"
            )
            LOGGER.error(
                f"{message.author} sent a non-PDF attachment named {message.attachments[0].filename}"
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
