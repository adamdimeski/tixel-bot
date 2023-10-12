from pymongo.mongo_client import MongoClient
import json
import os

with open(str(os.path.dirname(__file__)) + '/details.json') as file:
    details = json.load(file)

uri = details['mongodb_uri']
client = MongoClient(uri)


def mongo():
    try:
        db = client["tixelscrapy"]
        collection = db["tickets"]
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
    return db
