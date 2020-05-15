import time
import datetime
import numpy as np
import pandas as pd

from data.series import RSeries
from data.multi_series import RSeriesMulti
from data.mongo_storage import MongoStorage
    
from cxtpy.metrics_functions import *
from rebalance.pc_helper import *

from rebalance.pc_allocate import risk_parity, sequential_distribute_min_weight, adjust_forced_min_weight
from rebalance.pc_allocate_second_layer import single_cluster, knn_cluster, two_layer_weight
from rebalance.optimize import OptimizeWeights
from rebalance.pc_optimize import *

from rebalance import optimize

import rebalance.pc_select as select
import rebalance.pc_allocate as allocate

from google.google_sheet import StrategyMeta

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
#         print("{}: {} seconds.".format(method.__name__.upper(), te-ts))
    return timed


def get_df_combined_from_rs_list(rs_list, d1 = datetime.datetime(2000,1,1), d2 = datetime.datetime(3000,1,1)):
    df_list = []
    for rs in rs_list:
        temp_df = rs.df.loc[d1:d2].copy()
        temp_df.columns = [rs.Name]
        df_list.append(temp_df)
    df_combined = df_list_merge(df_list, "outer")
    return df_combined


class PortfolioSimulation():
#     s1, s2 = None, None # select startdate, enddate
#     a1, a2 = None, None # allocate startdate, enddate 
#     b_startdate, b_enddate = None, None # backward/lookback startdate, enddate
#     f_startdate, f_enddate = None, None # forward/evaluate startdate, enddate
    meta_df = {}
    portfolio_df = {}
    metrics = {}
    MS = MongoStorage()
    logs = {}
    
    exclude_sample_meta_df = pd.DataFrame()
    exclude_corr_meta_df = pd.DataFrame()
    exclude_season_meta_df = pd.DataFrame()
    exclude_select_meta_df = pd.DataFrame()
    exclude_is_meta_df = pd.DataFrame()
    exclude_zerovariance_meta_df = pd.DataFrame()
    
    def __init__(self, kwargs, gen_weight = False, filter_dict = None):
        disable_exclude_1 = False if kwargs.get("disable_exclude_1") is None else kwargs.get("disable_exclude_1")
        disable_exclude_2 = False if kwargs.get("disable_exclude_2") is None else kwargs.get("disable_exclude_2")
        disable_exclude_3 = False if kwargs.get("disable_exclude_3") is None else kwargs.get("disable_exclude_3")
        disable_exclude_4 = True if kwargs.get("disable_exclude_4") is None else kwargs.get("disable_exclude_4")
        
        meta_df = {}
        portfolio_df = {}
        metrics = {}
        MS = MongoStorage()
        logs = {}
    
        self.s1 = s1 = kwargs.get("s1")
        self.s2 = s2 = kwargs.get("s2")
        self.a1 = a1 = kwargs.get("a1")
        self.a2 = a2 = kwargs.get("a2")
        self.f1 = f1 = kwargs.get("f1")
        self.f2 = f2 = kwargs.get("f2")
        
        n = kwargs.get("n")
        seed = kwargs.get("seed")
        corr_threshold = kwargs.get("corr_threshold")
        
