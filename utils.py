
"""
ALL FUCTIOONS NOT RELATED TO DISCORD WILL BE IN HERE
    * Queries to database should be functions
"""
import json
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot


def checkDuplicateCreation(user, name):
    """
    Checks the MongoDB Database for duplicate creations
    Returns True or False
    
    """
    print('hello', user, name)

def getAuthorResources(author):
    return json.dumps(list(db.Nations.find({"author": author}, {"_id": 0})))

def getNationList(guild):
    return json.dumps(list(db.Nations.find({"guild": guild}, {"_id": 0})))


     

    
    
