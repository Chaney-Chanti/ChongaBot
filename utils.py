
"""
ALL FUNCTIONS NOT RELATED TO DISCORD WILL BE IN HERE
    * Queries to database should be functions
"""

import json
from tkinter import E
import pymongo
import os
from purgo_malum import client
from dotenv import load_dotenv

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot

def badWordFilter(text):
    """Censor out bad words from names. Returns True if profanity found"""
    return client.contains_profanity(text, add='you')

def checkCreation(userID, name):
    """
    * Checks the MongoDB Database for duplicate creations by looking
    for user and server
    * Will also call badWordFilter to filter out bad words
    Returns True or False
    """
    return db.Nations.count_documents({"author": userID}) > 0 or badWordFilter(name)

def getAuthorResources(userID):
    return json.dumps(list(db.Resources.find({"userID": userID}, {"_id": 0})))

def getNationList(serverID):
    return json.dumps(list(db.Nations.find({"serverID": serverID}, {"_id": 0})))

def addResources():
    print('HELLO')
    return
     
def attackSequence():
    """
    Handles the attacking procedure between two players.
    subtracts populations and gives the victim player a shield.
    (Might need balancing later if players have multiple accs
    and attack themselves for shields.)
    """
    pass

def playerHasShield():
    pass


