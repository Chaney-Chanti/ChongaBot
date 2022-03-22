
import json
import pymongo
import os
import random
import itertools
from purgo_malum import client
from dotenv import load_dotenv

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot


"""BOOLEAN CHECK FUNCTIONS"""
def badWordFilter(text):
    return client.contains_profanity(text, add='you')

def checkCreation(userID, name):
    return db.Nations.count_documents({'_id': userID}) > 0 or badWordFilter(name)

def checkBattleRatingRange(attackerID, defenderID):
    playerOneRating = json.dumps(list(db.Nations.find({'_id': attackerID}, {'_id': 0}))[0]['battleRating'])
    playerTwoRating = json.dumps(list(db.Nations.find({'_id': defenderID}, {'_id': 0}))[0]['battleRating'])
    return abs(int(playerOneRating) - int(playerTwoRating)) <= 100 

def playerExists(userID):
    return db.Nations.count_documents({'_id': userID}) > 0

"""GET DATA FUNCTIONS"""
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
    return list(db.Nations.find().sort('battleRating', -1))

"""GAME SERVICE FUNCTIONS """
def attackSequence(attackerID, defenderID):
    attackerArmy = list(db.Army.find({'userID': attackerID}, {'_id': 0}))[0]
    defenderArmy = list(db.Army.find({'userID': defenderID}, {'_id': 0}))[0]
    unitDiceRolls = {
        'lancer': { 'lowerBound': 3, 'upperBound': 5},
        'archer': { 'lowerBound': 3, 'upperBound': 10},
        'calvalry': { 'lowerBound': 3, 'upperBound': 5},
        'trebuchet': {'lowerBound': 3, 'upperBound': 5},
        'minutemen': { 'lowerBound': 3, 'upperBound': 5},
        'general': { 'lowerBound': 3, 'upperBound': 5},
        'cannon': { 'lowerBound': 3, 'upperBound': 5 },
        'infantry': { 'lowerBound': 3, 'upperBound': 5 },
        'tank': { 'lowerBound': 3, 'upperBound': 5 },
        'fighter': { 'lowerBound': 3, 'upperBound': 5 },
        'bomber': { 'lowerBound': 3, 'upperBound': 5 },
        'icbm': { 'lowerBound': 3, 'upperBound': 5 },
        'laserCannon': { 'lowerBound': 3, 'upperBound': 5 },
        # 'starFighter': { 'lowerBound': 3, 'upperBound': 5 },
        'battleCruiser': { 'lowerBound': 3, 'upperBound': 5 },
        'deathStar': { 'lowerBound': 9000, 'upperBound': 10000 },
    }
    attackerCasualties = {}
    defenderCasualties = {}
    random.seed(a=None)
    for unit in unitDiceRolls:
        print(unit, attackerArmy[unit], defenderArmy[unit])
        if attackerArmy[unit] == 0 or defenderArmy[unit] == 0:
            pass
        else:
            while attackerArmy[unit] > 0 and defenderArmy[unit] > 0:
                attackerRoll = random.randint(unitDiceRolls[unit]['lowerBound'], unitDiceRolls[unit]['upperBound'])
                defenderRoll = random.randint(unitDiceRolls[unit]['lowerBound'], unitDiceRolls[unit]['upperBound'])
                if attackerRoll > defenderRoll:
                    if unit in defenderCasualties:
                        defenderCasualties[unit] += 1 # I want to avoid setting the values to 0 in the dict and just write to it
                    else: defenderCasualties[unit] = 1
                    defenderArmy[unit] -= 1
                    winnerID = attackerID
                    loserID = defenderID
                elif attackerRoll < defenderRoll:
                    if unit in attackerCasualties:
                        attackerCasualties[unit] += 1 # I want to avoid setting the values to 0 in the dict and just write to it
                    else: 
                        attackerCasualties[unit] = 1
                    attackerArmy[unit] -= 1
                    winnerID = defenderID
                    loserID = attackerID

    loserData = list(db.Nations.find({'_id': loserID}, {'_id': 0}))[0]
    winnerData = list(db.Nations.find({'_id': winnerID}, {'_id': 0}))[0]
    db.Nations.update_one({'_id': winnerID}, {'$set': {'battleRating': winnerData['battleRating'] + 25}})
    db.Nations.update_one({'_id': loserID}, {'$set': {'battleRating': loserData['battleRating'] - 25}})
    battleSummary = {
        'winner': winnerData['name'].upper(),
        'loser': loserData['name'].upper(),
        'winnerBattleRating': str(winnerData['battleRating'] + 25),
        'loserBattleRating': str(loserData['battleRating'] - 25),
        'attackerCasualties': str(attackerCasualties),
        'defenderCasualties': str(defenderCasualties),
    }
    return battleSummary




