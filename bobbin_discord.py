#!/usr/bin/env python3

#   discord-bobbin-bot
#     github.com/micahcowan/discord-bobbin-bot
#     by Micah J Cowan <micah@addictivecode.org>
#
#   discord-bobbin-bot is licensed under the MIT License
#   https://opensource.org/license/mit

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
from typing import Optional

from config import Config

class __Config(Config):
    def __init__(self):
        if not hasattr(self, 'attract_tag'):
            self.attract_tag = '!bobbin'
        super().__init__()

    def channelOkay(self, chanName):
        "Returns True if the fully-qualified channel name (server#channel)"
        " is approved for messages."
        [guildName, _] = chanName.split(sep='#', maxsplit=1)
        return (chanName in self.acceptable_channels
                or f'{guildName}#*' in self.acceptable_channels)

cfg = __Config()

MSG_MAX_BYTES = 1900
MSG_MAX_LINES = 30

def getDiscordLogHandler(fname):
    os.makedirs( os.path.dirname(fname), exist_ok=True )

    handler = logging.handlers.RotatingFileHandler(
        filename=fname,
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}]'
                                  ' {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    return handler

discord.utils.setup_logging(handler=getDiscordLogHandler('logs/discord.log'), root=True)

intents = discord.Intents(
    messages = True,
    message_content = True,
    guilds = True,
)
client = discord.Client(intents=intents)
logger = logging.getLogger('bobbin')
msg_accept_logger = logging.getLogger('bobbin.message.incoming.accept')
msg_reject_logger = logging.getLogger('bobbin.message.incoming.reject')
msg_out_logger = logging.getLogger('bobbin.message.outgoing')
apology_logger = logging.getLogger('bobbin.message.outgoing.apology')

msg_logger = logging.getLogger('bobbin.message.content')
msg_logger.propagate = False
msg_logger.setLevel(logging.CRITICAL)
chan_in_logger = logging.getLogger('bobbin.message.content.channel.incoming')
chan_out_logger = logging.getLogger('bobbin.message.content.channel.outgoing')


dm_log_handler = getDiscordLogHandler('logs/msgs/dms.log')

dm_in_logger = logging.getLogger('bobbin.message.content.dm.incoming')
dm_in_logger.addHandler(dm_log_handler)
dm_in_logger.setLevel(logging.DEBUG)  # XXX s/b handled by cfg
dm_out_logger = logging.getLogger('bobbin.message.content.dm.outgoing')
dm_out_logger.addHandler(dm_log_handler)
dm_out_logger.setLevel(logging.DEBUG) # XXX s/b handled by cfg

adminUser = None
class AdminReportLogHandler(logging.Handler):
    def emit(self, record):
        if not client.is_ready():
            return
        async def continuation():
            global adminUser
            if adminUser is None:
                adminUser = await client.fetch_user(cfg.admin_id)
            if adminUser is None:
                return
            s = self.format(record)
            await adminUser.send(s)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(continuation())
            return
        loop.create_task(continuation())

def setup_admin_reporting():
    if not hasattr(cfg, 'notify_admin'):
        return
    for name in cfg.notify_admin:
        logger = logging.getLogger(name)
        logger.addHandler(AdminReportLogHandler())

setup_admin_reporting()

class Acceptability(Enum):
    def accepted(self):
        return self.value >= self.ACCEPT_LINE.value

    def rejected(self):
        return self.value < self.ACCEPT_LINE.value

    REJ_CHAFF           = 0     # Message, nothing to do with us
    REJ_CHANNEL         = 1     # Not an approved channel
    REJ_USER            = 2     # Blocked user

    ACCEPT_LINE         = 100

    ACC_TAGGED          = 100
    ACC_MENTIONED       = 101
    ACC_DIRECT_MESSAGE  = 102

########################################

def main():
    logger.info('BOBBIN BOT STARTING')
    def bleat():
        logger.info('BOBBIN BOT SHUTTING DOWN')
    atexit.register(bleat)
    client.run(cfg.token)

def get_msg_acceptability(message: discord.Message) -> Acceptability:
    content = message.content.strip()
    acc = Acceptability.REJ_CHAFF

    if isinstance(message.channel, discord.channel.DMChannel):
        acc = Acceptability.ACC_DIRECT_MESSAGE
    elif client.user in message.mentions:
        acc =  Acceptability.ACC_MENTIONED
    elif content.startswith(cfg.attract_tag):
        acc = Acceptability.ACC_TAGGED

    if acc.rejected():
        # The message was never for us.
        return acc

    if acc == Acceptability.ACC_DIRECT_MESSAGE:
        # It's a direct message. If we add user filtering later,
        # we might need to check more; but for now that's an
        # early accept.
        return acc

    # The message is for us; there may still be reasons we
    #  shouldn't handle
    if cfg.channelOkay(f'{message.guild.name}#{message.channel.name}'):
        return acc
    else:
        msg_reject_logger.info(f"{message.guild.name}#{message.channel.name}"
                               f" {message.author.name} ({message.author.id})"
                               f" attract in UNACCEPTABLE channel,"
                               f" msg ({message.id})")
        return Acceptability.REJ_CHANNEL

