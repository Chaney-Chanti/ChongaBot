
"""
ALL FUCTIOONS NOT RELATED TO DISCORD WILL BE IN HERE
"""
import json
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot


def checkCreation(user, name):
    """
    Checks the MongoDB Database for duplicate creations
    Returns True or False
    
    """
    print('hello', user, name)
    
    
