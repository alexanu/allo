import datetime
import numpy as np
import pandas as pd

from data.series import RSeries
from data.multi_series import RSeriesMulti
from data.mongo_storage import MongoStorage
from rebalance.single_simulation import PortfolioSimulation
from rebalance.pc_helper import generate_allocation_date, generate_monthly_allocation_date

from cxtpy.metrics_functions import *
from rebalance.analyze_replicate import compare_monthly_returns, compare_series, get_overall_weight_df

from multiprocessing import Pool

class FullPortfolioSimulation():
#     sim_kwargs = {"n": 60, "seed": 123, "corr_threshold": 0.8, "select_method": "SharpeThreshold", "sharpe_threshold": 0.5, "allocate_method": "AvgCMSCRP",
#                 "select_lookback": 45, "allocate_lookback": 45, "evaluate_forward": 45, "startdate": datetime.datetime(2017,1,1), "enddate": datetime.datetime(2019,1,1)
#              }
    logs = dict()
    random_sampling_for_each_interval = True
    sim_name = ""
    result_rs_list = []
    startdate = None
    enddate = None
    total_simulation = 1
    save = False
    
    def __init__(self, sim_name, save = False, bypass_check = False, client = "local"):
        self.save = save
        self.sim_name = sim_name
        if save and not bypass_check:
            MS = MongoStorage(client = None)
            db = MS.client["AnalysisEvo"]
            coll = db["Simulation"]
            existing_sim_name = coll.distinct("extra.sim_name")
            if sim_name in existing_sim_name:
                raise KeyError("{} already existed in db.AnalysisEvo.Simulation!".format(sim_name))
        
    def log(self, sim_custom_name, f2, message):
        date_str = f2.strftime("%Y%m%d")
        if self.logs.get(sim_custom_name) is None:
            self.logs[sim_custom_name] = dict()
        self.logs[sim_custom_name][date_str] = message
        
    def MultiSimulation(self, total_simulation, **sim_kwargs):
        self.startdate = sim_kwargs.get("startdate")
        self.enddate = sim_kwargs.get("enddate")
        self.total_simulation = total_simulation
        
        sim_name = self.sim_name
        
        rs_list = []
        for j in range(total_simulation):
            sim_kwargs["seed"] = j*10000
            sim_kwargs["sim_name"] = sim_name
            rs = self.SingleSimulation(**sim_kwargs)
            rs_list.append(rs)
        self.result_rs_list = rs_list
    
    def SingleSimulation(self, select_lookback, allocate_lookback, evaluate_forward, startdate, enddate, filter_dict = {}, custom_name = "", **sim_kwargs):
        # custom_name = "Sim_{}_{}".format(sim_kwargs.get("sim_name"), sim_kwargs.get("seed"))
        
        ### SPLIT DATA INTO N INTERVALS ###
        ### EACH INTERVAL CONTAINS A LOOKBACK FOR SELECTION AND ALLOCATION, AND A FORWARD EVALUATION PERIOD  ###
        ### LOOP ###
        result_date_dict_list = generate_allocation_date(startdate, enddate, allocate_lookback, evaluate_forward, select_lookback)
        oos_portfolio_df_list = []
        is_portfolio_df_list = []
        
        original_seed = sim_kwargs["seed"]

        counter = 0
        sim_obj_list = []
        for dd in result_date_dict_list:
            s1, s2 = dd.get("select_back_startdate"), dd.get("select_back_enddate")
            a1, a2 = dd.get("allocate_back_startdate"), dd.get("allocate_back_enddate")
            f1, f2 = dd.get("fwd_startdate"), dd.get("fwd_enddate")
            
            sim_kwargs["seed"] = original_seed + counter
            date_kwargs = dict(s1 = s1, s2 = s2, a1 = a1, a2 = a2, f1 = f1, f2 = f2)
            interval_kwargs = {**date_kwargs, **sim_kwargs}
            PS = None
            PS = PortfolioSimulation(kwargs = interval_kwargs, filter_dict = filter_dict)
            sim_obj_list.append(PS)
            oos_portfolio_df_list.append(PS.portfolio_df.copy()[["pret"]])
            is_portfolio_df_list.append(PS.is_portfolio_df.copy()[["pret"]])
            
            self.log(custom_name, f2, PS.logs.copy())
            counter = counter + 1
        
        sim_kwargs["original_seed"] = original_seed
        
        ### END OF LOOP ###
        # oos_portfolio_df = pd.concat(oos_portfolio_df_list).sort_index()
        # is_portfolio_df = pd.concat(is_portfolio_df_list).sort_index()
        oos_portfolio_df = pd.concat(oos_portfolio_df_list)
        oos_portfolio_df = oos_portfolio_df.groupby(oos_portfolio_df.index).first().sort_index()
        is_portfolio_df = pd.concat(is_portfolio_df_list)
        is_portfolio_df = is_portfolio_df.groupby(is_portfolio_df.index).first().sort_index()

        rs_oos = RSeries()
        rs_oos.load_custom_series(oos_portfolio_df[["pret"]], custom_series_name = "OOS_{}".format(custom_name), series_type = "Allocation")
        rs_is = RSeries()
        rs_is.load_custom_series(is_portfolio_df[["pret"]], custom_series_name = "IS_{}".format(custom_name), series_type = "Allocation")

        if custom_name != "":
            oos_kw, is_kw = sim_kwargs.copy(), sim_kwargs.copy()
            oos_kw["Sample"], is_kw["Sample"] = "OOS", "IS"
            rs_oos.SaveSeries(user=custom_name, extra = oos_kw.copy())
            rs_is.SaveSeries(user=custom_name, extra = is_kw.copy())

        self.rs_is, self.rs_oos, self.sim_obj_list = rs_is, rs_oos, sim_obj_list
        print("Successful.")


    def SingleMonthlySimulationWithTarget(self, startdate, enddate, target_ret_dict, filter_dict = {}, **sim_kwargs):
        custom_name = "Sim_{}_{}".format(sim_kwargs.get("sim_name"), sim_kwargs.get("seed"))
        
        ### SPLIT DATA INTO N INTERVALS ###
        ### EACH INTERVAL CONTAINS A LOOKBACK FOR SELECTION AND ALLOCATION, AND A FORWARD EVALUATION PERIOD  ###
        ### LOOP ###
        result_date_dict_list = generate_monthly_allocation_date(startdate, enddate)
        oos_portfolio_df_list = []
        is_portfolio_df_list = []
        
        original_seed = sim_kwargs["seed"]
        
        counter = 0
        sim_obj_list = []
        for dd in result_date_dict_list:
            s1, s2 = dd.get("select_back_startdate"), dd.get("select_back_enddate")
            a1, a2 = dd.get("allocate_back_startdate"), dd.get("allocate_back_enddate")
            f1, f2 = dd.get("fwd_startdate"), dd.get("fwd_enddate")
            
            target_ret = target_ret_dict.get(a2)
            sim_kwargs["seed"] = original_seed + counter
            date_kwargs = dict(s1 = s1, s2 = s2, a1 = a1, a2 = a2, f1 = f1, f2 = f2)
            interval_kwargs = {**date_kwargs, **sim_kwargs}
            interval_kwargs["target_ret"] = target_ret
            PS = None
            PS = PortfolioSimulation(kwargs = interval_kwargs, filter_dict = filter_dict)
            sim_obj_list.append(PS)
            oos_portfolio_df_list.append(PS.portfolio_df.copy()[["pret"]])
            is_portfolio_df_list.append(PS.is_portfolio_df.copy()[["pret"]])

            self.log(custom_name, f2, PS.logs.copy())
            counter = counter + 1
        
        sim_kwargs["original_seed"] = original_seed
        
        ### END OF LOOP ###
        # oos_portfolio_df = pd.concat(oos_portfolio_df_list).sort_index() 
        # is_portfolio_df = pd.concat(is_portfolio_df_list).sort_index()
        # solve duplicated date index when allocate lookback != evaluation fwd
        oos_portfolio_df = pd.concat(oos_portfolio_df_list)
        oos_portfolio_df = oos_portfolio_df.groupby(oos_portfolio_df.index).first().sort_index()
        is_portfolio_df = pd.concat(is_portfolio_df_list)
        is_portfolio_df = is_portfolio_df.groupby(is_portfolio_df.index).first().sort_index()

        rs_oos = RSeries()
        rs_oos.load_custom_series(oos_portfolio_df[["pret"]], custom_series_name = custom_name, series_type = "Simulation")
        rs_is = RSeries()
        rs_is.load_custom_series(is_portfolio_df[["pret"]], custom_series_name = custom_name, series_type = "Simulation")
        
        # if self.save:
        #     rs.SaveSeries(user="Public", extra = sim_kwargs.copy(), db_name = "AnalysisEvo", coll_name = "Simulation")
        self.rs_is, self.rs_oos, self.sim_obj_list = rs_is, rs_oos, sim_obj_list
        print("Successful.")

        # return rs_is, rs_oos, sim_obj_list
    
    def AnalyzeMSWT(self, tdf, startdate, enddate):
        rs_is, rs_oos, sim_obj_list = self.rs_is, self.rs_oos, self.sim_obj_list
        mr_df = compare_monthly_returns(rs_is, rs_oos, tdf, startdate, enddate)
        cp_df = compare_series(rs_is, rs_oos, tdf, startdate, enddate)
        weight_df = get_overall_weight_df(sim_obj_list)

        # cp_df.corr()
        # cp_df.plot()
        # weight_df
        return mr_df, cp_df, weight_df

    def ExtractWeights(self):
        weight_df = get_overall_weight_df(self.sim_obj_list)

        return weight_df

    def CompareSamples(self):
        compare_df = pd.concat([self.rs_is.df, self.rs_oos.df], axis = 1)
        compare_df.columns = ["IS_ret", "OOS_ret"]
        compare_df["IS_cret"] = np.cumprod(compare_df["IS_ret"] + 1)
        compare_df["OOS_cret"] = np.cumprod(compare_df["OOS_ret"] + 1)
        compare_df["IS_cret"] = compare_df["IS_cret"].fillna(method = "ffill")
        compare_df["OOS_cret"] = compare_df["OOS_cret"].fillna(method = "ffill")
        return compare_df

    def ExtractMetrics(self, d1 = None, d2 = None, metric_fun = "Sharpe"):
        d1 = self.startdate if d1 is None else d1
        d2 = self.enddate if d2 is None else d2
        m_list=[]
        for rs in self.result_rs_list:
            m_list.append(rs.get_metrics_by_date_2(d1=d1, d2=d2, metric_fun=metric_fun))
        return m_list

    def LoadFromMongo(self, find_filter, db_name = "AnalysisEvo", coll_name = "Simulation", client = "local"):
        MS = MongoStorage(client = client)
        meta_list = [j for j in MS.FilterAndGetMetadata(find_filter = find_filter, db_name = db_name, coll_name = coll_name)]
        if len(meta_list) == 0:
            raise ValueError("Could not find any simulation series from the given find_filter!")
            
        original_seed_list = [j.get("extra").get("original_seed") for j in meta_list]
        id_list = [j.get("_id") for j in meta_list]
        
        meta_df = pd.DataFrame(dict(original_seed = original_seed_list, _id = id_list)).sort_values("original_seed")
        self.result_rs_list = [MS.LoadAllSeriesFromId([j], db_name = db_name, coll_name = coll_name)[0] for j in meta_df["_id"].values]
        self.startdate = meta_list[0].get("extra").get("startdate")
        self.enddate = meta_list[0].get("extra").get("enddate")

    
