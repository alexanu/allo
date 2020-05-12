import json
import datetime
import pymongo
import pandas as pd
from bson import ObjectId

from data.series import RSeries
from data.init_mongo import InitMongo

class MongoStorage():
    def __init__(self, client = None):
        self.client = mongo_client = InitMongo(client = client)
     
    # Find series based on find_filter (return metadata_list_dict or id_list)
    def Find(self, find_filter = {}, id_only = False, db_name = "AnalysisEvo", coll_name = "Strategy"):
        # delete_filter = {"User": {"$nin": ["Deleted"]}}

        db = self.client[db_name]
        coll = db[coll_name]
        
        if id_only:
            id_list = x = [r['_id'] for r in coll.find(find_filter, {"data":0, "info":0})]
            return id_list
        else:    
            metadata_list_dict = x = [r for r in coll.find(find_filter, {"data":0, "info":0})]
            return metadata_list_dict

    # Load series given id_list
    def Load(self, id_list, db_name = "AnalysisEvo", coll_name = "Strategy"):
        if not isinstance(id_list, list):
            id_list = [id_list]

        db = self.client[db_name]
        coll = db[coll_name]

        id_list = [ObjectId(j) for j in id_list]
        doc_list = [r for r in coll.find({"_id": {"$in":id_list}})]
        rs_list = []
        for doc in doc_list:
            rs = RSeries()
            rs.load_from_mongo(doc = doc)
            rs_list.append(rs)
        return rs_list

    # Save list of series
    def Save(self, series_list, db_name = "AnalysisEvo", coll_name = "Strategy"):
        if not isinstance(series_list, list):
            series_list = [series_list]

        db = self.client[db_name]
        collection = db[coll_name]

        doc_list = [dict(info = SSeries.info, data = SSeries.df.reset_index().to_dict(orient = "rows")) for SSeries in series_list]
        collection.insert_many(doc_list)

    # Delete list of series
    def Delete(self, to_remove_id_list, db_name = "AnalysisEvo", coll_name = "Strategy"):
        db = self.client[db_name]
        coll = db[coll_name]

        try:
            to_remove_id_list = [ObjectId(j) for j in to_remove_id_list]
            myquery = { "_id": {"$in":  to_remove_id_list}}
            newvalues = { "$set": { "User": "Deleted" } }
            x = coll.update_many(myquery, newvalues)
            status = "Successfully removed {} strategies.".format(x.matched_count)
        except Exception as err:
            status = "Error removing {}: {}".format(to_remove_id_list, err)

        return status
