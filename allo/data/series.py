import os, uuid
import datetime
import functools
import pymongo
import numpy as np
import pandas as pd

import cxtpy.metrics_functions as mf
from cxtpy.metrics_functions import * ###TOFIX
from cxtpy.metrics_functions import rolling_metrics

from data.mongo_datetime import dt, dtnow, get_collection
from data.init_mongo import InitMongo

def truncate_initial_zeros(df):
    tdf = df.copy()
    tdf[tdf==0] = np.nan
    tdf = tdf.loc[tdf.first_valid_index():].fillna(0)
    return tdf

def generate_date_list(startdate, enddate, lookback_days, skip_days):
    refstartdate = enddate
    refenddate = enddate
    date_dict_list = []
    while refstartdate > startdate:
        s2 = refenddate
        s1 = s2 - datetime.timedelta(lookback_days)

        refenddate = s2 - datetime.timedelta(skip_days+1)
        refstartdate = refenddate - datetime.timedelta(lookback_days)
        date_dict = dict(d1 = s1, d2 = s2)
        date_dict_list.append(date_dict)

    return date_dict_list

class RSeries():
    def __init__(self):
        self.info = dict()
        self.df = pd.DataFrame()
        self.df_dict = dict()
        self.User = "Public"
        self.SavedDate = None
        self.Name = None
        self.ShortName = None
        self.SeriesType = None
        self.ISStartDate = None
        self.ISEndDate = None
        self.OOSEndDate = None
        self.ID = str(uuid.uuid4())
        self.metrics = dict()
        self.Saved = False


    def load_ninja_strat(self, file, df = None):
        try:
            if isinstance(file, str) and df is None:
                df = pd.read_csv(file)
            df.Date = pd.to_datetime(df.Date)
            df = df[["Date", "Daily Return"]].set_index("Date")
            df.columns = [os.path.basename(file).split(".")[0]]

            df = df.fillna(0)
            df.sort_index(inplace = True)

            self.df = df
            self.get_default_date(df)

            self.info["csv"] = file
            self.info["csv_basename"] = os.path.basename(file)
            self.info["SeriesType"] = "Strategy"
            self.info["Name"] = os.path.basename(file).split(".")[0]
            self.Name = self.info["Name"]
            self.SeriesType = self.info["SeriesType"]

            self.init_df_dict()
        except Exception as err:
            print("Error at load_ninja_strat:", file, "--", err)

    def load_custom_series(self, df, custom_series_name = None, series_type = "Custom"):
        df = df.fillna(0)
        df.sort_index(inplace = True)
