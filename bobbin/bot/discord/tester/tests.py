from __future__ import annotations

from enum import Enum
from sys import stderr
from typing import Any, Optional, TYPE_CHECKING

from .configs import configs, Basic, Config

import testcfg as cfg

if TYPE_CHECKING:
    from .app import App
    import discord
else:
    App = None

class TestAlreadyRunException(Exception):
    def __init__(self, test: Test):
        self.__test__ = test

class TS(Enum):
    PASS  = 0
    FAIL  = 1
    XFAIL = 2

    def label(self) -> str:
        return ['PASS', 'FAIL', 'XFAIL'][self.value]
    def color_label(self) -> str:
        # ANSI color sequences
        colors: list[str] = [
            '\033[1;32m',   # PASS: Bold Green
            '\033[31m',     # FAIL: Red
            '\033[1;34m',   # XFAIL: Bold Blue
        ]
        return f'{colors[self.value]}{self.label()}\033[m'

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


    async def run(self, client: App, config: Config) -> TS:
        if hasattr(self, 'status'):
            raise TestAlreadyRunException(self)
        self.status = TS.FAIL

        print(f'  {self.desc:70}', end='', file=stderr)

        rsp: str|None = await client.send_test(
            self.input.format(tag = config.attract_tag)
        )

        if rsp == self.expected:
            self.status = TS.PASS

        print(f'[{self.status.color_label()}]\n', file=stderr)

        if self.status != TS.PASS:
            print('*** NOT EXPECTED ***', file=stderr)
            print(f'Expected:\n{repr(self.expected)}\nGot:\n{repr(rsp)}\n',
                  file=stderr)

        return self.status

async def run_tests(client: App) -> None:
    for tcfg in configs:
        print(f'Running {tcfg.__name__} tests:', file=stderr)
        await tcfg.run_tests(client)


##################### TEST DEFINITIONS #####################

using_config = Basic

Test(
    desc = 'hello world',
    input = '{tag}\n? "Hello, world!!',
    expected = '```\nHello, world!!\n```',
)
