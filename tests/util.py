from typing import Optional
import monetdbe

CACHED_ARGS = ''
CACHED_CONNECTION: Optional[monetdbe.Connection] = None

def is_alive():
    global CACHED_CONNECTION
    return (
        CACHED_CONNECTION is not None
        and hasattr(CACHED_CONNECTION, '_internal')
        and CACHED_CONNECTION._internal is not None
    )

def flush_cached_connection():
    global CACHED_CONNECTION
    global CACHED_ARGS
    if is_alive():
        CACHED_CONNECTION.close()
    CACHED_CONNECTION = None
    CACHED_ARGS = ''


def get_cached_connection(*args, **kwargs) -> monetdbe.Connection:
    global CACHED_CONNECTION
    global CACHED_ARGS

    cachekey = repr((args, kwargs))
    if cachekey != CACHED_ARGS:
        flush_cached_connection()

    if is_alive():
        assert CACHED_CONNECTION
        CACHED_CONNECTION.rollback()
    else:
        # with open('/dev/tty', 'w') as f:
        #     print('<<<<OPEN OPEN OPEN>>>>', file=f)
        CACHED_CONNECTION = monetdbe.connect(':memory:')
        CACHED_ARGS = cachekey

    return CACHED_CONNECTION