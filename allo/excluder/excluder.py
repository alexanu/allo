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
        excluded = {}
        if len(excluder_kwargs) > 0:
            for kw in excluder_kwargs:
                name, kwargs = kw.get("name"), kw.get("kwargs")
                kwargs = {**kwargs, **date_kwargs}
                exclude_fun = custom_exclude.get(name)
                track_df, excluded_df = exclude_fun(track_df, **kwargs)
                excluded[name] = excluded_df

        self.track_df, self.excluded = track_df, excluded
    
    def get_output(self):
        return self.track_df, self.excluded