#         select_method = kwargs.get("select_method")
#         allocate_method = kwargs.get("allocate_method")
        b_startdate, b_enddate = min(s1, a1), max(s2,a2)
        f_startdate, f_enddate = f1, f2
        
        if not gen_weight:
            sampling_f_enddate = f_enddate
        else:
            sampling_f_enddate = b_enddate
            
        self.SampleFromPopulation(b_startdate = b_startdate, f_enddate = sampling_f_enddate, n = n, seed = seed, filter_dict = filter_dict)
        if not disable_exclude_4:
            self.Exclude_IS(f_startdate = f_startdate)
        if not disable_exclude_2:
            self.Exclude_SeasonalityMonth(b_enddate = b_enddate, f_startdate = f_startdate, f_enddate = f_enddate)
        if not disable_exclude_3:
            self.Exclude_DM()
        if not disable_exclude_1:
            self.Exclude_HighCorrelation(b_enddate = b_enddate, corr_threshold = corr_threshold)
        
        
        if self.meta_df.shape[0] > 0:
            self.Select(**kwargs)
            self.ExcludeZeroVariance(**kwargs)
            self.Allocate(**kwargs)

        if not gen_weight:
            self.BackwardTest(b1 = a1, b2 = a2)
            # self.ForwardTest(**kwargs)
            self.ForwardTest(f1 = f1, f2 = f2)
            self.Evaluate()
            
        self.format_meta_df()

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
    
    def log(self, s, key = "Log"):
        self.logs[key] = s
        
    @timeit
    def SampleFromPopulation(self, b_startdate, f_enddate, n = None, seed = 123, filter_dict = None):
        if filter_dict is None:
            filter_dict = {"User": {"$nin": ["Deleted"], "$regex": "Live|Incubation"}, "StartDate": {"$lte": b_startdate}, "EndDate": {"$gte": f_enddate}}
        else:
            filter_dict["StartDate"] = {"$lte": b_startdate}
            filter_dict["EndDate"] = {"$gte": f_enddate}
            
        meta_list = [j for j in self.MS.FilterAndGetMetadata(filter_dict)]
        if len(meta_list) == 0:
            self.log("SampleFromPopulation: No strategies found!", "SampleFromPopulation")
            print("filter_dict:", filter_dict)
            raise Exception("No strategies found! (Likely due to date constraints)")
            return None
            
        df = pd.DataFrame(meta_list)
        
        df["filter"] = df.groupby("Name")["EndDate"].apply(lambda x: x==np.max(x))
        fdf = df[df["filter"]].sort_values("Name")
        fdf = fdf.set_index("Name")
        fdf = fdf.loc[~fdf.index.duplicated(keep='last')]
        fdf = fdf.reset_index()
        fdf_full = fdf.copy()
        
        if n is not None:
            if n < fdf_full.shape[0]:
                fdf = fdf_full.sample(n, random_state = seed).copy()
        
        self.exclude_sample_meta_df = fdf_full.loc[~fdf_full["Name"].isin(fdf["Name"]), :].copy()
            
        self.log("SampleStrategies: {}".format(str(fdf["Name"].values)), "SampleFromPopulation_2")
                
        fdf["rs"] = [self.MS.LoadAllSeriesFromId([_id])[0] for _id in fdf["_id"].values]
        self.meta_df = fdf
    
    @timeit
    def Exclude_HighCorrelation(self, b_enddate, corr_threshold = 0.8):
        rs_list = self.meta_df["rs"].values
        
        # Calculate correlation
        df_combined = get_df_combined_from_rs_list(rs_list = rs_list, d2 = b_enddate)
        cr = df_combined.corr().abs()
        
        # Remove strategy that has high correlation with others
        cr2 = (cr > corr_threshold) & (cr < 1)
        
        if cr2.any().any():
            ix, iy = np.where(cr2)
            to_remove_index = [x for x, y in zip(ix, iy) if x < y]
            corr_with_index = [y for x, y in zip(ix, iy) if x < y]
            to_remove_strat = [j for j in cr2.index[to_remove_index]]
            corr_with_strat = [j for j in cr2.index[corr_with_index]]
            
            self.log("Removing Highly Correlated Strategies: {}".format(str(to_remove_strat)), "Exclude_HighCorrelation_1")
            self.log("Highly Correlated With  -  Strategies: {}".format(str(corr_with_strat)), "Exclude_HighCorrelation_2")

            meta_df = self.meta_df 
            self.exclude_corr_meta_df = meta_df.loc[meta_df["Name"].isin(to_remove_strat)].copy()
            meta_df = meta_df.loc[~meta_df["Name"].isin(to_remove_strat)]
            self.meta_df = meta_df
        else:
            self.log("No Highly Correlated Strategies.", "Exclude_HighCorrelation_3")
    
    @timeit
    def Exclude_SeasonalityMonth(self, b_enddate, f_startdate, f_enddate, **kwargs):
        months_list = get_months_list(f_startdate, f_enddate)
        
        tradeable_list = []
        for rs in self.meta_df["rs"]:
            tradeable_month = get_tradeable_month(df = rs.df.loc[:b_enddate])
            tradeable = np.array([j in tradeable_month for j in months_list]).any()
            tradeable_list.append(tradeable)
        self.meta_df["tradable"] = tradeable_list
        
        
        self.exclude_season_meta_df = self.meta_df.loc[~self.meta_df["tradable"], :].copy()
        to_remove_strat = self.meta_df.loc[~self.meta_df["tradable"], "Name"].values
        self.log("Removing Inactive Seasonalities Strategies: {}".format(to_remove_strat), "Exclude_SeasonalityMonth")
        
        self.meta_df = self.meta_df.loc[self.meta_df["tradable"]]
        
    @timeit
    def Exclude_DM(self, **kwargs):
        u1 = self.meta_df["Name"].str.contains("DataMined")
        to_remove_strat = self.meta_df.loc[u1, "Name"].values
        self.log("Removing DataMined Strategies: {}".format(to_remove_strat), "Exclude_DM")
        self.meta_df = self.meta_df.loc[~self.meta_df["Name"].isin(to_remove_strat)]
    
    def Exclude_IS(self, f_startdate, **kwargs):
        SM = StrategyMeta()
        self.meta_df["DateAdded"] = self.meta_df["Name"].apply(lambda x: SM.get_date_from_name(x))
        self.meta_df["ValidOOS"] = self.meta_df["DateAdded"].apply(lambda x: f_startdate > x)
        self.exclude_is_meta_df = self.meta_df.loc[~self.meta_df["ValidOOS"], :].copy()
        to_remove_strat = self.meta_df.loc[~self.meta_df["ValidOOS"], "Name"].values
        self.log("Removing In-Sample Strategies: {}".format(to_remove_strat), "Exclude_IS")
        
        self.meta_df = self.meta_df.loc[self.meta_df["ValidOOS"]]
     
    @timeit
    def Select(self, select_method, s1, s2, **kwargs):
        strategy_list = self.meta_df["Name"].values
        rseries_list = self.meta_df["rs"].values
        
        if select_method == "Random":
            selected_strategy_list = select.Select_Random(strategy_list, **kwargs)
        elif select_method == "SharpeThreshold":
            selected_strategy_list = select.Select_SharpeThreshold(rseries_list, strategy_list, s1, s2, **kwargs)
        elif select_method == "RankAlphaSharpe":
            selected_strategy_list = select.Select_RankAlphaSharpe(rseries_list, strategy_list, s1, s2, **kwargs)
        elif select_method == "RankSharpe":
            selected_strategy_list = select.Select_RankSharpe(rseries_list, strategy_list, s1, s2, **kwargs)
        elif select_method == "RankPctSharpe":
            selected_strategy_list = select.Select_RankPctSharpe(rseries_list, strategy_list, s1, s2, **kwargs)
        elif select_method == "JY":
            selected_strategy_list = select.Select_JY(rseries_list, strategy_list, s1, s2, **kwargs)
        elif select_method == "All":
            selected_strategy_list = strategy_list
        else:
            print("select_method:", select_method, "not defined! Default to select all.")
            selected_strategy_list = strategy_list
        
        mdf = self.meta_df
        to_remove_strat = mdf.loc[~mdf["Name"].isin(selected_strategy_list), "Name"].values
        
        self.exclude_select_meta_df = mdf.loc[~mdf["Name"].isin(selected_strategy_list), :].copy()
        
        self.log("Selected {} strategies by {}: {}".format(len(selected_strategy_list), select_method, str(selected_strategy_list)), "Select_1")
        self.log("Removed {} strategies by {}: {}".format(len(to_remove_strat), select_method, str(to_remove_strat)), "Select_2")
        
        self.meta_df = mdf.loc[mdf["Name"].isin(selected_strategy_list)]
        
        
    def ExcludeZeroVariance(self, a1, a2, **kwargs):
        allocate_method = kwargs.get("allocate_method")
        risk_method = ["CRP", "CRPTail", "RiskParity", "AvgCMSCRP", "AvgCMSCRPT", "AvgCRPCRPT", "HRP", "CHRP"]
        if allocate_method not in risk_method:
            return 
        
        # Get df_combined and filter date range
        strategy_list = self.meta_df["Name"].values
        rseries_list = self.meta_df["rs"].values
        
        allocate_back_df = get_df_combined_from_rs_list(rs_list = rseries_list, d1 = a1, d2 = a2).fillna(0)
        to_remove_strat = allocate_back_df.columns[allocate_back_df.std(axis=0)==0].values
        
        mdf = self.meta_df
        
        self.exclude_zerovariance_meta_df = mdf.loc[mdf["Name"].isin(to_remove_strat), :].copy()
        
        self.log("Removing Zero Variance Strategies: {}".format(str(to_remove_strat)), "ExcludeZeroVariance")
        
        self.meta_df = mdf.loc[~mdf["Name"].isin(to_remove_strat)]
        
        
    @timeit
    def Allocate(self, allocate_method, a1, a2, **kwargs):
        # Get kwargs
        optimize_method = kwargs.get("optimize_method")
        cash_per_strat = kwargs.get("cash_per_strat")
        portfolio_value = kwargs.get("portfolio_value")
        lowerbound = kwargs.get("lowerbound")
        upperbound = kwargs.get("upperbound")
        constrain_weight = kwargs.get("constrain_weight")
        strat_min_alloc = kwargs.get("strat_min_alloc")
        # adj_lowerbound = kwargs.get("adj_lowerbound")
        
        # Set default for kwargs
        cash_per_strat = set_default(cash_per_strat, 10000)
        portfolio_value = set_default(portfolio_value, 1e6)
        lowerbound = set_default(lowerbound, 0.0)
        upperbound = set_default(upperbound, 0.1)
        constrain_weight = set_default(constrain_weight, 1)
        strat_min_alloc = set_default(strat_min_alloc, {})
