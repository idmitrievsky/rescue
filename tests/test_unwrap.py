from typing import Generator

import pytest

from rescue.core import unwrap


def test_unwrap_generator_with_yield_will_raise() -> None:
    def always_yield() -> Generator[None, None, int]:
        yield None
        return 0

    with pytest.raises(AssertionError, match="argument doesn't yield"):
        unwrap(always_yield())


def test_unwrap_generator_without_yield_will_return() -> None:
    def never_yield() -> Generator[None, None, int]:
        always_false = False
        if always_false:
            yield None
        return 0

    assert unwrap(never_yield()) == 0
