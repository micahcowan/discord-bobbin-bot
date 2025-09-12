#!/usr/bin/env python3

# This example requires the 'message_content' intent.

import asyncio
import discord
from enum import Enum
import logging
import logging.handlers
import subprocess

intents = discord.Intents(messages=True)
intents.message_content = True
client = discord.Client(intents=intents)
logger = logging.getLogger('bobbin')
msg_logger = logging.getLogger('bobbin.message')

def main():
    tokf = open("token.txt")
    token = tokf.readline().rstrip()

    client.run(token, log_handler=getLogHandler(), root_logger=True)

class Acceptability(Enum):
    UNACCEPTABLE    = 0
    TAGGED          = 1
    MENTIONED       = 2
    DIRECT_MESSAGE  = 3

def getLogHandler():
    handler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    return handler

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

    if "bobbin" in lines[0].lower() or '<@' in lines[0]:
        lines.pop(0)

    if lines[0].strip().startswith("```"):
        lines.pop(0)

    if lines[-1].strip().startswith("```"):
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
    return '```\n' + s + '\n```\n'

async def run_bobbin(input: bytes):

    proc = await asyncio.create_subprocess_shell("bobbin --bot-mode --max-frames 7200",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    (out, err) = await proc.communicate(input)

    return (out + b"\n" + err)

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

    prep = msg_to_bobbin_input(message, message.content)
    outb = await run_bobbin(prep)
    outstr = bobbin_output_to_msg(message, outb)

    if acc == Acceptability.DIRECT_MESSAGE:
        await message.channel.send(outstr)
    else:
        await message.reply(outstr)

########################################

if __name__ == '__main__':
    main()
