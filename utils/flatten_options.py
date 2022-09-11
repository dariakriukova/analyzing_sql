from itertools import chain
from typing import Sequence


def flatten_options(ctx, param, values: Sequence[str]) -> set[str]:
    return set(chain.from_iterable(
        (value.split(',') if isinstance(value, str) else value for value in values)))
