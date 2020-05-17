import datetime
import numpy as np
import pandas as pd

from scipy.optimize import minimize
from pypfopt.value_at_risk import CVAROpt
from pypfopt.hierarchical_risk_parity import HRPOpt
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt.expected_returns import prices_from_returns, mean_historical_return, ema_historical_return


def OptimizeWeights(rdf, fun, lowerbound, upperbound, method, tol = 1e-8, constraint = True, sum_weight = 1):
    N = rdf.values.shape[1]
    if constraint:
        cons = (
                    {'type': 'eq', 'fun': lambda x:  np.sum(x)-sum_weight},
               )
    else:
        cons = ()
    bnds = [(lowerbound, upperbound) for j in range(N)]
    initial_weights = [1/N for j in range(N)]
    res = minimize(fun, initial_weights, method=method, bounds=bnds, constraints=cons, tol=tol, jac = "2-point", hess = "2-point")
    w = {name:weight for name, weight in zip(rdf.columns, res.x)}
    return w, res


# Working 
def optimize_equal_weight(returns_df):
    
    col_names = returns_df.columns.values
    count = len(col_names)
    weight_dict = {}
    
    for col in col_names:
        weight_dict[col] = 1/count
        
    return weight_dict

def optimize_value_at_risk(returns_df):

    cVAROptimizer = CVAROpt(returns_df)
    weights_dict = cVAROptimizer.min_cvar()

    return weights_dict

def optimize_hrp(returns_df):
    #hierarchical risk parity

    HRPOptimizer = HRPOpt(returns_df)
    weights_dict = HRPOptimizer.hrp_portfolio()

    return weights_dict

def optimize_max_sharpe(returns_df, lowerbound = 0, upperbound = 1):
    wb = (lowerbound, upperbound)
    
    ema_returns_df = ema_historical_return(prices_from_returns(returns_df))
    returns_cov_df = returns_df.cov()
    
    EFOptimizer = EfficientFrontier(ema_returns_df, returns_cov_df, weight_bounds=wb)
    weights_dict = EFOptimizer.max_sharpe()
 
    return weights_dict


# Temp
def optimize_min_volatility(expected_returns_df, cov_matrix):

    EFOptimizer = EfficientFrontier(expected_returns_df, cov_matrix)
    weights_dict = EFOptimizer.min_volatility()

    return weights_dict

def optimize_efficient_risk(expected_returns_df, cov_matrix, target_risk):

    EFOptimizer = EfficientFrontier(expected_returns_df, cov_matrix)
    weights_dict = EFOptimizer.efficient_risk(target_risk)
    
    return weights_dict

def optimize_efficient_returns(expected_returns_df, cov_matrix, target_return):

    EFOptimizer = EfficientFrontier(expected_returns_df, cov_matrix)
    weights_dict = EFOptimizer.efficient_return(target_return)

    return weights_dict

# def optimize_max_sharpe(expected_returns_df, cov_matrix):

#     EFOptimizer = EfficientFrontier(expected_returns_df, cov_matrix)
#     weights_dict = EFOptimizer.max_sharpe()
 
#     return weights_dict