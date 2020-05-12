import datetime
import pymongo
import pandas as pd
import json

def InitMongo(client = None, silent = True):
    try:
        with open("settings.txt") as file:
            settings = json.load(file)
    except:
        settings = {"mongo_uri": "mongodb://cxtanalytics:3.1415cxt@127.0.0.1:27017"}
        print("Cannot find settings.txt. Using default settings.")
        
    if client is not None:
        mongo_client = client
    else:
        mongo_client = pymongo.MongoClient(settings['mongo_uri'])
    
    if not silent:
        print("MongoStorage: Using {}".format(mongo_client.address))

    return mongo_client
