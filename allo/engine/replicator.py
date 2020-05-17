import time
import datetime
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from sklearn.metrics import mean_squared_error, mean_absolute_error

from cxtpy.metrics_functions import cumulative_returns_last
from engine.single_interval_allocator import SingleIntervalAllocator
from engine.rebalancer import Rebalancer
from data_parser import load_parse
from analysis.analyze_replicate import compare_monthly_returns, compare_series
from data.series import RSeries



class Replicator(Rebalancer):
    # Parameters:
    # startdate
    # enddate
    # index: e.g. "trpei"
    # single_config: subset of "example_replicator_config.yaml"

    def __init__(self, startdate, enddate, index, lookback_num_month, 
                    add_drift = 0, **single_config):
        self.startdate = startdate
        self.enddate = enddate
        self.output = []
        target_ret_dict, self.tdf = load_parse.get(index)()
        date_packet_list = self.construct_rebalance_date_list(startdate, enddate, lookback_num_month)
        for date_packet in date_packet_list: # allocate sequentially
            current_single_config = {**single_config, **date_packet}
            a1, a2 = date_packet.get("a1"), date_packet.get("a2")
            target_ret = cumulative_returns_last(self.tdf.loc[a1:a2].values.flatten())
            current_single_config["allocator_kwargs"]["target_ret"] = target_ret + add_drift
            track_df, excluded, forward_df = SingleIntervalAllocator(**current_single_config).get_output()
            self.save_output(track_df, excluded, date_packet, forward_df)
        self.fdf = self.construct_entire_series()    
        self.post_processing()
        
    def construct_rebalance_date_list(self, startdate, enddate, lookback_num_month, **kwargs):
        # assume allocate_lookback_num_month = 1 for now
        diff = enddate - startdate 
        num_months = int(diff.days/30) + 10
        startdate_list = [startdate.replace(day = 1) + relativedelta(months=j) for j in range(num_months)]
        filtered_startdate_list = [j for j in startdate_list if j >= startdate and j < (enddate - relativedelta(months=lookback_num_month)).replace(day = 1)]
        date_packet_list = []
        for a1 in filtered_startdate_list:
            a2 = a1 + relativedelta(months=lookback_num_month) - datetime.timedelta(days = 1)
            f1 = a1 + relativedelta(months=lookback_num_month) 
            f2 = a1 + relativedelta(months=lookback_num_month+1) - datetime.timedelta(days = 1)
            date_packet = {"a1": a1, "a2": a2, "s1": a1, "s2": a2, "f1": f1, "f2": f2}
            date_packet_list.append(date_packet)
        return date_packet_list

    def get_analysis(self):
        tdf = self.tdf
        rs_oos = self.rs
        mr_df = compare_monthly_returns(rs_oos, tdf).loc[self.startdate:self.enddate]
        cp_df = compare_series(rs_oos, tdf).loc[self.startdate:self.enddate]
        
        rs = RSeries()
        rs.load_custom_series(cp_df[["ACTUAL"]].pct_change())
        actual_metrics = rs.get_metrics()["Overall"]

        rs = RSeries()
        rs.load_custom_series(cp_df[["OOS"]].pct_change())
        allo_metrics = rs.get_metrics()["Overall"]

        # allo_metrics = self.rs.get_metrics()["Overall"]
        metrics_df = pd.DataFrame(dict(actual = actual_metrics, replica = allo_metrics)) # may not be meaningful! (because of linear interpolation on actual series)

        mr_df = mr_df.dropna()
        rmse = np.sqrt(mean_squared_error(mr_df["ACTUAL"], mr_df["OOS"]))
        mae = mean_absolute_error(mr_df["ACTUAL"], mr_df["OOS"])
        oos_ret = mr_df["OOS"]
        mean_neg = np.mean(oos_ret[oos_ret < 0])
        print("RMSE:", rmse)
        print("mae:", mae)
        print("mean_neg:", mean_neg)

        return mr_df, cp_df, metrics_df
