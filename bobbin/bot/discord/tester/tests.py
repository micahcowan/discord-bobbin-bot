from enum import Enum
import sys
from typing import Optional, TYPE_CHECKING

from .configs import configs, Foo

if TYPE_CHECKING:
    from .app import App
    import discord

class TestAlreadyRunException(Exception):
    def __init__(self, test: Test):
        self.__test__ = test

class TS(Enum):
    PASS  = 0
    FAIL  = 1
    XFAIL = 2

class Test:
    def __init__(
            self,
            desc: str,
            input: str,
            expected: Optional[str] = None,
            xfail: bool = False,
        ):
        self.desc = desc
        self.input = input
        self.expected = expected

        global using_config
        self.config = using_config
        using_config.register(self)

    def listen(self, msg: discord.Message) -> None:
        pass # XXX

    async def run(self, client: App) -> TS:
        if hasattr(self, 'status'):
            raise TestAlreadyRunException(self)
        self.status = TS.FAIL
        def listener(msg: discord.Message) -> None:
            self.listen(msg)

        await client.send_good(self.input, listener) # may change status
        return self.status


using_config = Foo

Test(
    desc = 'hello world',
    input = '!bobbin\n? "Hello, world!',
    expected = '```\nHello, world!!\n```\n',
)

async def run_tests(client: App) -> None:
    for tcfg in configs:
        print(f'Running {tcfg.__name__} tests:', file=sys.stderr)
        tcfg.run_tests(client)
