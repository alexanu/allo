import datetime
import pandas as pd
import pytz
from bson.codec_options import CodecOptions

def dtnow(timezone = 'US/Eastern'):
    date_now = datetime.datetime.now(pytz.timezone(timezone))
    return date_now

def dt(YY = 2019, MM = 7, DD = 11, hh = 0, mm = 0, ss = 0, timezone = "US/Eastern"):
    localtz = pytz.timezone(timezone)
    my_date = datetime.datetime(YY,MM,DD,hh,mm,ss)
    my_date = localtz.localize(my_date)
    return my_date

# def collection_to_df(coll_cursor, auto_find_datetime = True, time_columns=[], initial_tz='UTC', converted_tz='US/Eastern'):
#     df = pd.DataFrame([j for j in coll_cursor])
#     if df.shape[0] == 0:
#         return df
    
#     if auto_find_datetime:
#         dt_col = [str(j).find("datetime") != -1 for j in df.dtypes]
#         time_columns = df.columns[dt_col]
        
#     for j in time_columns:
#         df[j] = df[j].dt.tz_localize(initial_tz)
#         df[j] = df[j].dt.tz_convert(converted_tz)      

#     return df 


def get_collection(db, coll_name, timezone = "US/Eastern"):
    coll = db[coll_name].with_options(codec_options=CodecOptions(
                                         tz_aware=True,
                                         tzinfo=pytz.timezone('US/Eastern')))
    return coll