acceptable_machines = [
    "enhanced", "//e",
    "twoey", "][e", "iie",
    "plus", "+", "][+", "ii+", "twoplus", "autostart", "applesoft", "asoft",
    "original", "][", "ii", "two", "woz", "int", "integer",
]
def parse_params(params: dict, line: str):
    for word in line.split():
        assign = word.split(sep=':', maxsplit=1)
        if len(assign) == 2:
            [name, value] = assign
            if (name == 'm' and len(value) > 0
                    and value.lower() in acceptable_machines):
                params['machine'] = value

def msg_to_bobbin_run_params(message : discord.Message, inp: str) -> dict:
    lines = inp.splitlines(keepends=True)
    params = {}

    if (cfg.attract_tag in lines[0].lower() or '<@' in lines[0]
            or lines[0].startswith('!')):
        parse_params(params, lines[0].strip())
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
    if len(encoded) == 0 or encoded[-1] != b'\n'[-1]:
        encoded += b'\n'

    params['input'] = encoded
    return params

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

async def run_bobbin(input : bytes, machine : str = None) -> bytes:
    # The purpose of the `head` command in the shell pipeline below,
    # is only to prevent storage of exxtremely long output from bobbin (and to
    # terminate bobbin (via SIGPIPE) if it produces so much).
    #  It is NOT intended to truncate output to an actually suitable size:
    # we want to detect that elsewhere, so that we can then report the
    # truncation to the user (and log)
    mstr = ''
    if machine is not None and len(machine) > 0:
        mstr = f'-m {machine}'

    proc = await asyncio.create_subprocess_shell(
        f"bobbin --bot-mode --max-frames 7200 {mstr} | head -n 500 -c 5000",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    (out, err) = await proc.communicate(input)

    return (out + b"\n" + err)

async def apologize(acc : Acceptability, message : discord.Message):
    outstr = "[[Sorry, this bot experienced an internal error]]"
    if acc == Acceptability.ACC_DIRECT_MESSAGE:
        apology_logger.info(f"Apologizing to {message.author.name}'s DM"
                            f" (msgid {message.id}).")
        await message.channel.send(outstr)
    else:
        apology_logger.info(f"Apologizing to {message.author.name},"
                            f"msgid {message.id}.")
        await message.reply(outstr)

def log_received(message : discord.Message, acc : Acceptability):
    f : str = ""
    msgid = message.id
    user = message.author.name
    uid = message.author.id
    guildName = None
    chanName = None
    if acc != Acceptability.ACC_DIRECT_MESSAGE:
        guildName = message.guild.name
        chanName = message.channel.name

    if acc == Acceptability.ACC_TAGGED:
        f = f"{guildName}#{chanName} {user} ({uid}) TAGGED msg ({msgid})"
    elif acc == Acceptability.ACC_MENTIONED:
        f = f"{guildName}#{chanName} {user} ({uid}) MENTIONED msg ({msgid})"
    elif acc == Acceptability.ACC_DIRECT_MESSAGE:
        f = f"DIRECT MESSAGE: {user} ({uid}) msgid {msgid}."
    msg_accept_logger.info(f)

@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    acc = get_msg_acceptability(message)
    if acc.rejected():
        return

    kwArgs = {}
    log_received(message, acc)
    if acc == Acceptability.ACC_DIRECT_MESSAGE:
        dm_in_logger.debug(f'From uid {message.author.id}:\nINPUT\n'
                           f'{message.content}\n')
    else:
        chan_in_logger.debug(f'{message.guild.name}#{message.channel.name},'
                             f' from uid {message.author.id}:\nINPUT\n'
                             f'{message.content}\n')

    try:
        prep : dict = msg_to_bobbin_run_params(message, message.content)
        outb : bytes = await run_bobbin(**prep)
        outstr = bobbin_output_to_msg(message, outb)

        if acc == Acceptability.ACC_DIRECT_MESSAGE:
            msg_out_logger.info(f"Replying to {message.author.name}'s"
                                f" DM (msgid {message.id}).")
            dm_out_logger.debug(f'To uid {message.author.id}:\nOUTPUT\n'
                                f'{outstr}\n')
            await message.channel.send(outstr)
        else:
            msg_out_logger.info(f"Replying to {message.author.name},"
                                f"msgid {message.id}.")
            chan_out_logger.debug(f'{message.guild.name}#'
                                 f'{message.channel.name},'
                                 f' to uid {message.author.id}:\nOUTPUT\n'
                                 f'{outstr}\n')
            await message.reply(outstr)
    except Exception as e:
        await apologize(acc, message)
        raise e

########################################

if __name__ == '__main__':
    main()