#         df = truncate_initial_zeros(df)

        if custom_series_name is None:
            custom_series_name = df.columns[0]

        self.df = df
        self.get_default_date(df)

        self.info["SeriesType"] = series_type
        self.info["Name"] = custom_series_name

        self.User = "Public"
        self.Name = custom_series_name
        self.SeriesType = series_type

        self.init_df_dict()

    def load_from_mongo(self, doc):
        data = doc.get("data")
        self.User = doc.get('User')
        self.SavedDate = doc.get('SavedDate')
        self.Name = doc.get('Name')
        self.ShortName = doc.get('ShortName')
        self.info = doc.get('info')
        self.SeriesType = self.info["SeriesType"]
        self.ISStartDate = doc.get('StartDate')
        self.ISEndDate = doc.get('OOSDate')
        self.OOSEndDate = doc.get('EndDate')

        df = pd.DataFrame(data).set_index("Date").sort_index()
        self.df = df

        self.init_df_dict()

    def get_default_date(self, df):
        self.ISStartDate = df.first_valid_index()
        ISEnd1 = df.last_valid_index() - datetime.timedelta(days=180)
        ISEnd2 = df.first_valid_index() + (df.last_valid_index() - df.first_valid_index())*0.8
        self.ISEndDate = ISEnd1 if ISEnd1 > df.first_valid_index() else ISEnd2
        self.OOSEndDate = df.last_valid_index()


    def init_dates(self, ISStartDate, ISEndDate, OOSEndDate):
        ISStartDate = pd.to_datetime(ISStartDate)
        ISEndDate = pd.to_datetime(ISEndDate)
        OOSEndDate = pd.to_datetime(OOSEndDate)

        ISEndDate1 = ISEndDate
        ISEndDate2 = ISStartDate + (OOSEndDate - ISStartDate)*0.8
        if ISEndDate1 > ISStartDate and ISEndDate1 < OOSEndDate:
            ISEndDate = ISEndDate1
        else:
            print("ISEndDate is outside of ISStartDate and OOSEndDate. Using 20% OOSDate.")
            ISEndDate = ISEndDate2

        self.ISStartDate = ISStartDate
        self.ISEndDate = ISEndDate
        self.OOSEndDate = OOSEndDate

        self.init_df_dict()


    def init_df_dict(self):
        self.df_dict["Overall"] = self.df.loc[self.ISStartDate:self.OOSEndDate]
        self.df_dict["IS"] = self.df.loc[self.ISStartDate:self.ISEndDate]
        self.df_dict["OOS"] = self.df.loc[self.ISEndDate:self.OOSEndDate]


    def get_metrics_by_date_2(self, d1, d2, metric_fun = "Sharpe"):
        df = self.df.copy()
        sdf = df.loc[d1:d2].copy()
        fun = metrics_call.get(metric_fun)
        if fun is None:
            print("No such metrics function in metrics_call:", metric_fun)
            return None
        try:
            m = fun(sdf.iloc[:, 0].values)
        except:
            m = np.nan
        return m

    def get_metrics_by_date_list(self, date_list, metric_fun = "Sharpe"):
        df = self.df.copy()
        metrics_list = []
        for date_dict in date_list:
            d1 = date_dict.get("d1")
            d2 = date_dict.get("d2")
            sdf = df.loc[d1:d2].copy()
            fun = metrics_call.get(metric_fun)
            if fun is None:
                print("No such metrics function in metrics_call:", metric_fun)
                return None
            try:
                m = fun(sdf.iloc[:, 0].values)
            except:
                m = np.nan
            metrics_list.append(m)
        return metrics_list

    def get_alpha_metrics_by_date(self, d1, d2, benchmark_df, volatility_lookback = 90, **kwargs):
        Overall_df = self.df
        d1 = pd.to_datetime(d1)
        d0 = d1 - datetime.timedelta(volatility_lookback*2)
        d2 = pd.to_datetime(d2)
        df = Overall_df.loc[(Overall_df.index >= d0) & (Overall_df.index <= d2)]
        alpha_df = mf.generate_alpha_series(df = df, df_bench = benchmark_df, volatility_lookback = volatility_lookback)
        alpha_df = alpha_df.loc[d1:d2]
        m = mf.compute_metrics(alpha_df["alpha"])
        return m

    def get_metrics_by_date(self, d1, d2, benchmark_df = None):
        Overall_df = self.df_dict["Overall"]
        d1 = pd.to_datetime(d1)
        d2 = pd.to_datetime(d2)
        df = Overall_df.loc[(Overall_df.index > d1) & (Overall_df.index <= d2)]
        try:
            metrics = compute_metrics_with_benchmark(df=df, df_bench=benchmark_df)
        except:
            metrics = {}
        return metrics
    
    def get_alpha_metrics(self, benchmark_df, volatility_lookback = 90, **kwargs):
        alpha_df = mf.generate_alpha_series(df = self.df, df_bench = benchmark_df, volatility_lookback = volatility_lookback)
        
        samples = ["Overall", "IS", "OOS"]
        date_dict = dict(Overall = (self.ISStartDate, self.OOSEndDate), IS = (self.ISStartDate, self.ISEndDate),
                         OOS = (self.ISEndDate, self.OOSEndDate))
        
        self.alpha_metrics = dict()
        for s in samples:
            try:
                d1, d2 = date_dict[s]
                self.alpha_metrics[s] = compute_metrics_with_benchmark(df=alpha_df.loc[d1:d2], df_bench=benchmark_df)
            except:
                self.alpha_metrics[s] = compute_metrics_with_benchmark(df=df, df_bench=benchmark_df)
                for key, val in self.alpha_metrics[s].items():
                    self.alpha_metrics[s][key] = np.nan
                    
        return self.alpha_metrics
    
    def get_metrics(self, benchmark_df = None):