#         adj_lowerbound = set_default(adj_lowerbound, 0.008)        
    
        adj_lowerbound = cash_per_strat/portfolio_value
    
        # Get df_combined and filter date range
        strategy_list = self.meta_df["Name"].values
        rseries_list = self.meta_df["rs"].values
        
#         print(a1,a2, len(strategy_list))
       
        df_list = [rs.df.copy() for rs in rseries_list]
        data_df = pd.DataFrame(dict(df = df_list, names = strategy_list))
        
        allocate_back_df = get_df_combined_from_rs_list(rs_list = rseries_list, d1 = a1, d2 = a2).fillna(0)
        
        # Optimize weights
        if allocate_method == "TwoLayer_KNN_RP":
            cluster_df = knn_cluster(data_df, a1, a2, **kwargs)
            w, wdf = two_layer_weight(data_df, a1, a2, cluster_df, allocation_method = "risk parity")
            
        elif allocate_method == "MaxSharpe": # Deprecated
            fun = Weights_MaxSharpe_fun(allocate_back_df)
            w, res = OptimizeWeights(allocate_back_df, fun, lowerbound = lowerbound, upperbound = upperbound, 
                                     method = optimize_method, tol = 1e-8, constraint = True)
        elif allocate_method == "CMS": # Constrained Max Sharpe
            fun = Weights_MaxSharpePenalty_fun(allocate_back_df)
            w, res = OptimizeWeights(allocate_back_df, fun, lowerbound = lowerbound, upperbound = upperbound, 
                                     method = optimize_method, tol = 1e-8, constraint = False)
        elif allocate_method == "RiskParity":
            sd_list = []
            for rs in rseries_list:
                rdf = rs.df.copy().loc[a1:a2]
                sd = rdf.std()[0]
                sd_list.append(sd)
            w = risk_parity(sd_list, upperbound = 1)
            w = {name:weight for name, weight in zip(strategy_list, w)}
            
        elif allocate_method == "CRPTail": # Constrained Risk Parity
            tail_p = kwargs.get("tail_p")
            tail_p = set_default(tail_p, 0.05)
            sd_list = []
            for rs in rseries_list:
                rdf = rs.df.copy().loc[a1:a2]
                sd = ETL(rdf.iloc[:, 0].values, tail_p)
                sd_list.append(sd)
            w = risk_parity(sd_list, upperbound = upperbound)
            w = {name:weight for name, weight in zip(strategy_list, w)}
        
        elif allocate_method == "CRP": # Constrained Risk Parity
            sd_list = []
            for rs in rseries_list:
                rdf = rs.df.copy().loc[a1:a2]
                sd = rdf.std()[0]
                sd_list.append(sd)
            w = risk_parity(sd_list, upperbound = upperbound)
            w = {name:weight for name, weight in zip(strategy_list, w)}
            
        elif allocate_method == "AvgCMSCRP": # Average of CMS and CRP
            CRP_Weight = kwargs.get("CRP_Weight")
            CRP_Weight = set_default(CRP_Weight, 1) 
            SumWeight = CRP_Weight + 1
            fun = Weights_MaxSharpePenalty_fun(allocate_back_df)
            w1, res = OptimizeWeights(allocate_back_df, fun, lowerbound = lowerbound, upperbound = upperbound, 
                                     method = optimize_method, tol = 1e-8, constraint = False)
            sd_list = []
            for rs in rseries_list:
                rdf = rs.df.copy().loc[a1:a2]
                sd = rdf.std()[0]
                sd_list.append(sd)
            w2 = risk_parity(sd_list, upperbound = upperbound)
            w2 = {name:weight for name, weight in zip(strategy_list, w2)}
            
            w = dict()
            for key, val in w1.items():
                w[key] = (w1[key] + CRP_Weight*w2[key])/(SumWeight)
        elif allocate_method == "AvgCMSCRPT": # Average of CMS and CRPTail
            fun = Weights_MaxSharpePenalty_fun(allocate_back_df)
            w1, res = OptimizeWeights(allocate_back_df, fun, lowerbound = lowerbound, upperbound = upperbound, 
                                     method = optimize_method, tol = 1e-8, constraint = False)
            tail_p = kwargs.get("tail_p")
            tail_p = set_default(tail_p, 0.05)
            sd_list = []
            for rs in rseries_list:
                rdf = rs.df.copy().loc[a1:a2]
                sd = ETL(rdf.iloc[:, 0].values, tail_p)
                sd_list.append(sd)
            w2 = risk_parity(sd_list, upperbound = upperbound)
            w2 = {name:weight for name, weight in zip(strategy_list, w2)}
            
            w = dict()
            for key, val in w1.items():
                w[key] = 0.5*(w1[key] + w2[key])
                
        elif allocate_method == "AvgCRPCRPT": # Average of CRP and CRPTail
            tail_p = kwargs.get("tail_p")
            tail_p = set_default(tail_p, 0.05)
            sd_list = []
            tail_sd_list = []
            for rs in rseries_list:
                rdf = rs.df.copy().loc[a1:a2]
                sd = rdf.std()[0]
                tail_sd = ETL(rdf.iloc[:, 0].values, tail_p)
                sd_list.append(sd)
                tail_sd_list.append(tail_sd)
            w = risk_parity(sd_list, upperbound = upperbound)
            w2 = risk_parity(tail_sd_list, upperbound = upperbound)
            
            w = {name:(weight2+weight)/2 for name, weight, weight2 in zip(strategy_list, w, w2)}
        elif allocate_method == "HRP":
            w = optimize.optimize_hrp(allocate_back_df)
            
        elif allocate_method == "CHRP":
            w = optimize.optimize_hrp(allocate_back_df)
            w2 = [j for j in w.values()]
            w2 = allocate.flatten_upperbound(w2, upperbound)
            for key,val in zip(w.keys(), w2):
                w[key] = val
                
        elif allocate_method == "EWMS":
            w = optimize.optimize_max_sharpe(allocate_back_df, 0, 1)
            
        elif allocate_method == "CEWMS":
            w = optimize.optimize_max_sharpe(allocate_back_df, lowerbound, upperbound)
        
        elif allocate_method == "EqualWeight":
            w = optimize.optimize_equal_weight(allocate_back_df)

        ### replicate index
        elif allocate_method == "Replicate_LookbackSquareError":
            target_ret = kwargs["target_ret"]
            if target_ret is None:
                raise Exception("target_ret not defined for Replicate_LookbackSquareError!")
            fun = Weights_MinTargetErr(allocate_back_df, target_ret)
            w, res = OptimizeWeights(allocate_back_df, fun, lowerbound = lowerbound, upperbound = upperbound, 
                                     method = optimize_method, tol = 1e-8, constraint = False)
            
        else:
            self.log("No such allocate_method: {}, default to EqualWeight".format(allocate_method), "Allocate")
            print("Default to EqualWeight")
            w = optimize.optimize_equal_weight(allocate_back_df)
        
        old_weights_list = [j for j in w.values()]
        if constrain_weight:
            weights_list = sequential_distribute_min_weight(old_weights_list.copy(), adj_lowerbound)
        else:
            weights_list = old_weights_list

        weights_dict = dict()
        for key, val in zip(w.keys(), weights_list):
            weights_dict[key] = val
            
        self.meta_df["old_weight"] = old_weights_list #old
        self.meta_df["weight"] = self.meta_df["Name"]
        self.meta_df["weight"] = self.meta_df["weight"].replace(weights_dict)
        self.meta_df = adjust_forced_min_weight(self.meta_df, strat_min_alloc) # adjustment for forced min weights
    
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