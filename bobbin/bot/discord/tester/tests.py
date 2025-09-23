from __future__ import annotations

from enum import Enum
from sys import stderr
from typing import Any, Optional, TYPE_CHECKING

from ..util import shell_or_die
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

class Tally:
    def __init__(self) -> None:
        self.tallies: dict[TS, int] = {}

    def register(self, result: TS) -> None:
        t = self.tallies
        if result in t:
            t[result] += 1
        else:
            t[result] = 1

    def count(self) -> int:
        t = self.tallies
        c: int = 0
        for r in t:
            c += t[r]
        return c

    def report(self) -> None:
        print(file=stderr)
        print(f'Total tests run: {self.count()}', file=stderr)
        t = self.tallies
        for result in t:
            print(f'  {result.color_label()}: {t[result]}', file=stderr)
        print(file=stderr)
        if TS.FAIL in t:
            print('Tests FAILED.', file=stderr)
        elif TS.XFAIL in t:
            print('Tests succeded (with expected failures).', file=stderr)
        else:
            print('Tests PASSED.', file=stderr)

    def failed_any(self) -> bool:
        return TS.FAIL in self.tallies


class Test:
    tally = Tally()

    def __init__(
            self,
            desc: str,
            /,
            input: str,
            expected: Optional[str] = None,
            xfail: bool = False,
            channel: str = 'test_chan',
            timeout: float = 2,
        ):
        self.desc = desc
        self.input = input
        self.expected = expected
        self.channel = channel
        self.timeout = timeout
        self.xfail = xfail

        global using_config
        self.config = using_config
        using_config.register(self)


    async def run(self, client: App, config: Config) -> TS:
        if hasattr(self, 'status'):
            raise TestAlreadyRunException(self)
        self.status = TS.FAIL
        if self.xfail: self.status = TS.XFAIL

        print(f'  {self.desc:70}', end='', file=stderr, flush=True)

        rsp: str|None = await client.send_test(
            self.input.format(tag = config.attract_tag),
            channel = self.channel,
            timeout = self.timeout,
        )

        if rsp == self.expected:
            if self.xfail:
                self.status = TS.FAIL
            else:
                self.status = TS.PASS

        print(f'[{self.status.color_label()}]', file=stderr)

        if self.xfail and self.status == TS.FAIL:
            print('    expected failure, got pass, reporting as failure.',
                  file=stderr)

        if rsp != self.expected:
            print('*** NOT EXPECTED ***', file=stderr)
            print(f'Expected:\n{repr(self.expected)}\nGot:\n{repr(rsp)}',
                  file=stderr)

        self.tally.register(self.status)
        return self.status

async def run_tests(client: App) -> None:
    # Remove test tempdir
    print(file=stderr)
    await shell_or_die(f'rm -frv ./testtmp')
    print(file=stderr)
    for tcfg in configs:
        await tcfg.run_tests(client)


##################### TEST DEFINITIONS #####################

using_config = Basic

Test(
    'hello world',
    input = '{tag}\n? "Hello, world!!',
    expected = '```\nHello, world!!\n```',
)

Test(
    'code block stripping',
    input = '{tag}```\n? "Hell```o, world!!\n```',
    expected = '```\nHello, world!!\n```',
)

Test(
    'too many lines',
    input = '{tag}\n10 ? "Hello, world!!":goto 10',
    expected = (
        '```\n'
        + ''.join(('Hello, world!!\n' for i in range(0,30)))
        + '```\n[[Output was truncated]]'
    ),
)

Test(
    'too many chars',
    input = '{tag}\n10 ? "*";:goto 10',
    expected = (
        '```\n'
        + ''.join(('*' for i in range(0,1900)))
        + '\n```\n[[Output was truncated]]'
    ),
)

Test(
    'm:plus',
    input = '{tag} m:plus\n? "{{test}}"',
    expected = '```\n[TEST]\n```',
)

Test(
    'm:invalid',
    input = '{tag} m:invalid\n? "{{test}}"',
    expected = '[[m: invalid machine "invalid"]]\n```\n{test}\n```',
)

Test(
    'dm message',
    input = '? "Hello, world!!',
    expected = '```\nHello, world!!\n```',
    channel = 'dm',
    xfail = True,
)

# Basic: Timeouts expected
Test(
    'wrong channel',
    channel = 'bad_chan',
    input = '{tag}\n? "Hello, world!!',
    expected = None,
)

Test(
    'untagged',
    input = '? "Hello, world!!',
    expected = None
)

# Longer timeout
Test(
    'bobbin timeout',
    input = '{tag}\n10 PRINT "@";:FOR P=1 TO 10000:NEXT:GOTO 10\nRUN',
    expected = ('```\n@@@@@@@@@@@@\nbobbin: max emulated runtime (120 secs)'
                ' exceeded.\nbobbin: Exiting (3).\n```'),
    timeout = 30,
)
