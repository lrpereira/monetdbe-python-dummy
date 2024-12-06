from typing import Optional
import monetdbe

CACHED_ARGS = ''
CACHED_CONNECTION: Optional[monetdbe.Connection] = None


def is_alive():
    # noqa
    global CACHED_CONNECTION
    if CACHED_CONNECTION is None:
        return False
    if not hasattr(CACHED_CONNECTION, '_internal'):
        return False
    if CACHED_CONNECTION._internal is None:
        return False
    return True


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