# import os
# import query
# import pandas as pd
# import datetime
# import cxtpy.metrics_functions as mf
# from cxtpy.metrics_functions import *
# from cxtpy.metrics_functions import rolling_metrics
# import numpy as np
# import pandas as pd
# import functools

import os
import numpy as np
import pandas as pd

from data.series import RSeries, generate_date_list
from cxtpy.clean import df_list_merge
from cxtpy.general import init_dir

def select_single_series(series_class_df, name, column_name = "Name", silence = True):
    '''return the series object'''
    try:
        r = series_class_df.loc[series_class_df[column_name] == name]["Series"].iloc[0]
        return r
    except:
        if not silence:
            print("{} does not exist in series_class_df! Returning the first instance.".format(name))
        r = series_class_df["Series"].iloc[0]
        return r

def select_multiple_series(series_class_df, name_list, column_name = "Name", silence = True):
    '''return a list of series object'''
    r_list = series_class_df.loc[series_class_df[column_name].isin(name_list)]["Series"].values
    if len(r_list) == 0:
        if not silence:
            print("No instances match! Returning the first instance.")
        r_list = [series_class_df["Series"].values[0]]

    return r_list

def normalize_weights(weights_dict):
    total = sum(list(weights_dict.values()))
    for key, val in weights_dict.items():
        weights_dict[key] = weights_dict[key]/total
    return weights_dict

