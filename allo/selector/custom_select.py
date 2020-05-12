"""Contains custom selection of strategies methods
"""
import time
import random
import datetime
import numpy as np
import pandas as pd

from helper.main import set_default
from data.get_benchmark import get_benchmark


def select_random(rseries_list, strategy_list, s1, s2, size = 20, seed = None, **kwargs):
    """
    size: select `size` strategies randomly
    seed: set `None` to use time based seed
    """
    size = kwargs.get("size")
    time_seed = int((time.time()*1000000) % 1000000)
    seed = set_default(seed, time_seed)

    size = size if len(strategy_list) > size else len(strategy_list)
    np.random.seed(seed)
    selected_strategy_list = np.random.choice(strategy_list, size = size, replace = False)
    return selected_strategy_list


def select_sharpe_threshold(rseries_list, strategy_list, s1, s2, sharpe_threshold = 0.5, **kwargs):
    """Select strategy if sharpe > `sharpe_threshold`.
    """
    selected_strategy_list = []
    for rs, name in zip(rseries_list, strategy_list):
        sharpe_val = rs.get_metrics_by_date_list(date_list = [dict(d1 = s1, d2 = s2)], metric_fun = "Sharpe")[0]
        if sharpe_val > sharpe_threshold:
            selected_strategy_list.append(name)
    return selected_strategy_list


def select_sharpe_pct(rseries_list, strategy_list, s1, s2, top_pct = 0.3, **kwargs):
    """Select top `top_pct*100`% of strategies based on sharpe
    """
    top = int(len(strategy_list)*top_pct)
    sharpe_dict_list = []
    for rs, name in zip(rseries_list, strategy_list):
        metrics = rs.get_metrics_by_date(d1 = s1, d2 = s2)
        d = {}
        d["Sharpe"] = metrics.get("Sharpe")
        d["Name"] = name
        sharpe_dict_list.append(d)
    sharpe_df = pd.DataFrame(sharpe_dict_list)
    sharpe_df = sharpe_df.sort_values("Sharpe", ascending = False).head(top)
    selected_strategy_list = sharpe_df["Name"].values
    return selected_strategy_list


def select_alpha_sharpe_pct(rseries_list, strategy_list, s1, s2, top_pct = 0.3, benchmark_asset = "SPY", **kwargs):
    """Select top `top_pct*100`% of strategies based on alpha sharpe
    """
    df_bench = get_benchmark(benchmark_asset)
    top = int(len(strategy_list)*top_pct)

    sharpe_dict_list = []
    for rs, name in zip(rseries_list, strategy_list):
        try:
            metrics = rs.get_alpha_metrics_by_date(d1 = s1, d2 = s2, benchmark_df = df_bench)
        except:
            metrics = dict(Sharpe = -99)
        d = {}
        d["Sharpe"] = metrics.get("Sharpe")
        d["Name"] = name
        sharpe_dict_list.append(d)
    sharpe_df = pd.DataFrame(sharpe_dict_list)
    sharpe_df = sharpe_df.sort_values("Sharpe", ascending = False).head(top)
    selected_strategy_list = sharpe_df["Name"].values
    return selected_strategy_list


def select_all(rseries_list, strategy_list, s1, s2, **kwargs):
    return strategy_list


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
        print("Selection function not specified! Default to select_all.")
        return select_all
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
                         'selector.custom_select function identifier:', identifier)