from __future__ import annotations

import asyncio
from asyncio.subprocess import DEVNULL
import posix
import signal
from sys import stderr
from typing import TYPE_CHECKING, Any, TextIO

from ..util import shell_or_die

import testcfg as cfg

if TYPE_CHECKING:
    from .app import App
    from .tests import Test
else:
    App = None
    Test = None

class BobbinUnexpectedTermination(Exception):
    pass

configs = []

class Config:
    ########## CLASS METHODS ##########

    def __init_subclass__(cls) -> None:
        global configs
        configs.append(cls)
        cls.tests = [] # type: ignore[attr-defined]

    @classmethod
    def register(cls, test: Test) -> None:
        cls.tests.append(test) # type: ignore[attr-defined]

    @classmethod
    async def run_tests(cls, client: App) -> None:
        async with cls(client):  # Use an instance of this Config as the ContextManager
            for t in cls.tests: # type: ignore[attr-defined]
                await t.run(client)

            print('Sleeping after tests', file=stderr)
            await asyncio.sleep(2)

    ########## INSTANCE METHODS ##########

    def __init__(self, client: App) -> None:
        self.client = client

    async def __wait_for_bot_ready(self, logfile: str) -> None:
        c = 0
        while c < 10:
            await asyncio.sleep(1)
            ++c
            proc = await asyncio.create_subprocess_exec(
                'grep', '-q', 'We have logged in as ', logfile,
                stdin = DEVNULL, stderr = DEVNULL, stdout = DEVNULL
            )
            rslt = await proc.wait()
            if rslt == 0:
                return
        raise Exception("Couldn't detect bobbin bot startup")


    async def __monitor_bobbin(self) -> None:
        if self.bobbin_proc is None:
            # can't happen, shuts up type-checking
            return
        await self.bobbin_proc.wait()
        # If we get here, bobbin exited unexpectedly
        raise BobbinUnexpectedTermination('lost bobbin process')

    def write_config(self, file: TextIO) -> None:
        def q(s: str) -> str:
            return "'" + s.replace("'", "'\\''") + "'"
        test_chan = self.client.get_channel_from_cfg('test_chan')
        file.write(
            f'class Config:\n'
            f'    token = {cfg.BOBBIN_TOKEN}\n'
            f'    attract_tag = {q(cfg.attract_tag)}\n'
            '\n'
            f'    admin_id = {self.client.user.id}\n' # type: ignore
            f'    notify_admin = []\n'
            '\n'
            f'    acceptable_channels = [\n'
            f"        '{test_chan.guild.name}#{test_chan.name}'\n" # type: ignore
            f'    ]\n'
        )

    async def __aenter__(self) -> Config:
        def q(s: str) -> str:
            return "'" + s.replace("'", "'\\''") + "'"

        # Set up the test dir
        testdir = f'./testtmp/{self.__class__.__name__}'
        qtestdir = q(testdir)
        #   rm first, if necessary
        await shell_or_die(f'rm -frv {qtestdir}')
        #   then create
        await shell_or_die(f'mkdir -pv {qtestdir}')
        #   now set up symlinks
        await shell_or_die(f'ln -s ../../bobbin_discord.py {qtestdir}')
        await shell_or_die(f'ln -s ../../bobbin {qtestdir}')

        # Write the config file
        cfgf = open(f'{testdir}/config.py', 'x')
        if cfgf is None:
            raise Exception("can't open config for writing")
        self.write_config(cfgf)
        cfgf.close()
        await asyncio.sleep(0)

        # Fire up bobbin
        print('Spawning bobbin_discord.py.', file=stderr)
        proc = await asyncio.create_subprocess_shell(
            f'cd {qtestdir} && exec ./bobbin_discord.py'
        )
        self.bobbin_proc = proc
        task = asyncio.create_task(self.__monitor_bobbin())
        self.bobbin_monitor_task = task

        # Wait for bobbin to come up
        await self.__wait_for_bot_ready(f'{testdir}/logs/discord.log')

        return self

    async def __aexit__[T](self, exc_type: type[T], exc_value: T, tb : Any) -> None:
        proc = self.bobbin_proc
        if proc is None:
            return
        self.bobbin_pid = None
        if self.bobbin_monitor_task is not None:
            self.bobbin_monitor_task.cancel()
            self.bobbin_monitor_task = None
        print('Killing bobbin_discord.py.', file=stderr)
        proc.send_signal(signal.SIGINT)
        await proc.wait()

    bobbin_proc: asyncio.subprocess.Process|None
    bobbin_monitor_task: asyncio.Task[None]|None

class Basic(Config):
    pass
