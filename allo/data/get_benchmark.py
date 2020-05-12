import numpy as np
import pandas as pd
from data.mongo_storage import MongoStorage


def get_benchmark(benchmark, client = None):
    MS = MongoStorage(client = client)
    id_list = MS.Find(find_filter = {"SeriesType":"Benchmark", "Name": benchmark}, id_only = True)
    rs = MS.Load(id_list)[0]
    return rs.df