#         Overall_df = self.df.loc[self.ISStartDate:self.OOSEndDate]
#         IS_df = self.df.loc[self.ISStartDate:self.ISEndDate]
#         OOS_df = self.df.loc[self.ISEndDate:self.OOSEndDate]
        Overall_df = self.df_dict["Overall"]
        IS_df = self.df_dict["IS"]
        OOS_df = self.df_dict["OOS"]

        self.metrics = dict()
        self.metrics["Overall"] = compute_metrics_with_benchmark(df=Overall_df, df_bench=benchmark_df)
        self.metrics["IS"] = compute_metrics_with_benchmark(df=IS_df, df_bench=benchmark_df)
        self.metrics["OOS"] = compute_metrics_with_benchmark(df=OOS_df, df_bench=benchmark_df)

        return self.metrics
    
    def get_alpha_cumulative_returns(self, benchmark_df, volatility_lookback = 90, **kwargs):
        use_df = self.df_dict["Overall"]
        alpha_df = mf.generate_alpha_series(df = use_df, df_bench = benchmark_df, volatility_lookback = volatility_lookback)
        cumret_list = cumulative_returns(alpha_df.values)
        self.alpha_cumret_series = pd.Series(cumret_list, index = alpha_df.index)
        return self.alpha_cumret_series
    
    def get_alpha_drawdown(self):
        drawdown_list = drawdown(self.alpha_cumret_series.values)
        self.drawdown_series = pd.Series(drawdown_list, index = self.alpha_cumret_series.index)
        return self.drawdown_series
    
    def get_cumulative_returns(self):
        use_df = self.df_dict["Overall"]
        cumret_list = cumulative_returns(use_df.values)
        self.cumret_series = pd.Series(cumret_list, index = use_df.index)
        return self.cumret_series

    def get_drawdown(self):
        use_df = self.df_dict["Overall"]
        drawdown_list = drawdown(self.cumret_series.values)
        self.drawdown_series = pd.Series(drawdown_list, index = use_df.index)
        return self.drawdown_series

    def get_rolling_metrics(self, benchmark_df, lookback, use_sample = "Overall"):
        df_use = self.df_dict[use_sample]
        strat_name = df_use.columns[0]
        bench_name = benchmark_df.columns[0]
        if strat_name == bench_name:
            df_combined = df_use.copy()
        else:
            df_combined = pd.merge(df_use, benchmark_df, left_index = True, right_index = True)

        roll_df = rolling_metrics(df_combined, strat_name, lookback, bench_name)
        return roll_df

    def GetMetadata(self):
        meta_dict = dict(
                    User = self.User,
                    SavedDate = self.SavedDate,
                    Name = self.Name,
                    SeriesType = self.SeriesType,
                    StartDate = self.ISStartDate,
                    OOSDate = self.ISEndDate,
                    EndDate = self.OOSEndDate,
                    ID = self.ID
                )
        return meta_dict

    def UpdateMetadata(self, meta_dict):
        self.User = meta_dict.get("User")
        self.SavedDate = meta_dict.get("SavedDate")
        self.Name = meta_dict.get("Name")
        self.SeriesType = meta_dict.get("SeriesType")
        self.ISStartDate = meta_dict.get("StartDate")
        self.ISEndDate = meta_dict.get("OOSDate")
        self.OOSEndDate = meta_dict.get("EndDate")

    def SaveSeries(self, user="Public", extra = None, db_name = "AnalysisEvo", coll_name = "Strategy", client = None):
        try:
            if not self.Saved:
                client = InitMongo(client)
                db = client[db_name]
                coll = db[coll_name]
                d = dict(
                        User = user,
                        SavedDate = dtnow(),
                        Name = self.info.get("Name"),
                        ShortName = self.info.get("Name")[0:8],
                        SeriesType = self.info.get("SeriesType"),
                        info = self.info,
                        StartDate = self.ISStartDate,
                        OOSDate = self.ISEndDate,
                        EndDate = self.OOSEndDate,
                        data = self.df.reset_index().to_dict(orient = "rows"),
                        metrics = self.metrics,
                        extra = extra
                    )
                coll.insert_one(d)
                self.Saved = True
                return True
            else:
                print("{} has been saved before!".format(self.Name))
                return False
        except Exception as err:
            print("Error at SaveSeries in RSeries: {}".format(err))
            return False

#     def __init__(self, df, info):
#         self.df = df
#         self.info = info

        #SeriesType: Strategy/Benchmark/Custom
            #Strategy:
                #AnalyzeDate
                #StrategyName
                #TrueOOSDate
                #ISStartDate
                #ISEndDate
                #OOSEndDate
                #AssetTraded
                #StrategyTypeLabels
                #MarketDirection
                #CurrentStatus
                #SavedMetrics
            #Benchmark/Custom:

                #AssetTraded
