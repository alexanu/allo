"""Contains custom excluder of strategies methods
"""
import six
import time
import random
import datetime
import numpy as np
import pandas as pd

from helper.main import set_default
from helper.seasonality import get_months_list, get_tradeable_month
from allocator.custom_allocate import get_df_combined_from_rs_list
# from google.google_sheet import StrategyMeta


def exclude_high_correlation(track_df, b_enddate, corr_threshold = 0.8, **kwargs):
    """Exclude strategies that are highly correlated with another
    """    
    rs_list = track_df["rs"].values
    
    # Calculate correlation
    df_combined = get_df_combined_from_rs_list(rs_list = rs_list, d2 = b_enddate)
    cr = df_combined.corr().abs()
    
    # Remove strategy that has high correlation with others
    cr2 = (cr > corr_threshold) & (cr < 1)
    
    exclude_corr_meta_df = pd.DataFrame()
    if cr2.any().any():
        ix, iy = np.where(cr2)
        to_remove_index = [x for x, y in zip(ix, iy) if x < y]
        corr_with_index = [y for x, y in zip(ix, iy) if x < y]
        to_remove_strat = [j for j in cr2.index[to_remove_index]]
        corr_with_strat = [j for j in cr2.index[corr_with_index]]
        
        # self.log("Removing Highly Correlated Strategies: {}".format(str(to_remove_strat)), "Exclude_HighCorrelation_1")
        # self.log("Highly Correlated With  -  Strategies: {}".format(str(corr_with_strat)), "Exclude_HighCorrelation_2")

        exclude_corr_meta_df = track_df.loc[track_df["Name"].isin(to_remove_strat)].copy()
        track_df = track_df.loc[~track_df["Name"].isin(to_remove_strat)]
    else:
        print("No Highly Correlated Strategies.", "Exclude_HighCorrelation_3")
        # self.log("No Highly Correlated Strategies.", "Exclude_HighCorrelation_3")
    return track_df, exclude_corr_meta_df


def exclude_seasonality_month(track_df, b_enddate, f_startdate, f_enddate, **kwargs):
    """Exclude seasonality strategies that are not trading in particular months"""
    months_list = get_months_list(f_startdate, f_enddate)
    
    tradeable_list = []
    for rs in track_df["rs"]:
        tradeable_month = get_tradeable_month(df = rs.df.loc[:b_enddate])
        tradeable = np.array([j in tradeable_month for j in months_list]).any()
        tradeable_list.append(tradeable)
    track_df["tradable"] = tradeable_list
    
    exclude_season_meta_df = track_df.loc[~track_df["tradable"], :].copy()
    to_remove_strat = track_df.loc[~track_df["tradable"], "Name"].values
    # self.log("Removing Inactive Seasonalities Strategies: {}".format(to_remove_strat), "Exclude_SeasonalityMonth")
    
    track_df = track_df.loc[track_df["tradable"]]
    return track_df, exclude_season_meta_df


def exclude_data_mined(track_df, **kwargs):
    """Exclude DataMined strategies"""
    u1 = track_df["Name"].str.contains("DataMined")
    to_remove_strat = track_df.loc[u1, "Name"].values
    # self.log("Removing DataMined Strategies: {}".format(to_remove_strat), "Exclude_DM")
    exclude_data_mined_meta_df = track_df.loc[track_df["Name"].isin(to_remove_strat)]
    track_df = track_df.loc[~track_df["Name"].isin(to_remove_strat)]
    return track_df, exclude_data_mined_meta_df


# def exclude_insample(track_df, f_startdate, **kwargs):
#     SM = StrategyMeta()
#     track_df["DateAdded"] = track_df["Name"].apply(lambda x: SM.get_date_from_name(x))
#     track_df["ValidOOS"] = track_df["DateAdded"].apply(lambda x: f_startdate > x)
#     exclude_is_meta_df = track_df.loc[~track_df["ValidOOS"], :].copy()
#     to_remove_strat = track_df.loc[~track_df["ValidOOS"], "Name"].values
#     # self.log("Removing In-Sample Strategies: {}".format(to_remove_strat), "Exclude_IS")
#     track_df = track_df.loc[track_df["ValidOOS"]]
#     return track_df, exclude_is_meta_df

        
# def ExcludeZeroVariance(track_df, a1, a2, **kwargs):
#     allocate_method = kwargs.get("allocate_method")
#     risk_method = ["CRP", "CRPTail", "RiskParity", "AvgCMSCRP", "AvgCMSCRPT", "AvgCRPCRPT", "HRP", "CHRP"]
#     if allocate_method not in risk_method:
#         return 
    
#     # Get df_combined and filter date range
#     strategy_list = track_df["Name"].values
#     rseries_list = track_df["rs"].values
    
#     allocate_back_df = get_df_combined_from_rs_list(rs_list = rseries_list, d1 = a1, d2 = a2).fillna(0)
#     to_remove_strat = allocate_back_df.columns[allocate_back_df.std(axis=0)==0].values
    
#     mdf = track_df
    
#     self.exclude_zerovariance_meta_df = mdf.loc[mdf["Name"].isin(to_remove_strat), :].copy()
    
#     self.log("Removing Zero Variance Strategies: {}".format(str(to_remove_strat)), "ExcludeZeroVariance")
    
#     track_df = mdf.loc[~mdf["Name"].isin(to_remove_strat)]


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
        print("Excluder function not specified! Raise err.")
        raise Exception("Error.")
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
