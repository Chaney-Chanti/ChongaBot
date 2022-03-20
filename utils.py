
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
    return db.Nations.count_documents({'_id': userID}) > 0 or badWordFilter(name)

def checkBattleRatingRange(attackerID, defenderID):
    playerOneRank = json.dumps(list(db.Nations.find({'userID': attackerID}, {'_id': 0})))
    playerTwoRank = json.dumps(list(db.Nations.find({'userID': defenderID}, {'_id': 0})))
    return abs(playerOneRank - playerTwoRank) > 100 

def getUserStats(userID):
    return list(db.Nations.aggregate([
        {'$match': {'_id': userID}},
        {
            '$lookup': {
                'from': 'Resources',
                'localField': '_id',
                'foreignField': 'userID',
                'as': 'resources',
            }
        },
        {
            '$unwind': "$resources"
        },
    ]))[0]

def getRankings(): #Must change to be only top 50
    # return list(db.Nations.find())
    return list(db.Nations.find().sort('battleRating', -1))

def attackSequence(attackerID, defenderID):
    #Request Database for army data
    attackerArmy = list(db.Army.find({'userID': attackerID}, {'_id': 0}))[0]
    defenderArmy = list(db.Army.find({'userID': defenderID}, {'_id': 0}))[0]
    # for attackerUnits in attackerArmy:
        # if attackerUnits != 'userID':

    # for unit in defenderArmy:
        
    # print(attackerArmy['archer'])
    # print(defenderArmy)

def playerExists(userID):
    return db.Nations.count_documents({'userID': userID}) > 0



