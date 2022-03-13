
"""
ALL FUCTIOONS NOT RELATED TO DISCORD WILL BE IN HERE
    * Queries to database should be functions
"""
import json
from pickletools import read_unicodestring1
from numpy import true_divide
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot


def checkDuplicateCreation(author, guild):
    """
    Checks the MongoDB Database for duplicate creations by looking
    for user and server
    Returns True or False
    
    """
    return db.Nations.count_documents({"author": author}) > 0


def getAuthorResources(author):
    return json.dumps(list(db.Nations.find({"author": author}, {"_id": 0})))

def getNationList(guild):
    return json.dumps(list(db.Nations.find({"guild": guild}, {"_id": 0})))

def addResources():
    """
    Adds the correct resources per hour for all users.
    This function will be called every hour
    """
    pass
def attackSequence():
    """
    Handles the attacking procedure between two players.
    subtracts populations and gives the victim player a shield.
    (Might need balancing later if players have multiple accs
    and attack themselves for shields.)
    """
    pass



