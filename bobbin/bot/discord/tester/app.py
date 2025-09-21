import asyncio
from asyncio import Future
import sys
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

import discord
from discord.client import Client

from .tests import run_tests

import testcfg as cfg

from ..util.types import DiscordChannel

class ConcurrentSendTestException(Exception):
    pass

# The harness for the tests.
class App(Client):
    future: Optional[Future[Optional[str]]] = None

    def __init__(self, *args: Any, **kargs: Any) -> None:
        intents: discord.Intents = discord.Intents(
            messages = True,
            message_content = True,
            guilds = True,
        )
        super().__init__(*args, intents=intents, **kargs)
        self.__status: int = 1 # exit w failure status by default

    def __get_channel_from_cfg(self, name: str) -> DiscordChannel:
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

    def run(self, /, argv : list[str]) -> None: # type: ignore[override]
        super().run(token = cfg.TESTER_TOKEN)
        sys.exit(self.__status)

    async def on_error(self, *args: Any, **kwargs: Any) -> None:
        await super().on_error(*args, **kwargs)
        self.__status = 1
        await self.close()

    async def send_test(self, msg: str, timeout: int = 5) -> str | None:
        chan: DiscordChannel  = self.__get_channel_from_cfg('test_chan')
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

        async def delay() -> None:
            await asyncio.sleep(timeout)
            if self.future is not None and not self.future.done():
                self.future.set_result(None)
                self.future = None

        asyncio.create_task(delay())

        return await future

    async def on_ready(self) -> None:
        await run_tests(self)

        # Exit!
        self.__status = 0
        await self.close()
