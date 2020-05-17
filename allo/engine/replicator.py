import time
import datetime
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from engine.single_interval_allocator import SingleIntervalAllocator
from engine.rebalancer import Rebalancer
from data_parser import load_parse

class Replicator(Rebalancer):
    # Parameters:
    # startdate
    # enddate
    # index: e.g. "trpei"
    # single_config: subset of "example_replicator_config.yaml"

    def __init__(self, startdate, enddate, index,
                    **single_config):
        self.output = []
        target_ret_dict = load_parse.get(index)()
        date_packet_list = self.construct_rebalance_date_list(startdate, enddate)
        for date_packet in date_packet_list: # allocate sequentially
            current_single_config = {**single_config, **date_packet}
            current_single_config["allocator_kwargs"]["target_ret"] = target_ret_dict.get(date_packet.get("a2"))
            track_df, excluded, forward_df = SingleIntervalAllocator(**current_single_config).get_output()
            self.save_output(track_df, excluded, date_packet, forward_df)
        self.fdf = self.construct_entire_series()    
        self.post_processing()
        
    def construct_rebalance_date_list(self, startdate, enddate, **kwargs):
        # assume allocate_lookback_num_month = 1 for now
        diff = enddate - startdate 
        num_months = int(diff.days/30) + 10
        startdate_list = [startdate.replace(day = 1) + relativedelta(months=j) for j in range(num_months)]
        filtered_startdate_list = [j for j in startdate_list if j >= startdate and j < (enddate - relativedelta(months=1)).replace(day = 1)]
        date_packet_list = []
        for a1 in filtered_startdate_list:
            a2 = a1 + relativedelta(months=1) - datetime.timedelta(days = 1)
            f1 = a1 + relativedelta(months=1) 
            f2 = a1 + relativedelta(months=2) - datetime.timedelta(days = 1)
            date_packet = {"a1": a1, "a2": a2, "s1": a1, "s2": a2, "f1": f1, "f2": f2}
            date_packet_list.append(date_packet)
        return date_packet_list

  