class StatisticalTest():
    def __init__(self, FPS1, FPS2, d1 = None, d2 = None, sig_threshold = 0.05):
        if len(FPS1.result_rs_list) != len(FPS2.result_rs_list):
            raise ValueError("Total Simulation is not the same. Aborting comparison!")
        else:
            self.d1 = d1
            self.d2 = d2
            self.summary_pair_df = self.pair_table(FPS1, FPS2, sig_threshold)
            self.summary_df_1 = self.self_table(FPS1)
            self.summary_df_2 = self.self_table(FPS2)
    
    def self_table(self, FPS):
        metrics_fun_list = ["CAGR", "Volatility", "Sharpe", "Calmar", "Sortino", "Positive Periods", "Average Positive", "Average Negative", "ETL", "Max Drawdown"]
        positive_is_good = [1, 0, 1, 1, 1, 0, 0, 0, 0, 0]
        
        summary_list = []
        for metric in metrics_fun_list:
            m_list_1 = FPS.ExtractMetrics(metric_fun = metric, d1 = self.d1, d2 = self.d2)
            mdf = pd.DataFrame(dict(m1 = m_list_1))
            mdf["d"] = mdf["m1"]
            summary = mdf["d"].describe().to_dict()
            summary["Metric"] = metric
            summary_list.append(summary)
            
        sdf = pd.DataFrame(summary_list)
        sdf = sdf.set_index("Metric")
        sdf = sdf[["mean", "std", "min", "25%", "50%", "75%", "max"]]

        return sdf
        
    def pair_table(self, FPS1, FPS2, sig_threshold = 0.05):
        metrics_fun_list = ["CAGR", "Volatility", "Sharpe", "Calmar", "Sortino", "Positive Periods", "Average Positive", "Average Negative", "ETL", "Max Drawdown"]
        positive_is_good = [1, -1, 1, 1, 1, 1, 1, 1, 1, 1]
        
        summary_list = []
        for metric in metrics_fun_list:
            m_list_1 = FPS1.ExtractMetrics(metric_fun = metric, d1 = self.d1, d2 = self.d2)
            m_list_2 = FPS2.ExtractMetrics(metric_fun = metric, d1 = self.d1, d2 = self.d2)
            mdf = pd.DataFrame(dict(m1 = m_list_1, m2 = m_list_2))
            mdf["d"] = mdf["m1"] - mdf["m2"]
            summary = mdf["d"].describe().to_dict()
            summary["greater_pct"] = (mdf["d"] > 0).mean()

            t_test = stats.ttest_rel(mdf["m1"].values, mdf["m2"].values)
            summary["t-statistic"] = t_test.statistic

            if t_test.pvalue >= sig_threshold:
                summary["sign"] = "=="
            else:
                if t_test.statistic > 0:
                    summary["sign"] = ">>"
                else:
                    summary["sign"] = "<<"
            summary["Metric"] = metric
            summary_list.append(summary)
            
        sdf = pd.DataFrame(summary_list)
        sdf["positive_is_good"] = positive_is_good
        sdf["better"] = sdf["t-statistic"]*sdf["positive_is_good"] > 0 
        sdf["better"] = sdf["better"].replace(dict(better = {True:"better", False:"worse"}))
        sdf = sdf.set_index("Metric")
        sdf = sdf[["mean", "std", "min", "25%", "50%", "75%", "max", "greater_pct", "t-statistic", "sign", "better"]]
        
        return sdf
    