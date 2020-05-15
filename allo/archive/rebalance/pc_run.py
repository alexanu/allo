import datetime
import numpy as np
import pandas as pd


from MongoStorage import MongoStorage
from PortfolioConstruction import *

import json
from dateutil.parser import parse

def load_json_kwargs(filename, j = 1):
    with open(filename, "r") as file:
        kw = json.load(file)
        kw = parse_json_date(kw)
        kw["setup"] = "{}_{}".format(kw["setup_name"], str(j).zfill(3))
        kw["seed"] = j
    return kw
    
def parse_json_date(kwargs):
    kwargs["startdate"] = parse(kwargs["startdate"])
    kwargs["lastdate"] = parse(kwargs["lastdate"])
    return kwargs

def RunAllocate(kwargs):
    try:
        MS = MongoStorage(client = "local")
        filter_seriestype = kwargs.get("filter_seriestype")
        id_list = [j.get("_id") for j in MS.FilterAndGetMetadata({"User": {"$nin": ["Deleted"]}, "SeriesType": {"$in": filter_seriestype}})]
        PC = PortfolioConstruction()
        status = [PC.AddSeries(j) for j in MS.LoadAllSeriesFromId(id_list)]
        Result = PC.SelectAndAllocateOverTime(**kwargs)
        m = Result["Metrics"]
        m["setup"] = kwargs["setup"]
        m["setup_name"] = kwargs["setup_name"]
        print("done:", m["setup"])
        return m
    except Exception as err:
        print("e:", err)
        return None