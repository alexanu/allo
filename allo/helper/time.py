"""Helper functions - time-related
"""
import time
from helper.main import set_default


def timeit(method):
    """decorator to time function
    """
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        verbose = kw.get("verbose")
        verbose = set_default(verbose, 2)
        if verbose > 1:
            print("{}: {} seconds.".format(method.__name__, te-ts))
    return timed