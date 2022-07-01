import functools
import traceback
from concurrent import futures
from typing import Iterable


def filter_generator(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        for y in f(*args, **kwargs):
            if y is None:
                continue
            yield y
    return wrapper


@filter_generator
def check(futures: Iterable['futures.Future'], throw=True):
    for future in futures:
        e = future.exception()
        if e:
            if throw:
                raise e
            else:
                traceback.print_exception(etype=type(e), value=e, tb=e.__traceback__)

        yield future