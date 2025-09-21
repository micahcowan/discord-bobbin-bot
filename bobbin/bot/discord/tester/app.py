import discord
from discord.client import Client
import sys

import testcfg as cfg

# The harness for the tests.
class App(Client):
    def __init__(self, *args, **kargs):
        intents = discord.Intents(
            messages = True,
            message_content = True,
            guilds = True,
        )
        super().__init__(*args, intents=intents, **kargs)
        self.__status = 1 # exit w failure status by default

    def __get_channel_from_cfg(self, name):
        chanSpec = getattr(cfg, name)
        chan = None
        if not isinstance(chanSpec, str):
            # Assume it's an int
            chan = self.get_channel(chanSpec)
        elif '#' in chanSpec:
            [tg, tc] = chanSpec.split(sep='#', maxsplit=1)
            for c in self.get_all_channels():
                if c.guild.name == tg and c.name == tc:
                    chan = c
                    print(f"channel id for {name} is {chan.id}.")
                    break
        else:
            raise Exception(f"{name} is a str but doesn't contain #!")

        return chan

    def run(self, argv : list) -> None:
        super().run(token = cfg.TESTER_TOKEN)
        sys.exit(self.__status)

    async def on_error(self, *args, **kwargs):
        await super().on_error(*args, **kwargs)
        self.__status = 1
        await self.close()

    async def on_ready(self):
        chan = self.__get_channel_from_cfg('test_chan')

        await chan.send('Hello, testing world!')

        # Exit!
        self.__status = 0
        await self.close()
