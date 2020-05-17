import datetime
import numpy as np
import pandas as pd 

from helper.time import timeit
from allocator import custom_allocate
from allocator.final_adjustment import sequential_distribute_min_weight, adjust_forced_min_weight

class Allocator(object):
    """Allocator class. 
    
    # Properties
    track_df: current simulation data (stored in df)
    allocate_method
    a1: start date 
    a2: end date
    adj_lowerbound: final lowerbound (based on cash value/portfolio value)
    strat_min_alloc: dictionary in the form of {strategy_name: min_weight}

    # Methods
    NA
    """
    # @timeit
    def __init__(self, track_df, allocate_method, a1, a2, adj_lowerbound = 0, strat_min_alloc = {}, multiplicative_rescale = -1, **kwargs):
        rseries_list = track_df["rs"].values
        strategy_list = track_df["Name"].values

        # Allocate
        allocate_fun = custom_allocate.get(allocate_method)
        w = weights_dict_0 = allocate_fun(rseries_list, strategy_list, a1, a2, **kwargs)

        # Sequential adjustment based on new `adj_lowerbound`        
        old_weights_list = [j for j in w.values()]
        weights_list = sequential_distribute_min_weight(old_weights_list.copy(), adj_lowerbound)
        
        weights_dict = dict()
        for key, val in zip(w.keys(), weights_list):
            weights_dict[key] = val

        output_df = track_df.copy()
        output_df["weight_0"] = output_df["Name"] 
        output_df["weight"] = output_df["Name"]
        output_df["weight_0"] = output_df["weight"].replace(weights_dict_0)
        output_df["weight"] = output_df["weight"].replace(weights_dict)

        # Adjustment for forced min weights
        self.output_df = adjust_forced_min_weight(output_df, strat_min_alloc) 
        
        if multiplicative_rescale != -1:
            self.output_df["weight_2"] = output_df["weight"].copy()
            self.output_df["weight"] = self.output_df["weight"]*(multiplicative_rescale/self.output_df["weight"].sum())
        
    def get_output(self):
        return self.output_df
