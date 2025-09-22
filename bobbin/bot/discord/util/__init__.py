import asyncio
from asyncio import create_subprocess_shell
from asyncio.subprocess import Process

# blocks until shell command exits, but
#  does so graciously, to allow other ctasks to run
async def shell_or_die(cmd: str) -> None:
    p: Process = await create_subprocess_shell(cmd)
    st: int = await p.wait()
    if st != 0:
        raise Exception(f'{cmd}: Exit {st}')
