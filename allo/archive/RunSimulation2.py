import time
import socket
import datetime
import numpy as np
import pandas as pd
import json
from dateutil.parser import parse
import warnings
warnings.filterwarnings("ignore")

from data.mongo_storage import MongoStorage
from rebalance.single_simulation import PortfolioSimulation
from rebalance.full_simulation import FullPortfolioSimulation, StatisticalTest
from simulation.run_multiprocessing import run_simulation
from google.google_sheet import get_settings, get_gworksheet, worksheet_to_pandas

import task.google_task as gt

#https://docs.google.com/spreadsheets/d/1LmH12tAwb2zjd5aeUqeBK6h1nbOG-9XJF8nHIcwB8gc/edit#gid=0
if __name__ == "__main__":
    gsheet = "PortfolioSimulation"
    wsheet = "TaskV2_RPS"
    print("Starting Simulation Service...")
    while True:
        status = gt.do_task(gsheet = gsheet, wsheet = wsheet, TEST = False)
        if status == -99:
            print("Break: 2.5 hours...")
            time.sleep(3600*2.5)
        else:
            print("Break for next task: 10 seconds...")
            time.sleep(10)
            
