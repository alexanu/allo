import time
import datetime
import numpy as np
import pandas as pd

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
            track_df, excluded = SingleIntervalAllocator(**current_single_config).get_output()
            self.save_output(track_df, excluded)
            
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

    def save_output(self, track_df, excluded):
        output_packet = {"track_df": track_df, "excluded": excluded}
        self.output.append(output_packet)

    def get_output(self):
        return self.output