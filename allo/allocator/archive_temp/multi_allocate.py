import os 
import query
import pandas as pd
import datetime
import numpy as np
import pandas as pd
import functools

from RSeries import *
from RSeriesMulti import *
from MongoStorage import *

import warnings
warnings.filterwarnings("ignore")
from cxtpy.metrics_functions import *

from PortfolioConstruction import PortfolioConstruction
# Iterative - every 45 days process - Select, then Allocate
# Selection - inclusion and exclusion (seasonalities exclusion)
## - Exclude bad performance on individual level
## - Exclude "similar" strategies - timeframe, trade style
## - Exclude strategies that do not add value on portfolio level

# Allocation - Weight Optimization
from optimize import * 
from pc_optimize import * 
from pc_helper import *

# optimize_method = "L-BFGS-B", "BFGS", "TNC"
from functools import partial
import multiprocessing as mp
import json
from dateutil.parser import parse

import time
import joblib

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



if __name__ == "__main__":
    print("starting...")
    argss = []
    N = 100
    PROC = 6
    for k in range(5):
        for j in range(N):
            with open("setup_arg_json_{}.txt".format(k), "r") as file:
                kw = json.load(file)
                kw = parse_json_date(kw)
                kw["setup"] = "{}_{}".format(kw["setup_name"], str(j).zfill(3))
                argss.append(kw)
    
    t0 = time.time()
    pool = mp.Pool(processes = PROC)
    z = pool.map(RunAllocate, argss)
    t1 = time.time()
    
    joblib.dump(z, "y.pkl")
    print(t1-t0, (t1-t0)/500)