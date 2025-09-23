import asyncio
from asyncio import Future, Task
import sys
from sys import stderr
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

import discord
from discord.client import Client

from .tests import Test, run_tests

import testcfg as cfg

from ..util.types import DiscordChannel

class ConcurrentSendTestException(Exception):
    pass

# The harness for the tests.
class App(Client):
    future: Optional[Future[Optional[str]]] = None
    timeout_task: Task[None]|None = None

    def __init__(self, *args: Any, **kargs: Any) -> None:
        intents: discord.Intents = discord.Intents(
            messages = True,
            message_content = True,
            guilds = True,
        )
        super().__init__(*args, intents=intents, **kargs)
        self.__status: int = 1 # exit w failure status by default

    def get_channel_from_cfg(self, name: str) -> DiscordChannel:
        chanSpec: Union[str, int] = getattr(cfg, name)
        chan: DiscordChannel
        if not isinstance(chanSpec, str):
            # Assume it's an int
            chan = self.get_channel(chanSpec)
        elif '#' in chanSpec:
            tg: str
            tc: str
            [tg, tc] = chanSpec.split(sep='#', maxsplit=1)
            c: DiscordChannel
            for c in self.get_all_channels():
                if c.guild.name == tg and c.name == tc:
                    chan = c
                    print(f"channel id for {name} is {chan.id}.")
                    break
        else:
            raise Exception(f"{name} is a str but doesn't contain #!")

        return chan

    def is_bot_under_test(self, user: discord.User | discord.Member) -> bool:
        match : int|str = cfg.test_user
        if isinstance(match, str):
            if match == user.name:
                print(f"user id for {match} is {user.id}.")
                return True
            else:
                return False
        else: # assume
            return match == user.id

    def run(self, /, argv : list[str]) -> None: # type: ignore[override]
        super().run(token = cfg.TESTER_TOKEN)
        sys.exit(self.__status)

    async def on_error(self, *args: Any, **kwargs: Any) -> None:
        await super().on_error(*args, **kwargs)
        self.__status = 1
        await self.close()

    async def send_test(
                self, msg: str, /,
                channel: str = 'test_chan',
                timeout: float = 2,
            ) -> str | None:

        if channel != 'dm':
            chan: DiscordChannel  = self.get_channel_from_cfg(channel)
            await chan.send(msg) # type: ignore # (.send)

        if self.future is not None:
            raise ConcurrentSendTestException()

        # Now, send_test must not return until either:
        #  (a) a channel message from the bot is received, which will be
        #      then be returned, or
        #  (b) a timeout occurs, in which case None is returned
        future: Future[Optional[str]] = (
            asyncio.get_running_loop().create_future())
        self.future = future

        async def delay(tmout: float) -> None:
            await asyncio.sleep(tmout)
            if self.future is not None and not self.future.done():
                self.future.set_result(None)
                self.future = None

        self.timeout_task = asyncio.create_task(delay(timeout))

        return await future

    async def on_ready(self) -> None:
        await run_tests(self)

        # Exit!
        t = Test.tally
        t.report()
        if t.failed_any():
            self.__status = 1
        else:
            self.__status = 0
        await self.close()

    async def on_message(self, msg: discord.Message) -> None:
        if msg.author == self.user:
            return
        if self.future is None:
            return
        if not self.is_bot_under_test(msg.author):
            return

        self.future.set_result(msg.content)
        self.future = None
        if self.timeout_task is not None:
            self.timeout_task.cancel()
            self.timeout_task = None
