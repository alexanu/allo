import datetime
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta


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
    