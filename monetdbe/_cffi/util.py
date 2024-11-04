
from typing import Dict
from logging import getLogger
from pprint import pprint

_logger = getLogger(__file__)


def get_info() -> Dict:
    """
    Fetch some MonetDBe specific properties
    """
    import monetdbe

    from_monetdb = monetdbe.connect().execute("select * from env()").fetchall()

    try:
        from monetdbe._cffi.monet_info import INFO
    except ImportError as e:
        _logger.error(f"can't import branch file: {e}")
        INFO = {}

    try:
        version = monetdbe._cffi.internal.version()
    except Exception as e:
        _logger.error(f"can't call monetdb version() function: {e}")
        version = "not set"

    return {"from_monetdb": from_monetdb, "version": version, **INFO}


def print_info():
    pprint(get_info())
