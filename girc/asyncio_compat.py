"""
Version independent compat wrapper for asyncio
"""

import asyncio

__all__ = ('ensure_future',)


def ensure_future(fut, *, loop=None):
    """
    Wraps asyncio.async()/asyncio.ensure_future() depending on the python version
    :param fut: The awaitable, future, or coroutine to wrap
    :param loop: The loop to run in
    :return: The wrapped future
    """
    if sys.version_info < (3, 4, 4):
        # This is to avoid a SyntaxError on 3.7.0a2+
        func = getattr(asyncio, "async")
    else:
        func = asyncio.ensure_future

    return func(fut, loop=loop)  # pylint: disable=locally-disabled, deprecated-method