class RSeriesMulti():
    def __init__(self):
        self.all_rseries_list = []
        self.all_rseries_list_only = []
        self.all_rseries_df = pd.DataFrame(dict(Name = [], Series = [], SeriesType = [], ID = []))
        self.names = []

        self.multi_rolling_df_dict = dict()
        self.rolling_keys = []
        self.added_id_list = []

        self.silence = True

    def checkExistName(self, name):
        u1 = all_rseries_df.Name.isin([name])
        if u1.any():
            return True
        else:
            return False

    def CheckAddId(self, add_id):
        return add_id in self.added_id_list

    def AddSeries(self, rseries, add_id = None, replace = False):
        if add_id is not None:
            if add_id not in self.added_id_list:
                self.added_id_list.append(add_id)
            else:
                return

        entry = dict()
        entry["Series"] = rseries
        entry["ID"] = rseries.ID
        entry["Name"] = rseries.info["Name"]
        entry["SeriesType"] = rseries.info["SeriesType"]
        original_name = entry["Name"]

        if replace:
            u1 = self.all_rseries_df.Name.isin([entry["Name"]])
            self.all_rseries_df = self.all_rseries_df.loc[~u1] # Remove strategy of the same Name
        else:
            u1 = self.all_rseries_df.Name.isin([entry["Name"]])
            j = 0
            while u1.any():
                entry["Name"] = "{}_{}".format(original_name, j)
                u1 = self.all_rseries_df.Name.isin([entry["Name"]])
                j = j+1

        self.all_rseries_df = self.all_rseries_df.append(entry, ignore_index = True) # Add the latest strategy of the same Name
        self.all_rseries_list = list(self.all_rseries_df.to_dict(orient = "rows"))
        self.all_rseries_list_only = list(self.all_rseries_df["Series"].values)

        self.names = self.all_rseries_df.Name.values

    def AddCustomSeries(self, df, custom_series_name = None):
        rseries = RSeries()
        rseries.load_custom_series(df, custom_series_name)
        self.AddSeries(rseries)

    def GetMetadataList(self):
        return [rs.GetMetadata() for rs in self.all_rseries_list_only]

    def cachePickle(self, cache_folder = "cache", session_id = "test"):
        init_dir(cache_folder)
        init_dir(os.path.join(cache_folder, session_id))
        pkl_path = os.path.join(cache_folder, session_id, "all_rseries_df.pkl")

        if isinstance(self.all_rseries_df, list):
            print("Invalid/No Series Data. Skipping cache.")
        else:
            self.all_rseries_df["Name2"] = self.all_rseries_df["Name"].replace(regex = ["_"], value = "")
            self.all_rseries_df = self.all_rseries_df.sort_values("Name2")
            self.names = self.all_rseries_df["Name"].values
            strat_list = self.names
            added_id_list = self.added_id_list
            self.all_rseries_df.to_pickle(pkl_path)
            save_cache(item = strat_list, item_name = "strat_list", session_id = session_id, item_type = "value")
            save_cache(item = added_id_list, item_name = "added_id_list", session_id = session_id, item_type = "value")


    def readPickle(self, cache_folder = "cache", session_id = "test"):
        init_dir(cache_folder)
        init_dir(os.path.join(cache_folder, session_id))
        pkl_path = os.path.join(cache_folder, session_id, "all_rseries_df.pkl")
        try:
            self.all_rseries_df = pd.read_pickle(pkl_path)
            self.all_rseries_list = list(self.all_rseries_df.to_dict(orient = "rows"))
            self.all_rseries_list_only = list(self.all_rseries_df["Series"].values)
            self.names = self.all_rseries_df["Name"].values
            self.added_id_list = load_cache(item_name = "added_id_list", session_id = session_id, item_type = "value")
            return 1
        except Exception as err:
            if not self.silence:
                print(err)
                print("Error loading {}".format(pkl_path))
            return 0

    def ChangeDate(self, ISStartDate, ISEndDate, OOSEndDate):
        for rs in self.all_rseries_list_only:
            rs.init_dates(ISStartDate, ISEndDate, OOSEndDate)

    def FilterStrategyList(self, series_type_list = ["Strategy"]):
        return self.all_rseries_df.loc[self.all_rseries_df["SeriesType"].isin(series_type_list)]["Name"].values

    def SubsetSeries(self, name_list, column_name = "Name", force_list = False):
        if isinstance(name_list, list) or type(name_list) == type(np.array([1])):
            return select_multiple_series(self.all_rseries_df, name_list, column_name)
        else:
            if force_list:
                return select_single_series(self.all_rseries_df, [name_list], column_name)
            else:
                return select_single_series(self.all_rseries_df, name_list, column_name)

    def run_multi_rolling_metrics(self, strategy_list, benchmark, lookback):
        series_list = self.SubsetSeries(strategy_list, force_list = True)
        benchmark_series = self.SubsetSeries(benchmark, force_list = False)
        multi_rolling_df_dict = dict()
        for SSeries in series_list:
            multi_rolling_df_dict[SSeries.info["Name"]] = SSeries.get_rolling_metrics(benchmark_series.df, lookback)
        self.multi_rolling_df_dict = multi_rolling_df_dict
        self.rolling_keys = multi_rolling_df_dict[series_list[0].info["Name"]].columns

    def SubsetRollingMetrics(self, rolling_metrics_name):
        if len(self.multi_rolling_df_dict) == 0:
            print("RSeriesMulti.run_multi_rolling_metrics() has not been run!")
            return dict()
        sub_multi_rolling_df_dict = dict()
        for key, val in self.multi_rolling_df_dict.items():
            sub_multi_rolling_df_dict[key] = val[rolling_metrics_name]

        return sub_multi_rolling_df_dict

    def SubsetCumulativeReturns(self, strategy_list = None):
        if strategy_list is None:
            series_list = self.SubsetSeries(self.names, force_list = True)
        else:
            series_list = self.SubsetSeries(strategy_list, force_list = True)

        CR_dict = dict()
        for rs in series_list:
            key = rs.info["Name"]
            CR_dict[key] = rs.get_cumulative_returns()

        return CR_dict

    def get_metrics_by_intervals(self, metric_fun, startdate, enddate, lookback_days, skip_days):
        date_list = generate_date_list(startdate = startdate,
                                       enddate = enddate,
                                       lookback_days = lookback_days,
                                       skip_days = skip_days)
        d2_list = [j.get("d2") for j in date_list]

        m = {}
        for rs in self.all_rseries_list_only:
            m[rs.Name] = rs.get_metrics_by_date_list(date_list, metric_fun)
        mdf = pd.DataFrame(m).T
        mdf.columns = d2_list
        mdf = mdf.sort_index(axis = 1, ascending = True)
        mdf.columns = [j.strftime("%m/%d/%Y") for j in mdf.columns]
        mdf = mdf.reset_index()
        mdf = mdf.rename(columns = {"index": "Strategy"})
        self.date_list = date_list
        return mdf

    def get_df_combined(self, strategy_list = None, use_sample = "Overall", how = "outer", force_list = False):
        if strategy_list is None:
            strategy_list = self.all_rseries_df.Name.values
        rseries_sub_df = self.all_rseries_df.loc[self.all_rseries_df.Name.isin(strategy_list)]
        rseries_sub_list = rseries_sub_df.to_dict(orient = "rows")
        df_list = []
        for j in rseries_sub_list:
            temp_df = j.get("Series").df_dict.get(use_sample)
            temp_df.columns = [j.get("Name")]
            df_list.append(temp_df)

        if force_list:
            return df_list
        else:
            df_combined = df_list_merge(df_list, how)
            return df_combined

    def get_custom_weights_series(self, weights_dict, strategy_list = None, custom_series_name = "CustomSeries", daily_return_deduction = 0, norm_weights = True):
        try:
            if norm_weights:
                weights_dict = normalize_weights(weights_dict)
        except:
            print("Cannot normalize weights.")

        df_combined = self.get_df_combined(strategy_list = strategy_list).copy().fillna(0)
        df_weighted = df_combined*weights_dict
        custom_series = df_weighted.sum(axis = 1) - daily_return_deduction
        custom_df = pd.DataFrame(custom_series, columns=[custom_series_name])
        return custom_df

    def get_precoded_weights_dict(self, strategy_list = None, method = "Template"):
        weights = dict()
        if strategy_list is None:
            strategy_list = self.names

        if method == "Template":
            N = len(strategy_list)
            for j in strategy_list:
                weights[j] = 0
        elif method == "Equal":
            N = len(strategy_list)
            for j in strategy_list:
                weights[j] = 1/(N)
        elif method == "Risk Parity":
            volatility_dict = self.get_df_combined(strategy_list = strategy_list).std().to_dict()
            ss = 0
            for j in strategy_list:
                weights[j] = 1/volatility_dict[j]
                ss = ss + weights[j]

            for j in strategy_list:
                weights[j] = weights[j]/ss

        return weights
