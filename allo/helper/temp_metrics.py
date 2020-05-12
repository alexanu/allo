import numpy as np


def ETL(x, p = 0.05):
    """Expected tail loss"""
    x = np.array(x)
    neg_ret = np.percentile(x, p*100)
    return np.mean(x[x < neg_ret])
