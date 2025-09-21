import sys
from typing import TYPE_CHECKING, Any, Callable, Union

import discord
from discord.client import Client

from .tests import run_tests

import testcfg as cfg

if TYPE_CHECKING:
    from ..util.types import DiscordChannel

type Listener = Callable[[discord.Message], None]

# The harness for the tests.
class App(Client):
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

    async def send_good(self, msg: str, lsn: Listener) -> None:
        pass # XXX

    async def on_ready(self) -> None:
        chan = self.__get_channel_from_cfg('test_chan')

        await run_tests(self)

        # Exit!
        self.__status = 0
        await self.close()
