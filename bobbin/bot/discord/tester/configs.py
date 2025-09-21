from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import App
    from .tests import Test

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
    def run_tests(cls, client: App) -> None:
        pass # XXX

class Foo(Config):
    pass
