from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import App
    from .tests import Test
else:
    App = None
    Test = None

configs = []

class Config:
    def __init_subclass__(cls) -> None:
        global configs
        configs.append(cls)
        cls.tests = [] # type: ignore[attr-defined]

    @classmethod
    def register(cls, test: Test) -> None:
        cls.tests.append(test) # type: ignore[attr-defined]

    @classmethod
    async def run_tests(cls, client: App) -> None:
        for t in cls.tests: # type: ignore[attr-defined]
            await t.run(client)

class Foo(Config):
    pass
