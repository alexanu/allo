import datetime
import numpy as np
import pandas as pd


def risk_parity(sd_list, upperbound = 0.1):
    """Apply inverse weight to the given risk factor (`sd_list`).
    """
    sd_list = np.array(sd_list)
    sd_list[np.isnan(sd_list)] = 0
    
    inv_sd_list = 1/sd_list
    inv_sd_list[np.isinf(inv_sd_list)] = 0
    
    w = inv_sd_list/np.sum(inv_sd_list)
    
    if upperbound == 1:
        return w
    
    u1 = w > upperbound
    u2 = w <= upperbound
    
    w[u1] = upperbound
    remainder_weights = 1 - np.sum(w[u1])
    if np.sum(w[u2]) > 0:
        scale = remainder_weights/np.sum(w[u2])
        w[u2] = w[u2]*scale
    
    # Final flatten: disregard any conditions and flatten the weights to obey upperbound
    u3 = w > upperbound
    w[u3] = upperbound
    
    return w
