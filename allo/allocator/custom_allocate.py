"""Allocator methods.
"""
import six
import warnings
import numpy as np
import pandas as pd

import optimize
from allocator.risk_parity import risk_parity
from allocator.final_adjustment import flatten_upperbound
from helper.temp_metrics import ETL # move metrics to cxtpy


def get_df_combined_from_rs_list(rs_list, d1 = datetime.datetime(2000,1,1), d2 = datetime.datetime(3000,1,1)):
    """Extract df_combined from rs_list given date constraint: `(d1,d2)`."""
    df_list = []
    for rs in rs_list:
        temp_df = rs.df.loc[d1:d2].copy()
        temp_df.columns = [rs.Name]
        df_list.append(temp_df)
    df_combined = df_list_merge(df_list, "outer")
    return df_combined


def constrained_risk_parity(rseries_list, strategy_list, a1, a2, upperbound):
    """Constrained Risk Parity (CRP) using std dev (volatility) as risk measure""""
    sd_list = []
    for rs in rseries_list:
        rdf = rs.df.copy().loc[a1:a2]
        sd = rdf.std()[0]
        sd_list.append(sd)
    w = risk_parity(sd_list, upperbound = upperbound)
    w = {name:weight for name, weight in zip(strategy_list, w)}
    return w


def constrained_tail_risk_parity(rseries_list, strategy_list, a1, a2, upperbound, tail_p):
    """Constrained Tail Risk Parity (CRPT) using Expected Tail Loss (ETL) as risk measure""""
    sd_list = []
    for rs in rseries_list:
        rdf = rs.df.copy().loc[a1:a2]
        sd = ETL(rdf.iloc[:, 0].values, tail_p)
        sd_list.append(sd)
    w = risk_parity(sd_list, upperbound = upperbound)
    w = {name:weight for name, weight in zip(strategy_list, w)}
    return w


def constrained_max_sharpe(rseries_list, a1, a2, lowerbound, upperbound, optimize_method = None):
    """Constrained Max Sharpe (CMS)""""
    allocate_back_df = get_df_combined_from_rs_list(rs_list = rseries_list, d1 = a1, d2 = a2).fillna(0)

    fun = optimize.lambda_optimize.get("Weights_MaxSharpePenalty_fun")
    fun = fun(allocate_back_df)
    w, res = optimize.optimize.OptimizeWeights(allocate_back_df, fun, lowerbound = lowerbound, upperbound = upperbound, 
                                method = optimize_method, tol = 1e-8, constraint = True)
    return w


def avg_cms_crp(rseries_list, strategy_list, a1, a2, lowerbound, upperbound, weights = (1,1)):
    """Weighted average of CMS and CRP"""
    w1 = constrained_max_sharpe(rseries_list, a1, a2, lowerbound, upperbound, optimize_method = None)
    w2 = constrained_risk_parity(rseries_list, strategy_list, a1, a2, upperbound)
    w = {}
    for key, val in w1.items():
        w[key] = (w1[key]*weights[0] + w2[key]*weights[1])/(weights[0]+weights[1])
    return w


def avg_cms_crpt(rseries_list, strategy_list, a1, a2, lowerbound, upperbound, tail_p, weights = (1,1)):
    """Weighted average of CMS and CRPT"""
    w1 = constrained_max_sharpe(rseries_list, a1, a2, lowerbound, upperbound, optimize_method = None)
    w2 = constrained_tail_risk_parity(rseries_list, strategy_list, a1, a2, upperbound, tail_p)
    w = {}
    for key, val in w1.items():
        w[key] = (w1[key]*weights[0] + w2[key]*weights[1])/(weights[0]+weights[1])
    return w


def chrp(rseries_list, a1, a2, upperbound):
    """Constrained Hierarchical Risk Parity""""
    allocate_back_df = get_df_combined_from_rs_list(rs_list = rseries_list, d1 = a1, d2 = a2).fillna(0)
    w = optimize.optimize.optimize_hrp(allocate_back_df)
    w2 = [j for j in w.values()]
    w2 = flatten_upperbound(w2, upperbound)
    for key,val in zip(w.keys(), w2):
        w[key] = val
    return w


def cewms(rseries_list, a1, a2, lowerbound, upperbound):
    """Constrained Exponential Weighted Max Sharpe"""
    allocate_back_df = get_df_combined_from_rs_list(rs_list = rseries_list, d1 = a1, d2 = a2).fillna(0)
    w = optimize.optimize.optimize_max_sharpe(allocate_back_df, lowerbound, upperbound)
    return w


def equal_weight(rseries_list, a1, a2):
    """Equal weight"""
    allocate_back_df = get_df_combined_from_rs_list(rs_list = rseries_list, d1 = a1, d2 = a2).fillna(0)
    w = optimize.optimize.optimize_equal_weight(allocate_back_df)
    return w


def replicate_minimize_lookback_square_error(rseries_list, a1, a2, lowerbound, upperbound, target_ret, optimize_method = None, constraint = True):
    """For Replicate: Minimize the lookback square error of optimized returns and target returns"""
    allocate_back_df = get_df_combined_from_rs_list(rs_list = rseries_list, d1 = a1, d2 = a2).fillna(0)
    fun = optimize.lambda_optimize.get("Weights_MinTargetErr")
    fun = fun(allocate_back_df, target_ret)
    w, res = OptimizeWeights(allocate_back_df, fun, lowerbound = lowerbound, upperbound = upperbound, 
                                method = optimize_method, tol = 1e-8, constraint = constraint)
    return w


def two_layer_knn_rp(data_df, a1, a2, cluster_df, allocation_method, **kwargs):
    """Two layers kNN clustering of strategies, then allocate each cluster by `allocation_method`
    
    # STATUS: IN DEVELOPMENT
    """
    # cluster_df = knn_cluster(data_df, a1, a2, **kwargs)
    # w, wdf = two_layer_weight(data_df, a1, a2, cluster_df, allocation_method = allocation_method)
    # return w, wdf
    return


def get(identifier):
    """Get the `identifier` allocation function.
    # Arguments
        identifier: None or str, name of the function.
    # Returns
        The allocation function, `CRP` if `identifier` is None.
    # Raises
        ValueError if unknown identifier
    """
    if identifier is None:
        print("Allocation function not specified! Default to constrained_risk_parity.")
        return constrained_risk_parity
    if isinstance(identifier, six.string_types):
        identifier = str(identifier)
        return globals().get(identifier)
    elif callable(identifier):
        # if isinstance(identifier, Layer):
        #     warnings.warn(
        #         'Do not pass a layer instance (such as {identifier}) as the '
        #         'activation argument of another layer. Instead, advanced '
        #         'activation layers should be used just like any other '
        #         'layer in a model.'.format(
        #             identifier=identifier.__class__.__name__))
        return identifier
    else:
        raise ValueError('Could not interpret '
                         'allocator.method function identifier:', identifier)