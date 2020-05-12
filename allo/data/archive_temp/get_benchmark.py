import numpy as np
import pandas as pd
from data.mongo_storage import MongoStorage

def get_benchmark(benchmark, client = None):
    MS = MongoStorage(client = client)
    rs = MS.FindSeries(cond = {"SeriesType":"Benchmark", "Name": benchmark})
    return rs.df