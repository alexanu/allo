import time
import datetime
import numpy as np
import pandas as pd

# from cxtpy.metrics_functions import *
from data.mongo_storage import MongoStorage

from helper.time import timeit
from excluder.excluder import Excluder
from selector.selector import Selector
from allocator.allocator import Allocator


# To-add features: use `pip install logzero` to log?
class SingleIntervalAllocator(object):
    # Example args:
    # s1, s2 = datetime.datetime(2017,1,1), datetime.datetime(2018,1,1)
    # a1, a2 = datetime.datetime(2018,1,1), datetime.datetime(2019,1,1)
    # f1, f2 = datetime.datetime(2019,1,1), datetime.datetime(2019,6,1)
    # find_filter, sample_threshold = 2
    # sample_population_n = 10000
    # sample_population_seed = 123
    # gen_weight = False
    # excluder_kwargs = [ 
    #                     {"name": "exclude_high_correlation", "kwargs": {"corr_threshold": 0.9}}, 
    #                     {"name": "exclude_seasonality_month", "kwargs": {}}, 
    #                     {"name": "exclude_data_mined", "kwargs": {}}
    #                 ] # apply each in sequence
    # selector_kwargs = {"select_method": "select_all"}
    # allocator_kwargs = {"allocate_method": "constrained_risk_parity", "upperbound": 0.3, "adj_lowerbound": 0.008, "strat_min_alloc": {}}
    # evaluator_kwargs = {"f1": None, "f2": None}

    def __init__(self, s1, s2, a1, a2,
                    excluder_kwargs, selector_kwargs, allocator_kwargs,
                    find_filter, sample_threshold = 2, 
                    sample_population_n = 10000, sample_population_seed = 123, 
                    f1 = None, f2 = None, **kwargs):
        date_kwargs = self.construct_dates(s1, s2, a1, a2, f1, f2) # Construct boundary dates for filtering population strategiess
        selector_kwargs = {**selector_kwargs, **date_kwargs}   
        allocator_kwargs = {**allocator_kwargs, **date_kwargs}   
        excluded = {}
        
        self.MS = MongoStorage() # Initialize MongoStorage 
        meta_list = self.get_full_meta(find_filter, **date_kwargs) # Get full population metadata
        if len(meta_list) > sample_threshold:
            track_df, excluded_0 = self.sample_from_population(meta_list, n = sample_population_n, seed = sample_population_seed)

            # Exclude, Select, Allocate                                                                        
            track_df, excluded_1 = Excluder(track_df, date_kwargs, excluder_kwargs).get_output()
            track_df, excluded_2 = Selector(track_df, **selector_kwargs).get_output()
            track_df = Allocator(track_df, **allocator_kwargs).get_output()
            excluded = {**excluded_0, **excluded_1, **excluded_2}

            self.track_df, self.excluded = track_df, excluded

    def get_output(self):
        return self.subset_track_df(self.track_df), self.excluded

    def construct_dates(self, s1, s2, a1, a2, f1, f2, **kwargs):
        startdate, enddate = min(s1, a1), max(s2,a2)
        date_kwargs = {
                        "s1": s1, "s2": s2, "a1": a1, "a2": a2, 
                        "f1": f1, "f2": f2,
                        "startdate": startdate, "enddate": enddate
                        }
        return date_kwargs

    def get_full_meta(self, find_filter, startdate, enddate, **kwargs):
        # filter_dict = {"User": {"$nin": ["Deleted"], "$regex": user_regex_filter}, "StartDate": {"$lte": b_startdate}, "EndDate": {"$gte": f_enddate}}
        find_filter["StartDate"] = {"$lte": startdate}
        find_filter["EndDate"] = {"$gte": enddate}
        meta_list = [j for j in self.MS.Find(find_filter)]
        new_meta_list = pd.DataFrame(meta_list).sort_values("EndDate").groupby("Name").last().reset_index().to_dict(orient="records")
        if len(meta_list) > len(new_meta_list):
            print("DUPLICATES FOUND! Duplicates will be removed...")
        # self.meta_list = meta_list #debug
        return new_meta_list

    def sample_from_population(self, meta_list, n = 10000, seed = 123, **kwargs):
        """Sample from population strategies, return id_list for loading."""
        if len(meta_list) == 0:
            # self.log("SampleFromPopulation: No strategies found!", "SampleFromPopulation")
            raise Exception("No strategies found! (Likely due to date constraints)")

        fdf = df = pd.DataFrame(meta_list)
        N = df.shape[0]
        
        exclude_sample_meta_df = pd.DataFrame()
        if n >= N:
            full_meta = meta_list
        else:
            df["filter"] = df.groupby("Name")["EndDate"].apply(lambda x: x==np.max(x))
            fdf = df[df["filter"]].sort_values("Name")
            fdf = fdf.set_index("Name")
            fdf = fdf.loc[~fdf.index.duplicated(keep='last')]
            fdf = fdf.reset_index()
            fdf_full = fdf.copy()
            fdf = fdf_full.sample(n, random_state = seed).copy()
            exclude_sample_meta_df = fdf_full.loc[~fdf_full["Name"].isin(fdf["Name"]), :].copy()

        # self.log("SampleStrategies: {}".format(str(fdf["Name"].values)), "SampleFromPopulation_2")
        id_list = [_id for _id in fdf["_id"].values]
        fdf["rs"] = [self.MS.Load([_id])[0] for _id in fdf["_id"].values]
        excluded = {}
        excluded['exclude_sample'] = exclude_sample_meta_df
        return fdf, excluded

    def subset_track_df(self, track_df):
        needed_columns = ["Name", "StartDate", "OOSDate","EndDate", "_id"]
        p1 = track_df.loc[:,track_df.columns.str.startswith("weight")]
        p2 = track_df.loc[:,needed_columns]
        sub_track_df = pd.concat([p2, p1], axis = 1)
        return sub_track_df

    # if self.meta_df.shape[0] > 0:
    #     self.Select(**kwargs)
    #     self.ExcludeZeroVariance(**kwargs)
    #     self.Allocate(**kwargs)

    # if not gen_weight:
    #     self.BackwardTest(b1 = a1, b2 = a2)
    #     # self.ForwardTest(**kwargs)
    #     self.ForwardTest(f1 = f1, f2 = f2)
    #     self.Evaluate()
        
    # self.format_meta_df()

        # Debug
