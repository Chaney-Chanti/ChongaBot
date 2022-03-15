
"""
ALL FUNCTIONS NOT RELATED TO DISCORD WILL BE IN HERE
    * Queries to database should be functions
"""

import json
import pymongo
import os
from purgo_malum import client
from dotenv import load_dotenv

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot

def badWordFilter(text):
    return client.contains_profanity(text, add='you')

def checkCreation(userID, name):
    return db.Nations.count_documents({"userID": userID}) > 0 or badWordFilter(name)

def getUserStats(userID):
    return json.dumps(list(db.Nations.find({"userID": userID}, {"_id": 0})))

def getRankings():
    # return list(db.Nations.find())
    return list(db.Nations.find().sort("population", -1))

def attackSequence():
    pass

def playerHasShield():
    pass



