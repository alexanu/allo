import numpy as np
import pandas as pd

def P_RET(weights, returns):
    #weights (n,1), returns (k,n)
    R = np.array(weights)*np.array(returns)
    RP = np.sum(R, axis = 1)
    return RP

def P_RET_TARGET_SQERR(weights, returns, target_ret):
    opt_ret = P_CAGR(weights, returns, af = returns.shape[0])
    ERR = (opt_ret - target_ret)**2
    return ERR

def P_CAGR(weights, returns, af = 1):
    RP = P_RET(weights, returns)
    N = RP.shape[0]
    return np.prod(1+RP)**(af/N) - 1

def P_VOL(weights, returns, af = 1):
    RP = P_RET(weights, returns)
    N = RP.shape[0]
    return np.std(RP)*np.sqrt(af)


def P_SHARPE(weights, returns, af = 252):
    RP = P_RET(weights, returns)
    N = RP.shape[0]
    return (np.prod(1+RP)**(af/N) - 1)/(np.std(RP)*np.sqrt(af))

def P_MIN_SHARPE_PENALTY(weights, returns, af = 252):
    RP = P_RET(weights, returns)
    N = RP.shape[0]
    penalty = np.sum(weights) - 1
    penalty = (10**6)*(penalty**2)
    return -1*(np.prod(1+RP)**(af/N) - 1)/(np.std(RP)*np.sqrt(af)) + penalty
