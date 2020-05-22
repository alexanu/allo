import requests
import pandas as pd
from data.series import RSeries
from data.mongo_storage import MongoStorage


def query_data(asset = "SPY"):
    url = "https://query1.finance.yahoo.com/v7/finance/download/{}?period1=0&period2=3075094400&interval=1d&events=history".format(asset)
    site = requests.get(url)
    data = site.text
    data2 = [x.split(',') for x in data.split('\n')]
    col, rows = data2[0], data2[1:]
    df = pd.DataFrame(rows, columns = col)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace = True)
    df = df.astype(float)
    return df


def download_yahoo(asset_list):
    MS = MongoStorage()
    z = MS.Find({"Name": {"$in": asset_list}, "SeriesType": {"$in":["yahoo"]}})
    exist_asset = [j["Name"] for j in z]
    to_download_asset_list = [j for j in asset_list if j not in exist_asset]
    to_download_asset_list

    for asset in to_download_asset_list:
        try:
            df = query_data(asset)
            df[asset] = df["Adj Close"].pct_change()
            df = df.dropna()
            rdf = df[[asset]]
            if rdf.shape[0] > 100:
                rs = RSeries()
                rs.load_custom_series(rdf, custom_series_name = asset, series_type = "yahoo")
                rs.SaveSeries()
            else:
                print("Not enough data:", asset)
        except Exception as err:
            print(err)
            print("Error:", asset)
        
            