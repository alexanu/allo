"""Helper functions - miscellaneous
"""
import datetime
import numpy as np
import pandas as pd


def set_default(var, default):
    return default if var is None else var