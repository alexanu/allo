import datetime
import numpy as np
import pandas as pd 
from dateutil.relativedelta import relativedelta


def add_prev_day(tdf, insert_val = 0):
    prev_day = tdf.index[0] - datetime.timedelta(days = 1)
    tdf.loc[prev_day, :] = insert_val
    tdf = tdf.sort_index()
    return tdf

def get_monthly_ret_dict(tdf, ret_col, startdate = None, enddate = None):
    tdf = tdf.copy()
    prev_day = tdf.index[0] - datetime.timedelta(days = 1)
    tdf.loc[prev_day, ret_col] = 0
    tdf = tdf.sort_index()
    tdf["ret"] = np.cumprod(1+tdf[ret_col])
    mr = tdf.resample("M").last()[["ret"]].pct_change()
    if startdate is not None and enddate is not None:
        fd = pd.date_range(start=startdate, end=enddate, freq='M')
        mr = mr.loc[fd]
    target_ret_dict = mr["ret"].to_dict()
    return target_ret_dict

def compare_monthly_returns(rs_is, rs_oos, tdf, startdate = None, enddate = None):
    rrdf1 = rs_is.df.copy()
    rrdf2 = rs_oos.df.copy()
    is_ret_dict = get_monthly_ret_dict(rrdf1, "pret", startdate, enddate)
    oos_ret_dict = get_monthly_ret_dict(rrdf2, "pret", startdate, enddate)
    target_ret_dict = get_monthly_ret_dict(tdf, tdf.columns[0], startdate, enddate)
    ret_dict_combined = (target_ret_dict, is_ret_dict, oos_ret_dict)
    mr_df = pd.DataFrame(ret_dict_combined).T
    mr_df.columns = ["ACTUAL", "IS", "OOS"]
    
    return mr_df

def compare_series(rs_is, rs_oos, tdf, startdate, enddate, add_month_tolerance = True, return_actual = False):
    if add_month_tolerance:
        startdate = startdate.replace(day = 1) + relativedelta(months=1)
        enddate = enddate.replace(day = 1) - relativedelta(months=1) - datetime.timedelta(days = 1)
    tdf = tdf.resample("1D").last()
    rrdf1 = rs_is.df.copy()
    rrdf2 = rs_oos.df.copy()
    rdf = pd.concat([tdf[tdf.columns[0]], rrdf1, rrdf2], axis = 1).loc[startdate:enddate]
    # if force_common:
    #     u1 = rdf.isna().any(axis = 1)
    #     rdf = rdf.loc[~u1]
    rdf = add_prev_day(rdf, 0)
    crdf = np.cumprod(1+rdf)
    sdf = crdf
    sdf.columns = ["ACTUAL", "IS", "OOS"]  
    
    if return_actual:
        return sdf
    else:
        return sdf.interpolate(method='linear')



def get_weight_df(sim_obj):
    mdf = sim_obj.clean_meta_df
    dt = mdf["f1"].values[0]
    mdf2 = mdf[["Name", "weight"]]
    dt_str = pd.to_datetime(str(dt)).strftime('%Y-%m-%d')
    mdf2.columns = ["Name", dt_str]
    return mdf2.set_index("Name")

def get_overall_weight_df(sim_obj_list):
    weight_df_list = [get_weight_df(sim_obj) for sim_obj in sim_obj_list]
    weight_df = pd.concat(weight_df_list, axis = 1)
    return weight_df