import os
import json
import datetime
import time
import re
import json
import numpy as np
import pandas as pd
from dateutil.parser import parse
from cxtpy.metrics_functions import pct_str
from cxtpy.clean import df_list_merge

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from custom_crypt.crypt import Crypt


def get_code(text):
    r = re.search("_([0-9]{4})_", text)
    if r is None:
        return None
    else:
        return str(int(r.group(1))) #.zfill(4)
    
def get_settings():
    try:
        with open("settings.txt") as file:
            json_settings = json.load(file)
    except:
        json_settings = {"mongo_client": "local", "credential_path_select": "ubuntu-ws"}
        print("Using default json_settings.")
        
    print(json_settings)
    credential_path_select = json_settings["credential_path_select"]
        
    if credential_path_select == "ubuntu-ws":
        credentials_path = '/media/workstation/Storage/GoogleProject/DeepLearningAlphaC.txt'
    elif credential_path_select == "window-vm":
        credentials_path = 'C:/Users/Workstation/Desktop/DeepLearningAlphaC.txt'
    elif credential_path_select == "window-jy":
        credentials_path = 'C:/Users/jy/Desktop/DeepLearningAlphaC.txt'
    elif credential_path_select == "popos":
        credentials_path = '/home/workstation/DeepLearningAlphaC.txt'
    
    json_settings["credentials_path"] = credentials_path
    
    return json_settings
    
def authorize():
    scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
    c = Crypt()
    dec_secret = c.Read_Decrypt("google_secret.public")
    google_secret_dict = json.loads(dec_secret)
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(google_secret_dict, scope)
    gc = gspread.authorize(credentials)
    return gc

# def authorize_old(credentials_path):
#     scope = ['https://spreadsheets.google.com/feeds',
#          'https://www.googleapis.com/auth/drive']
#     credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
#     gc = gspread.authorize(credentials)
#     return gc

def get_gworksheet(gsheet = "TASK", wsheet = "Accepted", credentials_path = None, sleep = 0):
    if credentials_path is None:
        credentials_path = '/media/workstation/Storage/GoogleProject/DeepLearningAlphaC.txt'
    try:
        #Get Strategy Meta from Google Sheet instead of json
        time.sleep(sleep)
        # gc = authorize(credentials_path)
        gc = authorize()
        spreadsheet = gc.open(gsheet)
        return spreadsheet.worksheet(wsheet)
    except Exception as err:
        print("Error at:", "get_gworksheet")
        print(err)
        raise err


def worksheet_to_pandas(wsheet):
        Accepted = wsheet.get_all_records()
        adf = pd.DataFrame(Accepted)
        adf = adf.astype("str")
        return adf
    
def get_gsheet(gsheet = "TASK", wsheet = "Accepted", credentials_path = None):
    if credentials_path is None:
        credentials_path = '/media/workstation/Storage/GoogleProject/DeepLearningAlphaC.txt'
        
    try:
        #Get Strategy Meta from Google Sheet instead of json
        gc = authorize(credentials_path)
        spreadsheet = gc.open(gsheet)
        worksheet_list = spreadsheet.worksheets()
        Accepted = spreadsheet.worksheet(wsheet).get_all_records()
        adf = pd.DataFrame(Accepted)
        adf = adf.astype("str")

        #Select a strat, and get strategy_meta from TASK.Accepted sheet
        strategy_meta = adf
        return strategy_meta
    except Exception as err:
        print("Error at:", "get_all_strategy_meta")
        print(err)
        raise err

def clean_proj_sheet(gdf):
    col =  ["Added By", "Code", "Completion", "Date", "Incubation Date", "Live Trading Date", "Instruments", "Last Update"]
    gdf = gdf[col].set_index("Code")
    gdf["Date"] = pd.to_datetime(gdf["Date"])
    gdf["Incubation Date"] = pd.to_datetime(gdf["Incubation Date"])
    gdf["Live Trading Date"] = pd.to_datetime(gdf["Live Trading Date"])
    gdf["Last Update"] = pd.to_datetime(gdf["Last Update"])
    return gdf


class StrategyMeta():
    def __init__(self, gsheet = "CXTPM_2", wsheet = "Master"):
        try:
            self.strat_meta_df = pd.read_pickle("strat_meta.pkl")
        except:
            json_settings = get_settings()
            sheet = get_gworksheet(gsheet= gsheet, wsheet= wsheet, credentials_path = json_settings["credentials_path"])
            gdf = worksheet_to_pandas(sheet)
            self.strat_meta_df = clean_proj_sheet(gdf)
            self.SaveMeta()
    
    def SaveMeta(self):
        self.strat_meta_df.to_pickle("strat_meta.pkl")
        return 
        
    def get_date_from_name(self, strat_name, default_date = datetime.datetime(2017, 7, 25)):
        try:
            code = get_code(strat_name)
            if code is None:
                return default_date
            else:
                q = self.strat_meta_df.loc[code]["Date"]
                return q
        except:
            return default_date
    