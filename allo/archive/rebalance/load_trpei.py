import datetime
import numpy as np
import pandas as pd 
from dateutil.relativedelta import relativedelta

def load_parse_trpei():
    df = pd.read_csv("_TRPEI.csv")
    df.columns = ["Year"] + [j+1 for j in range(12)] + ["Temp"]
    df = df.drop(["Temp"], axis = 1)
    df.set_index("Year", inplace = True)

    first_year = int(df.index[0])
    target_ret_dict = {}
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            dt = datetime.datetime(first_year + i, 1+j, 1) + relativedelta(months = 1) - datetime.timedelta(days = 1) 
            raw_val = df.iloc[i,j]
            if not df.isna().iloc[i,j]:
                ret = float(raw_val.replace("%", ""))/100
                target_ret_dict[dt] = ret
    tdf = pd.Series(target_ret_dict)
    tdf = pd.DataFrame(tdf)
    tdf.columns = ["TRPEI"]

    return target_ret_dict, tdf
