import discord
from discord.client import Client

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

    async def on_ready(self):
        chan = self.__get_channel_from_cfg('test_chan')

        print(repr(chan))
        await chan.send('Hello, testing world!')

        # Exit!
        await self.close()
