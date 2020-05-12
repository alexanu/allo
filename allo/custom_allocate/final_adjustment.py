"""Contains functions for final adjustment of weights.
"""
import datetime
import numpy as np
import pandas as pd


def flatten_upperbound(w, upperbound = 0.1):
    """Adjust any weights above a specified upperbound.

    # Step 1: Set any weights above `upperbound` as `upperbound`.
    # Step 2: Scale all other weights multiplicatively, such that the sum of all weights = 1
    # Step 3: Set any weights above `upperbound` as `upperbound` again (there may be some weights over-scaled in Step 2).
    """
    w = np.array(w)
    u1 = w > upperbound
    u2 = w <= upperbound
    
    w[u1] = upperbound # Step 1
    remainder_weights = 1 - np.sum(w[u1])

    if np.sum(w[u2]) > 0:
        scale = remainder_weights/np.sum(w[u2])
        w[u2] = w[u2]*scale # Step 2
    
    u3 = w > upperbound
    w[u3] = upperbound # Step 3
    return w


def flatten_and_distribute(w, min_threshold = 0.008):
    """Flatten any weights below `min_threshold` and scale the rest multiplicatively, such that sum = 1.
    """
    w = np.array(w)
    if np.min(w[w!=0]) < min_threshold:
        w[w == np.min(w[w != 0])] = 0 #flatten the smallest
        w = w/np.sum(w) #distribute to the others #multiplicative distribution
    return w
    

def sequential_distribute_min_weight(w, min_threshold = 0.008):
    """Sequentially finds the lowest non-zero weight(s) that are below min_threshold and set them to zero. 
    # Then scale the rest by a factor of k such that the sum of weights is 1.
    # Repeat the process until all weights are either zero or above min_threshold.
    """
    w = np.array(w)
    w[np.isnan(w)] = 0
    
    if np.all(w == 0):
        return w
    
    w = np.round(w,10)
    
    while np.min(w[w != 0]) < min_threshold:
        w = flatten_and_distribute(w, min_threshold)
    return w


def adjust_forced_min_weight(mdf, strat_min_alloc):
    """Force specified strategies to be allocated with specified minimum weights.

    # Example params:
    # strat_min_alloc = {"_0146_2_BondTurnOfTheMonth": 0.045, "_0058_2_ZommaCrashPortfolio_R": 0.03} # example
    """
    
    strats = list(strat_min_alloc.keys())
    if len(strats) == 0:
        return mdf # no adjustment
        
    min_allocs = list(strat_min_alloc.values())
    mdf["old_weight_2"] = mdf["weight"].copy()
    min_sum_weight = 0
    for strat, min_alloc in strat_min_alloc.items():
        u1 = mdf["Name"] == strat
        u2 = mdf["weight"] < min_alloc
        mdf.loc[u1 & u2, "weight"] = min_alloc
        if (u1 & u2).any():
            min_sum_weight += min_alloc
    if min_sum_weight == 0:
        "no adjustment"
    elif min_sum_weight > 1:
        print("The sum of the minimum allocations exceed 1! Adjustments will not be made (Total allocations will exceed 1!).")
    else:
        u2 = mdf["Name"].isin(strats)
        sum_weight_old = mdf.loc[~u2, "weight"].sum() # sum of weights of other strats before adjustments
        sum_weight_new = 1 - min_sum_weight # sum of weights of other strats after adjustments
        ratio = sum_weight_new/sum_weight_old # adjustment ratio
        mdf.loc[~u2, "weight"] = mdf.loc[~u2, "weight"]*ratio
    w = mdf["weight"].copy()
    mdf = mdf.drop(["weight"], axis = 1)
    mdf["weight"] = w
    return mdf