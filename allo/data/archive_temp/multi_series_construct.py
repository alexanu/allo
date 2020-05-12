# PortfolioConstruction is DEPRECATED, try to port SampleStrategy to RSeriesMulti
import datetime
import numpy as np
import pandas as pd

from data.series import RSeries
from data.multi_series import RSeriesMulti
from data.mongo_storage import MongoStorage

# from pc_helper import generate_allocation_date, check_equal_weight, set_default
from rebalance.pc_helper import * ###TOFIX
from rebalance.pc_select import *
from rebalance.optimize import OptimizeWeights
from rebalance.pc_optimize import *
from rebalance.pc_allocate import *
from rebalance.optimize_metrics import P_SHARPE

from cxtpy.metrics_functions import *

class PortfolioConstruction(RSeriesMulti):
    Result = {}
    rs_df = {}

    def SampleStrategy(self, random_n_sample = None, filter_dict = {}, dont_load = False):
        if filter_dict is None:
            filter_dict = {"User": {"$nin": ["Deleted"]}, "Name": {"$regex": "_[0-9]{4}_"}}

        MS = MongoStorage()
        meta_list = [j for j in MS.FilterAndGetMetadata(filter_dict)]
        df = pd.DataFrame(meta_list)
        df["filter1"] = df.groupby("Name")["SavedDate"].apply(lambda x: x==np.max(x)) # conflicting
        df["filter2"] = df.groupby("Name")["EndDate"].apply(lambda x: x==np.max(x))
        df["filter"] = df["filter2"] #& df["filter1"]
        fdf = df[df["filter"]].sort_values("Name")
        fdf = fdf.set_index("Name")
        fdf = fdf.loc[~fdf.index.duplicated(keep='last')]
        fdf = fdf.reset_index()

        if random_n_sample is not None:
            fdf = fdf.sample(random_n_sample)
        id_list = fdf["_id"].values
        name_list = fdf["Name"].values

        if dont_load:
            return name_list
        else:
            status = [self.AddSeries(j) for j in MS.LoadAllSeriesFromId(id_list)]
        # Result = PC.SelectAndAllocateOverTime(**kwargs)

    def SelectAndAllocateOverTime(self, select_method, allocate_method, weight_lookback, weight_forward, select_lookback, startdate = None, lastdate = None, **kwargs):

        ### INITIALIZE DATA ###
        last_index = kwargs.get("last_index")
        filter_seriestype = kwargs.get("filter_seriestype")
        filter_seriestype = ["Strategy"] if filter_seriestype is None else filter_seriestype

        filter_strategy_list = self.FilterStrategyList(series_type_list = filter_seriestype)
        df = self.get_df_combined(strategy_list = filter_strategy_list).fillna(0).copy()

        # Setting the startdate and lastdate (change lastdate for robustness testing)
        if startdate is None:
            startdate = df.first_valid_index()
        else:
            startdate = startdate - datetime.timedelta(weight_lookback)
        if lastdate is None:
            lastdate = df.last_valid_index()
        df = df.loc[startdate:lastdate]

        Result = dict()
        ### END OF INITIALIZATION ###

        ### SPLIT DATA INTO N INTERVALS ###
        ### EACH INTERVAL CONTAINS A LOOKBACK FOR SELECTION AND ALLOCATION, AND A FORWARD EVALUATION PERIOD  ###
        ### LOOP ###
        result_date_dict_list = generate_allocation_date(startdate, lastdate, weight_lookback, weight_forward, select_lookback)
        result_date_dict_list = result_date_dict_list[0:last_index]

        counter = 0
        for dd in result_date_dict_list:
            s1, s2 = dd.get("select_back_startdate"), dd.get("select_back_enddate")
            a1, a2 = dd.get("allocate_back_startdate"), dd.get("allocate_back_enddate")
            f1, f2 = dd.get("fwd_startdate"), dd.get("fwd_enddate")
            rs_df = self.all_rseries_df.copy()
            rs_df["Selected"] = 1
            bwd_df = df.loc[a1:a2]
            fwd_df = df.loc[f1:f2]

            # FILTER
            rs_df.loc[~rs_df["Name"].isin(filter_strategy_list), "Selected"] = 0
            dd["Filter_Selected"] = filter_strategy_list

            # EXCLUSION
            rs_df, exclusion_selected_strategy_list = self.Exclude(rs_df, f1, f2)
            dd["Exclusion_Selected"] = exclusion_selected_strategy_list

            # SELECTION
            rs_df, selected_strategy_list = self.Select(select_method, rs_df, s1, s2, **kwargs)
            dd["Selected"] = selected_strategy_list

            # ALLOCATION
            weights, rs_df = self.Allocate(allocate_method, rs_df, a1, a2, **kwargs)
            dd["rs_df"] = rs_df
            dd["Weights"] = weights

            # WEIGHTS ADJUSTMENT


            # EVALUATION
            weights_list = [j for j in weights.values()]
            if check_equal_weight(weights_list):
                print("WARNING: OPTIMIZER DOES NOT CONVERGE - STUCK AT EQUAL WEIGHTS! Counter:", counter)

            final_selected_strategy_list = rs_df.loc[rs_df["Selected"] == 1, "Name"].values
            dd["interval_optimized_fwd_df"] = weights_list*fwd_df[final_selected_strategy_list]
            dd["interval_fwd_sharpe"] = P_SHARPE(weights_list, fwd_df[final_selected_strategy_list])
            dd["interval_bwd_sharpe"] = P_SHARPE(weights_list, bwd_df[final_selected_strategy_list])

            counter = counter + 1

        Result["Intervals"] = result_date_dict_list
        ### END OF LOOP ###

        ### COMBINE INTERVALS ###
        ### Generate Portfolio Equity Curve ###
        try:
            Result["Portfolio_DF"] = self.GetPortfolioDF(result_date_dict_list)
            Result["Portfolio_Returns"] = Result["Portfolio_DF"].sum(axis = 1)
            Result["Portfolio_Equity"] = cumulative_returns(Result["Portfolio_Returns"])
            Result["Portfolio_Equity"] = pd.Series(Result["Portfolio_Equity"], index = Result["Portfolio_Returns"].index)
            rs = RSeries()
            df = pd.DataFrame(Result["Portfolio_Returns"], columns = ["Portfolio_Returns"])
            rs.load_custom_series(df, custom_series_name = "Portfolio", series_type = "Portfolio")
            Result["RSeries"] = rs
            Result["Metrics"] = rs.get_metrics_by_date(d1 = startdate, d2 = lastdate)
            Result["SetupName"] = kwargs.get("setup_name")
        except Exception as err:
            print(err)

        ### END OF COMBINE ###
        self.Result = Result

        return Result

    def GenWeight(self):
        rs_df = self.all_rseries_df.copy()
        rs_df["Selected"] = 1
        bwd_df = df.loc[a1:a2]
        fwd_df = df.loc[f1:f2]

        # FILTER
        rs_df.loc[~rs_df["Name"].isin(filter_strategy_list), "Selected"] = 0
        dd["Filter_Selected"] = filter_strategy_list

        # EXCLUSION
        rs_df, exclusion_selected_strategy_list = self.Exclude(rs_df, f1, f2)
        dd["Exclusion_Selected"] = exclusion_selected_strategy_list

        # SELECTION
        rs_df, selected_strategy_list = self.Select(select_method, rs_df, s1, s2, **kwargs)
        dd["Selected"] = selected_strategy_list

        # ALLOCATION
        weights, rs_df = self.Allocate(allocate_method, rs_df, a1, a2, **kwargs)
        dd["rs_df"] = rs_df
        dd["Weights"] = weights

        # WEIGHTS ADJUSTMENT

    def Exclude(self, rs_df, d1, d2, **kwargs):
        months_list = get_months_list(d1, d2)
        exclusion_selected_strategy_list = []
        rs_list = rs_df.Series.values
        rs_name_list = rs_df.Name.values
        for rs, name in zip(rs_list, rs_name_list):
            tradeable_month = get_tradeable_month(df = rs.df)
            tradeable = np.array([j in tradeable_month for j in months_list]).any()
            if tradeable:
                exclusion_selected_strategy_list.append(name)
        rs_df.loc[~rs_df["Name"].isin(exclusion_selected_strategy_list), "Selected"] = 0

        return rs_df, exclusion_selected_strategy_list

    def Select(self, select_method, rs_df, s1, s2, **kwargs):
        strategy_list = rs_df.loc[rs_df["Selected"] == 1]["Name"].values
        rseries_list = rs_df.loc[rs_df["Selected"] == 1]["Series"].values
        if select_method == "Random":
            selected_strategy_list = Select_Random(strategy_list, **kwargs)
        elif select_method == "RankSharpe":
            selected_strategy_list = Select_RankSharpe(rseries_list, strategy_list, s1, s2, **kwargs)
        elif select_method == "JY":
            selected_strategy_list = Select_JY(rseries_list, strategy_list, s1, s2, **kwargs)
        else:
            selected_strategy_list = []
        rs_df.loc[~rs_df["Name"].isin(selected_strategy_list), "Selected"] = 0
        return rs_df, selected_strategy_list


    def Allocate(self, allocate_method, rs_df, a1, a2, **kwargs):
        # Get kwargs
        optimize_method = kwargs.get("optimize_method")
        lowerbound = kwargs.get("lowerbound")
        upperbound = kwargs.get("upperbound")

        # Set default for kwargs
        optimize_method = set_default(optimize_method, "TNC")
        lowerbound = set_default(lowerbound, 0)
        upperbound = set_default(upperbound, 0.1)

        # Get df_combined and filter date range
        strategy_list = rs_df.loc[rs_df["Selected"] == 1]["Name"].values
        rseries_list = rs_df.loc[rs_df["Selected"] == 1]["Series"].values
        allocate_back_df = self.get_df_combined(strategy_list = strategy_list).fillna(0).copy().loc[a1:a2]

        # Optimize weights
        if allocate_method == "MaxSharpe": # Deprecated
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
                w[key] = 0.5*(w1[key] + w2[key])
        else:
            print("No such allocate_method:", allocate_method)
            w, res = None, None

        weights_list = [j for j in w.values()]
        rs_df.loc[rs_df["Selected"] == 1, "Weights"] = weights_list

        return w, rs_df

    def GetPortfolioDF(self, result_date_dict_list):
        portfolio_df = pd.concat([j.get("interval_optimized_fwd_df") for j in result_date_dict_list])
        portfolio_df = portfolio_df.sort_index()

        return portfolio_df
