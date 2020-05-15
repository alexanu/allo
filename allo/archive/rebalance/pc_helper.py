import datetime
import numpy as np
import pandas as pd
from cxtpy.metrics_functions import *
from dateutil.relativedelta import relativedelta

def robustness_index(df, **kwargs):
    # judge the robustness of the strategy up to that point (for selection, upgrade/demotion)
    roll_freq = 45
    roll_lookback = 90
    min_sharpe_expectation_1 = 0.6
    min_sharpe_expectation_2 = 0.8
    score1 = -5
    score2 = 1
    score3 = 2
    score4 = 3
    score5 = 2
    
    df = df.copy()
    d0 = df.first_valid_index()
    k = 0
    rolling_metrics_list = []
    while True:
        d1 = d0 + datetime.timedelta(roll_freq*k)
        d2 = d1 + datetime.timedelta(roll_lookback)
        if d2 > df.last_valid_index():
            break
        m = compute_metrics_with_benchmark(df=df.loc[d1:d2], df_bench=None)
        m["startdate"] = d1
        m["enddate"] = d2
        rolling_metrics_list.append(m)
        k = k + 1
    rdf2 = pd.DataFrame(rolling_metrics_list)
    
    rdf2["SharpeSMA"] = rdf2["Sharpe"].rolling(20).apply(lambda x: np.mean(x)).shift(1).fillna(min_sharpe_expectation_2)
    rdf2["SharpeExp"] = score1 + score2*(rdf2["Sharpe"] > 0) + score3*(rdf2["Sharpe"] > min_sharpe_expectation_1) + score4*(rdf2["Sharpe"] > min_sharpe_expectation_2) + score5*(rdf2["Sharpe"] > rdf2["SharpeSMA"])
    rdf2["SumSharpeExp"] = cumsum_ceiling(rdf2["SharpeExp"].values)
    robustness = rdf2["SumSharpeExp"].values[-1]

    return robustness

def cumsum_ceiling(x, lower = 0, upper = 100):
    ss = 100
    ss_list = []
    for j in x:
        ss = ss + float(j)
        if ss < 0:
            ss = 0
        elif ss > 100:
            ss = 100
        ss_list.append(ss)
    return ss_list
    
    
def ETL(x, p = 0.05):
    x = np.array(x)
    neg_ret = np.percentile(x, p*100)
    return np.mean(x[x < neg_ret])


def set_default(var, default):
    return default if var is None else var

def check_equal_weight(x):
    if np.max(x) - np.min(x) < 1e-3:
        return True
    else:
        return False
    
def generate_allocation_date(startdate, lastdate, weight_lookback, weight_forward, select_lookback):
    refstartdate = lastdate
    refenddate = lastdate
    date_dict_list = []
    while refstartdate > startdate:
        s1 = refenddate - datetime.timedelta(select_lookback + weight_forward) # Selection lookback startdate
        s2 = refenddate - datetime.timedelta(weight_forward + 1) # Selection lookback enddate
        a1 = refenddate - datetime.timedelta(weight_lookback + weight_forward) # Allocation lookback startdate
        a2 = refenddate - datetime.timedelta(weight_forward + 1) # Allocation lookback enddate
        m1 = refenddate - datetime.timedelta(weight_forward) # Forward Evaluation startdate
        m2 = refenddate # Forward Evaluation enddate
        
        refenddate = a2
        refstartdate = min(a1, s1)
        date_dict = dict(
                         select_back_startdate = s1, select_back_enddate = s2, 
                         allocate_back_startdate = a1, allocate_back_enddate = a2, 
                         fwd_startdate = m1, fwd_enddate = m2
                    )
        date_dict_list.append(date_dict)

    return date_dict_list

def generate_monthly_allocation_date(startdate, enddate, allocate_lookback_num_month = 1):
    # assume allocate_lookback_num_month = 1 for now
    diff = enddate - startdate 
    num_months = int(diff.days/30) + 2
    startdate_list = [startdate.replace(day = 1) + relativedelta(months=j) for j in range(num_months)]
    filtered_startdate_list = [j for j in startdate_list if j >= startdate and j < (enddate - relativedelta(months=1)).replace(day = 1)]
    date_dict_list = []
    for a1 in filtered_startdate_list:
        a2 = a1 + relativedelta(months=1) - datetime.timedelta(days = 1)
        f1 = a1 + relativedelta(months=1) 
        f2 = a1 + relativedelta(months=2) - datetime.timedelta(days = 1)
        date_dict = dict(
                            select_back_startdate = a1, select_back_enddate = a2, 
                            allocate_back_startdate = a1, allocate_back_enddate = a2, 
                            fwd_startdate = f1, fwd_enddate = f2
                        )
        date_dict_list.append(date_dict)

    return date_dict_list

def get_tradeable_month(df):
    df2 = df.copy()
    column_name = df2.columns[0]
    df2["month"] = df2.index.month
    tradeable_df = df2.groupby("month")[column_name].apply(lambda x: np.mean(x==0)) < 1 
    trade_month = tradeable_df.loc[tradeable_df].index
    buffer_month = trade_month-1
    add_buffer = [j for j in buffer_month[~buffer_month.isin(trade_month)] if j != 0]
    new_trade_month = np.concatenate([add_buffer, trade_month])
    return new_trade_month

def get_months_list(d1, d2):
    diff_days = (d2 - d1).days + 1
    date_list = [d1 + datetime.timedelta(j) for j in range(diff_days)]
    month_list = np.unique([j.month for j in date_list])
    return month_list
    