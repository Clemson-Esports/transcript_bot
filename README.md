# Transcript Checker

[![image](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![image](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

---------------------------
### Submission Instructions

1) Log into https://iroar.app.clemson.edu/dashboard/ (with the VPN!!! the bot will likely not work with a transcript dowloaded from cuapps)
2) Select **Student Self-Service**
3) Under **Student Records**, select **Academic Transcript**
4) Select the appropriate level in the **Transcript Level** dropdown menu, and **Web Transcript** in the **Transcript Type** dropdown menu
5) Print this page (the shortcut for this is Ctrl + P)
6) In the **Destination** dropdown menu, click **Save as PDF** (make sure you are **not** clicking "Microsoft Print to PDF", this breaks the PDF reading the bot does)
7) Click save
8) Save the transcript as ``LastName_Transcript.pdf``
9) DM this file to the transcript checking bot. If the bot is online, it should be displayed on the user sidebar as ``Transcript Checker``. You can also type ``+ping`` in any channel if you are having trouble finding the bot, and the bot will respond to you if it's online

We've found that this process works most smoothly if you download the transcript through Google Chrome or Microsoft Edge.

----------------------
### Privacy Disclaimer

We understand and sympathize with any privacy concerns related to submitting personal information to any Discord bot. Once your transcript is submitted, the information that is saved, upon successful parsing, is:

- Your full name
- Your student type (undergraduate/graduate)
- Your username
- Your eligibility (**not** your GPA!<sup>[1](#gpa)</sup>)

This message is sent back to you, as well as into a channel in the Discord server that is visible by any user with Admin privileges (Officers/CEO/some bots). Note that your transcript will **never** be downloaded by our bot - the information is passed as a bytestring.

Upon an unsuccessful parsing, through, more information will be stored:

- If you send an attachment-less message, your message's content and username will be logged.
- If you send more than one attachment, the number of attachments and your username will be logged.
- If you send a non-PDF file, the name of the file and your username will be logged.
- If there is some unaccounted-for error, the error's traceback and your username will be logged.

This logs into a [JSON Lines](https://jsonlines.org/) file on our server, but this file is not necessarily private. This is mostly to keep track of malicious agents, such as those spamming and/or sending malicious files to the bot.

-------------
<a name="gpa"><sup>1</sup></a><span style="font-size:0.8em;">While your GPA is calculated, it is an intermediate variable, and is immediately discarded once the calculations are finished.</span>