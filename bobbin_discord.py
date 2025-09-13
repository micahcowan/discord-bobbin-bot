#!/usr/bin/env python3

# This example requires the 'message_content' intent.

import asyncio
import atexit
import discord
import discord.utils
from enum import Enum
import logging
import logging.handlers
import os
import re
import subprocess
import sys

MSG_MAX_BYTES = 1900
MSG_MAX_LINES = 30

intents = discord.Intents(messages=True)
intents.message_content = True
client = discord.Client(intents=intents)
logger = logging.getLogger('bobbin')
ann_logger = logging.getLogger('bobbin.message')
msg_logger = logging.getLogger('bobbin.message.content')

def getDiscordLogHandler():
    try:
        os.mkdir('logs')
    except FileExistsError:
        pass # that's fine

    handler = logging.handlers.RotatingFileHandler(
        filename='logs/discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    return handler

discord.utils.setup_logging(handler=getDiscordLogHandler(), root=True)

def main():
    tokf = open("token.txt")
    token = tokf.readline().rstrip()

    logger.info('BOBBIN BOT STARTING')
    def bleat():
        logger.info('BOBBIN BOT SHUTTING DOWN')
    atexit.register(bleat)
    client.run(token)

class Acceptability(Enum):
    UNACCEPTABLE    = 0
    TAGGED          = 1
    MENTIONED       = 2
    DIRECT_MESSAGE  = 3

def get_msg_acceptability(message: discord.Message) -> Acceptability:
    content = message.content.strip()
    if isinstance(message.channel, discord.channel.DMChannel):
        return Acceptability.DIRECT_MESSAGE
        #await message.channel.send(f"direct messaging!  \"{content}\"")
    elif client.user in message.mentions:
        return Acceptability.MENTIONED
        #await message.reply(f"Replying: \"{content}\"")
    elif content.startswith("!bobbin"):
        return Acceptability.TAGGED
        #await message.reply(f"Attract: \"{content}\"")
    return Acceptability.UNACCEPTABLE

def msg_to_bobbin_input(message : discord.Message, inp: str) -> bytes:
    lines = inp.splitlines(keepends=True)

    if "!bobbin" in lines[0].lower() or '<@' in lines[0]:
        lines.pop(0)

    if len(lines) > 0 and lines[0].strip().startswith("```"):
        lines.pop(0)

    if len(lines) > 0 and lines[-1].strip().startswith("```"):
        lines.pop()

    unencoded = ''.join(lines)
    encoded = None
    try:
        encoded = unencoded.encode('us-ascii')
    except UnicodeEncodeError:
        logger.warn(f'Message #{message.id} contained non-ASCII chars! Removed invalid chars')
        encoded = unencoded.encode('us-ascii', errors='ignore')
    if encoded[-1] != b'\n'[-1]:
        encoded += b'\n'
    return encoded

def bobbin_output_to_msg(message : discord.Message, outb : bytes) -> str:
    s = None
    try:
        s = outb.decode('us-ascii')
    except UnicodeEncodeError:
        logger.warn(f"bobbin's response to message #{message.id} failed to encode to ASCII?! Discarding.")
        return "[[could not process output]]"
    if s.strip() == '':
        return "[[script produced no output]]"

    s = re.sub('[`]{3}', '`\u200C`\u200C`', s)

    # Check that the output isn't huge
    trunc = False
    if s.count('\n') > MSG_MAX_LINES:
        trunc = True
        lines = s.splitlines(keepends=True)
        s = ''.join(lines[0:MSG_MAX_LINES])
    if len(s) > MSG_MAX_BYTES:
        trunc = True
        s = s[0:MSG_MAX_BYTES] + '\n'

    s = '```\n' + s + '```\n'
    if trunc:
        s += '[[Output was truncated]]'
    return s

async def run_bobbin(input: bytes):
    # The purpose of the `head` command in the shell pipeline below,
    # is only to prevent storage of exxtremely long output from bobbin (and to
    # terminate bobbin (via SIGPIPE) if it produces so much).
    #  It is NOT intended to truncate output to an actually suitable size:
    # we want to detect that elsewhere, so that we can then report the
    # truncation to the user (and log)
    proc = await asyncio.create_subprocess_shell(
        "bobbin --bot-mode --max-frames 7200 | head -n 500 -c 5000",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    (out, err) = await proc.communicate(input)

    return (out + b"\n" + err)

async def apologize(acc : Acceptability, message : discord.Message):
    outstr = "[[Sorry, this bot experienced an internal error]]"
    if acc == Acceptability.DIRECT_MESSAGE:
        ann_logger.info(f"Apologizing to {message.author.name}'s DM"
                        + f" (msgid {message.id}).")
        await message.channel.send(outstr)
    else:
        ann_logger.info(f"Apologizing to {message.author.name},"
                        + f"msgid {message.id}.")
        await message.reply(outstr)

def log_received(message : discord.Message, acc : Acceptability):
    f : str = ""
    msgid = message.id
    user = message.author.name
    uid = message.author.id
    cname = ""
    if not hasattr(message, 'channel'):
        cname = "None"
    elif hasattr(message.channel, 'name'):
        cname = message.channel.name
    else:
        cname = f"#{message.channel.id}"

    if acc == Acceptability.TAGGED:
        f = f"We were tagged (!bobbin) in msgid {msgid} by user {user} ({uid}) on {message.guild.name}#{cname}."
    elif acc == Acceptability.MENTIONED:
        f = f"We were mentioned in msgid {msgid} by user {user} ({uid}) on {message.guild.name}#{cname}."
    elif acc == Acceptability.DIRECT_MESSAGE:
        f = f"User {user} ({uid}) sent us a direct message (id {msgid})."
    ann_logger.info(f)

@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    acc = get_msg_acceptability(message)
    if acc == Acceptability.UNACCEPTABLE:
        return

    log_received(message, acc)

    try:
        prep = msg_to_bobbin_input(message, message.content)
        outb = await run_bobbin(prep)
        outstr = bobbin_output_to_msg(message, outb)

        if acc == Acceptability.DIRECT_MESSAGE:
            ann_logger.info(f"Replying to {message.author.name}'s DM (msgid {message.id}).")
            await message.channel.send(outstr)
        else:
            ann_logger.info(f"Replying to {message.author.name}, msgid {message.id}.")
            await message.reply(outstr)
    except Exception as e:
        await apologize(acc, message)
        raise e

########################################

if __name__ == '__main__':
    main()
