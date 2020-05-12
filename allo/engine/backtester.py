import time
import datetime
import numpy as np
import pandas as pd

from cxtpy.metrics_functions import *

from data.series import RSeries
from data.mongo_storage import MongoStorage

from helper.time import timeit
from excluder.excluder import Excluder
from selector.selector import Selector
from allocator.allocator import Allocator

# To-add features: use `pip install logzero` to log?


class Rebalancer():
    ### START Parameters needed: ###
    # 1. IS-EndDate/Lookback-EndDate: a2
    # 2. OOS-StartDate/Trading-StartDate: f1
    # 3. OOS-EndDate/Trading-EndDate: f2 
    # 4. Excluder parameters
    # 5. Selector parameters
    # 6. Allocator parameters
    # 7. Evaluator parameters
    ### END Parameters ###
    ### START Structure ###
    # Step 1: 
    ### END Structure ###
    ### Objects to store ###
    # Temporary 1. self....
    # 2. ...

    # Permanent 1.
    # 2. ...
    ### END Objects ###
    def __init__(self, **kwargs):

        pass


class Pipeline(object):
    
    # exclude_sample_meta_df = pd.DataFrame()
    # exclude_corr_meta_df = pd.DataFrame()
    # exclude_season_meta_df = pd.DataFrame()
    # exclude_select_meta_df = pd.DataFrame()
    # exclude_is_meta_df = pd.DataFrame()
    # exclude_zerovariance_meta_df = pd.DataFrame()
    # sample_kwargs = {"name":"population_sample", "kwargs":{"n": 150}}
    # excluder_kwargs = [ 
    #                     {"name": "excluder_correlation", "kwargs": {"corr_threshold": 0.6}}, 
    #                     {"name": "excluder_variance", "kwargs": {"threshold": 0.0001}}, 
    #                     {"name": "excluder_seasonality", "kwargs": {"threshold": 2}}
    #                 ] # apply each in sequence
    # selector_kwargs = {"select_method": "select_all"}
    # allocator_kwargs = {"allocate_method": "constrained_risk_parity", "adj_lowerbound": 0.008, "strat_min_alloc": {}}
    # evaluator_kwargs = {"f1": None, "f2": None}

    def __init__(self, s1, s2, a1, a2, f1, f2, 
                    excluder_kwargs, selector_kwargs, allocator_kwargs,
                    find_filter, sample_population_n = 10000,
                    sample_population_seed = 123, gen_weight = False, **kwargs):
        date_kwargs = self.construct_dates(s1, s2, a1, a2, 
                                            f1, f2, gen_weight) # Construct boundary dates for filtering population strategiess
        selector_kwargs = {**selector_kwargs, **date_kwargs}   
        allocator_kwargs = {**allocator_kwargs, **date_kwargs}   
        all_excluded_df_list = []

        self.MS = MongoStorage() # Initialize MongoStorage 
        meta_list = self.get_full_meta(find_filter, **date_kwargs) # Get full population metadata
        track_df, exclude_sample_meta_df = self.sample_from_population(meta_list, n = sample_population_n,
                                                                        seed = sample_population_seed) # Load data

        # Exclude, Select, Allocate                                                                        
        track_df, excluded_df_list = Excluder(track_df, date_kwargs, excluder_kwargs).get_output()
        track_df, exclude_select_meta_df = Selector(track_df, **selector_kwargs).get_output()
        track_df = Allocator(track_df, **allocator_kwargs).get_output()

        all_excluded_df_list.append(exclude_sample_meta_df)
        all_excluded_df_list += excluded_df_list
        all_excluded_df_list.append(exclude_select_meta_df)

        self.track_df, self.all_excluded_df_list = track_df, all_excluded_df_list

    def get_output(self):
        return self.track_df, self.all_excluded_df_list

    def construct_dates(self, s1, s2, a1, a2, f1, f2, gen_weight, **kwargs):
        b_startdate, b_enddate = min(s1, a1), max(s2,a2)
        f_startdate, f_enddate = f1, f2
        sampling_f_enddate = b_enddate if gen_weight else f_enddate
        date_kwargs = {
                        "s1": s1, "s2": s2, "a1": a1, "a2": a2, "f1": f1, "f2": f2, 
                        "b_startdate": b_startdate, "b_enddate": b_enddate, 
                        "f_startdate": f_startdate, "f_enddate": f_enddate
                        }
        return date_kwargs

    def get_full_meta(self, find_filter, b_startdate, f_enddate, **kwargs):
        # filter_dict = {"User": {"$nin": ["Deleted"], "$regex": user_regex_filter}, "StartDate": {"$lte": b_startdate}, "EndDate": {"$gte": f_enddate}}
        find_filter["StartDate"] = {"$lte": b_startdate}
        find_filter["EndDate"] = {"$gte": f_enddate}
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
        return fdf, exclude_sample_meta_df


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
    
    
        
    
    @timeit
    def ForwardTest(self, f1, f2, **kwargs):
        rs_list = self.meta_df["rs"].values
        w_list = self.meta_df["weight"].values
        
        dfc = get_df_combined_from_rs_list(rs_list = rs_list, d1 = f1, d2 = f2)
        allocated_df = dfc*w_list
        allocated_df = allocated_df.fillna(0)
        portfolio_df = pd.DataFrame(allocated_df.sum(axis = 1), columns = ["pret"])
        portfolio_df["pcret"] = cumulative_returns(portfolio_df["pret"])
        
        self.portfolio_df = portfolio_df.copy()

    @timeit
    def BackwardTest(self, b1, b2, **kwargs):
        rs_list = self.meta_df["rs"].values
        w_list = self.meta_df["weight"].values
        
        dfc = get_df_combined_from_rs_list(rs_list = rs_list, d1 = b1, d2 = b2)
        
        # todel1
        self.debug1 = dfc.copy()
        self.debug2 = self.meta_df["weight"]
        # todel2

        allocated_df = dfc*w_list
        allocated_df = allocated_df.fillna(0)
        portfolio_df = pd.DataFrame(allocated_df.sum(axis = 1), columns = ["pret"])
        portfolio_df["pcret"] = cumulative_returns(portfolio_df["pret"])
        
        self.is_portfolio_df = portfolio_df.copy()
        
    @timeit    
    def Evaluate(self):
        rs = RSeries()
        df = self.portfolio_df[["pret"]]
        rs.load_custom_series(df, custom_series_name = "PortfolioSegment", series_type = "PortfolioSegment")
        metrics = rs.get_metrics_by_date(d1 = df.index[0], d2 = df.index[-1])
        self.oos_metrics = metrics.copy()

        rs = RSeries()
        df = self.is_portfolio_df[["pret"]]
        rs.load_custom_series(df, custom_series_name = "PortfolioSegment", series_type = "PortfolioSegment")
        metrics = rs.get_metrics_by_date(d1 = df.index[0], d2 = df.index[-1])
        self.is_metrics = metrics.copy()

    
    def format_meta_df(self):
        mdf = self.meta_df.copy()
        mdf_rs = self.exclude_sample_meta_df
        mdf_e1 = self.exclude_corr_meta_df
        mdf_e2 = self.exclude_season_meta_df
        mdf_es = self.exclude_select_meta_df
        mdf_is = self.exclude_is_meta_df
        mdf_ezv = self.exclude_zerovariance_meta_df
        
        
        mdf["status"] = "selected"
        
        mdf_rs["status"] = "exclude_sample"
        mdf_rs["weight"] = 0
        mdf_e1["status"] = "exclude_corr"
        mdf_e1["weight"] = 0
        mdf_e2["status"] = "exclude_season"
        mdf_e2["weight"] = 0
        mdf_es["status"] = "exclude_select"
        mdf_es["weight"] = 0
        mdf_is["status"] = "exclude_is"
        mdf_is["weight"] = 0
        mdf_ezv["status"] = "exclude_zerovariance"
        mdf_ezv["weight"] = 0
        
        mdf = pd.concat([mdf, mdf_rs, mdf_e1, mdf_e2, mdf_es, mdf_is, mdf_ezv])
        try:
            mdf = mdf[["Name", "_id", "User", "StartDate", "EndDate", "DateAdded", "status", "weight"]]
        except:
            mdf = mdf[["Name", "_id", "User", "StartDate", "EndDate", "status", "weight"]] # quick fix on ExcludeIS (disabled = 1)
        
        mdf["s1"] = self.s1
        mdf["s2"] = self.s2
        mdf["a1"] = self.a1
        mdf["a2"] = self.a2
        mdf["f1"] = self.f1
        mdf["f2"] = self.f2

        self.clean_meta_df = mdf