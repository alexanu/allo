from selector import custom_select


class Selector(object):
    """Selector class. 
    
    # Properties
    track_df: current simulation data (stored in df)
    select_method
    s1: start date 
    s2: end date

    # Methods
    NA
    """
    @timeit
    def __init__(self, track_df, select_method, s1, s2, **kwargs):
        rseries_list = track_df["rs"].values
        strategy_list = track_df["Name"].values
        select_fun = custom_select.get(select_method)
        selected_strategy_list = select_fun(rseries_list, strategy_list, s1, s2, **kwargs)
    
        mdf = track_df
        to_remove_strat = mdf.loc[~mdf["Name"].isin(selected_strategy_list), "Name"].values
        exclude_select_meta_df = mdf.loc[~mdf["Name"].isin(selected_strategy_list), :].copy()        
        output_df = mdf.loc[mdf["Name"].isin(selected_strategy_list)]
        
        # self.log("Selected {} strategies by {}: {}".format(len(selected_strategy_list), select_method, str(selected_strategy_list)), "Select_1")
        # self.log("Removed {} strategies by {}: {}".format(len(to_remove_strat), select_method, str(to_remove_strat)), "Select_2")

        return output_df, exclude_select_meta_df