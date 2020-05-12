from excluder import custom_exclude

class Excluder(object):
    """Excluder class. 
    
    # Properties
    track_df: current simulation data (stored in df)
    date_kwargs
    excluder_kwargs

    # Methods
    NA
    """
    def __init__(self, track_df, date_kwargs, excluder_kwargs):
        excluded_df_list = []
        if len(excluder_kwargs) > 0:
            for kw in excluder_kwargs:
                name, kwargs = kw.get("name"), kw.get("kwargs")
                kwargs = {**kwargs, **date_kwargs}
                exclude_fun = custom_exclude.get(name)
                track_df, excluded_df = exclude_fun(track_df, **kwargs)
                excluded_df_list.append(excluded_df.copy())

        self.track_df, self.excluded_df_list = track_df, excluded_df_list
    
    def get_output(self):
        return self.track_df, self.excluded_df_list