#         try:
#             if self.meta_df.shape[0] > 0:
#                 self.Select(**kwargs)
#                 self.ExcludeZeroVariance(**kwargs)
#                 self.Allocate(**kwargs)

#             if not gen_weight:
#                 self.ForwardTest(**kwargs)
#                 self.Evaluate()

#             self.format_meta_df()
#         except Exception as err:
#             print("Debug:", err)
    
    
        
    
    # @timeit
    # def ForwardTest(self, f1, f2, **kwargs):
    #     rs_list = self.meta_df["rs"].values
    #     w_list = self.meta_df["weight"].values
        
    #     dfc = get_df_combined_from_rs_list(rs_list = rs_list, d1 = f1, d2 = f2)
    #     allocated_df = dfc*w_list
    #     allocated_df = allocated_df.fillna(0)
    #     portfolio_df = pd.DataFrame(allocated_df.sum(axis = 1), columns = ["pret"])
    #     portfolio_df["pcret"] = cumulative_returns(portfolio_df["pret"])
        
    #     self.portfolio_df = portfolio_df.copy()

    # @timeit
    # def BackwardTest(self, b1, b2, **kwargs):
    #     rs_list = self.meta_df["rs"].values
    #     w_list = self.meta_df["weight"].values
        
    #     dfc = get_df_combined_from_rs_list(rs_list = rs_list, d1 = b1, d2 = b2)
        
    #     # todel1
    #     self.debug1 = dfc.copy()
    #     self.debug2 = self.meta_df["weight"]
    #     # todel2

    #     allocated_df = dfc*w_list
    #     allocated_df = allocated_df.fillna(0)
    #     portfolio_df = pd.DataFrame(allocated_df.sum(axis = 1), columns = ["pret"])
    #     portfolio_df["pcret"] = cumulative_returns(portfolio_df["pret"])
        
    #     self.is_portfolio_df = portfolio_df.copy()
        
    # @timeit    
    # def Evaluate(self):
    #     rs = RSeries()
    #     df = self.portfolio_df[["pret"]]
    #     rs.load_custom_series(df, custom_series_name = "PortfolioSegment", series_type = "PortfolioSegment")
    #     metrics = rs.get_metrics_by_date(d1 = df.index[0], d2 = df.index[-1])
    #     self.oos_metrics = metrics.copy()

    #     rs = RSeries()
    #     df = self.is_portfolio_df[["pret"]]
    #     rs.load_custom_series(df, custom_series_name = "PortfolioSegment", series_type = "PortfolioSegment")
    #     metrics = rs.get_metrics_by_date(d1 = df.index[0], d2 = df.index[-1])
    #     self.is_metrics = metrics.copy()

    
    # def format_meta_df(self):
    #     mdf = self.meta_df.copy()
    #     mdf_rs = self.exclude_sample_meta_df
    #     mdf_e1 = self.exclude_corr_meta_df
    #     mdf_e2 = self.exclude_season_meta_df
    #     mdf_es = self.exclude_select_meta_df
    #     mdf_is = self.exclude_is_meta_df
    #     mdf_ezv = self.exclude_zerovariance_meta_df
        
        
    #     mdf["status"] = "selected"
        
    #     mdf_rs["status"] = "exclude_sample"
    #     mdf_rs["weight"] = 0
    #     mdf_e1["status"] = "exclude_corr"
    #     mdf_e1["weight"] = 0
    #     mdf_e2["status"] = "exclude_season"
    #     mdf_e2["weight"] = 0
    #     mdf_es["status"] = "exclude_select"
    #     mdf_es["weight"] = 0
    #     mdf_is["status"] = "exclude_is"
    #     mdf_is["weight"] = 0
    #     mdf_ezv["status"] = "exclude_zerovariance"
    #     mdf_ezv["weight"] = 0
        
    #     mdf = pd.concat([mdf, mdf_rs, mdf_e1, mdf_e2, mdf_es, mdf_is, mdf_ezv])
    #     try:
    #         mdf = mdf[["Name", "_id", "User", "StartDate", "EndDate", "DateAdded", "status", "weight"]]
    #     except:
    #         mdf = mdf[["Name", "_id", "User", "StartDate", "EndDate", "status", "weight"]] # quick fix on ExcludeIS (disabled = 1)
        
    #     mdf["s1"] = self.s1
    #     mdf["s2"] = self.s2
    #     mdf["a1"] = self.a1
    #     mdf["a2"] = self.a2
    #     mdf["f1"] = self.f1
    #     mdf["f2"] = self.f2

    #     self.clean_meta_df = mdf