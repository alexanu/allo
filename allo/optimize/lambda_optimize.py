import six
import datetime
import numpy as np
import pandas as pd

from optimize.optimize import OptimizeWeights
from optimize.optimize_metrics import P_MIN_SHARPE_PENALTY, P_SHARPE, P_RET_TARGET_SQERR


def Weights_MaxSharpePenalty(rdf, lowerbound = 0, upperbound = 0.1):
    fun = lambda x: P_MIN_SHARPE_PENALTY(x, rdf.values, 1)
    return OptimizeWeights(rdf = rdf, fun = fun, lowerbound = lowerbound, upperbound = upperbound, tol = 1e-9, constraint = False)

def Weights_MaxSharpe(rdf, lowerbound = 0, upperbound = 0.1):
    fun = lambda x: -1*P_SHARPE(x, rdf.values, 1)
    return OptimizeWeights(rdf = rdf, fun = fun, lowerbound = lowerbound, upperbound = upperbound, constraint = True)

def Weights_MaxSharpe_fun(rdf):
    fun = lambda x: -1*P_SHARPE(x, rdf.values, 1)
    return fun

def Weights_MaxSharpePenalty_fun(rdf):
    fun = lambda x: P_MIN_SHARPE_PENALTY(x, rdf.values, 1)
    return fun

def Weights_MinTargetErr(rdf, target_ret):
    fun = lambda x: 1000*P_RET_TARGET_SQERR(x, rdf.values, target_ret)
    return fun


def get(identifier):
    """Get the `identifier` function.
    # Arguments
        identifier: None or str, name of the function.
    # Returns
        The allocation function
    # Raises
        ValueError if unknown identifier
    """
    # if identifier is None:
    #     return None
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
                         'optimize.lambda_optimize function identifier:', identifier)