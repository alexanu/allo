import time
import datetime
import numpy as np
import pandas as pd

from data.series import RSeries
from cxtpy.metrics_functions import cumulative_returns
from engine.single_interval_allocator import SingleIntervalAllocator


class Rebalancer(object):
    # Parameters:
    # startdate
    # enddate
    # selector_lookback
    # allocator_lookback
    # rebalance_frequency
    # single_config: subset of "example_rebalancer_config.yaml"

    def __init__(self, startdate, enddate, rebalance_frequency, selector_lookback, allocator_lookback,
                    **single_config):
        self.output = []
        date_packet_list = self.construct_rebalance_date_list(startdate, enddate, rebalance_frequency, 
                                                                selector_lookback, allocator_lookback)
        for date_packet in date_packet_list: # allocate sequentially
            current_single_config = {**single_config, **date_packet}
            track_df, excluded, forward_df = SingleIntervalAllocator(**current_single_config).get_output()
            self.save_output(track_df, excluded, date_packet, forward_df)

        self.post_processing()
        
    def construct_rebalance_date_list(self, startdate, enddate, 
                                        rebalance_frequency, selector_lookback, allocator_lookback, **kwargs):
        latest = startdate
        date_packet_list = []
        while latest < enddate:
            f1 = latest
            f2 = latest + datetime.timedelta(days = rebalance_frequency - 1)
            s1 = latest - datetime.timedelta(days = selector_lookback + 1)
            s2 = latest - datetime.timedelta(days = 1)
            a1 = latest - datetime.timedelta(days = allocator_lookback + 1)
            a2 = latest - datetime.timedelta(days = 1)
            date_packet = {"a1": a1, "a2": a2, "s1": s1, "s2": s2, "f1": f1, "f2": f2}
            date_packet_list.append(date_packet)
            latest += datetime.timedelta(days = rebalance_frequency)
        return date_packet_list

    def save_output(self, track_df, excluded, date_packet, forward_df):
        output_packet = {"track_df": track_df, "excluded": excluded, "date_packet": date_packet, "forward_df": forward_df}
        self.output.append(output_packet)

    def post_processing(self):
        self.construct_entire_series() 
        self.compile_weights()

    def construct_entire_series(self):
        df = pd.concat([j["forward_df"] for j in self.output])
        df["pcret"] = cumulative_returns(df["pret"])
        
        rs = RSeries()
        rdf = df[["pret"]]
        rs.load_custom_series(rdf, custom_series_name = "custom_allocate_series", series_type = "CustomAllo")
        
        self.fdf = df
        self.rs = rs

    def compile_weights(self, override_weight = "weight"):
        tdf_list = []
        for output_packet in self.output:
            f1 = output_packet["date_packet"]["f1"]
            f2 = output_packet["date_packet"]["f2"]
            track_df = output_packet["track_df"]
            tdf = track_df[["Name", override_weight]].set_index("Name").T.copy()
            tdf["f1"] = f1
            tdf["f2"] = f2
            tdf = tdf.reset_index(drop = True).set_index(["f1", "f2"])
            tdf_list.append(tdf)
        self.weights_df =  pd.concat(tdf_list)
    
    def get_output(self):
        return self.output, self.fdf

    def get_weights(self):
        return self.weights_df

    def get_metrics(self):
        return self.rs.get_metrics()