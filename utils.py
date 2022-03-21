
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
    return abs(int(playerOneRating) - int(playerTwoRating)) < 100 

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
        'cannon': { 'lowerBound': 3, 'upperBound': 5 },
        'infantry': { 'lowerBound': 3, 'upperBound': 5 },
        'tank': { 'lowerBound': 3, 'upperBound': 5 },
        'fighter': { 'lowerBound': 3, 'upperBound': 5 },
        'bomber': { 'lowerBound': 3, 'upperBound': 5 },
        'ICBM': { 'lowerBound': 3, 'upperBound': 5 },
        'laser cannon': { 'lowerBound': 3, 'upperBound': 5 },
        'starfighter': { 'lowerBound': 3, 'upperBound': 5 },
        'battlecruiser': { 'lowerBound': 3, 'upperBound': 5 },
        'death star': { 'lowerBound': 9000, 'upperBound': 10000 },
    }
    attackerCasualties = {}
    defenderCasualties = {}
    for unit in attackerArmy:
        random.seed(a=None)
        numRounds = 1
        if unit == 'userID':
            pass
        else:
            print('CURRENT UNIT:', unit)
            while True: # this needs to change
                attackerRoll = random.randint(unitDiceRolls[unit]['lowerBound'], unitDiceRolls[unit]['upperBound'])
                defenderRoll = random.randint(unitDiceRolls[unit]['lowerBound'], unitDiceRolls[unit]['upperBound'])
                # print('attackerRoll', attackerRoll)
                # print('defenderRoll', defenderRoll)
                if attackerRoll > defenderRoll:
                    defenderArmy[unit] -= 1
                    if unit in defenderCasualties:
                        defenderCasualties[unit] += 1
                    else:
                       defenderCasualties[unit] = 1
                    # print('defenderUnitsLeft:' , defenderArmy[unit])
                elif attackerRoll < defenderRoll:
                    attackerArmy[unit] -= 1
                    if unit in attackerCasualties:
                        attackerCasualties[unit] += 1
                    else:
                       attackerCasualties[unit] = 1
                    # print('attackerUnitsLeft:' , attackerArmy[unit])
                if unit not in attackerArmy or unit not in defenderArmy:
                    break #moves onto the next unit
                if attackerArmy[unit] == 0:
                    winnerData = list(db.Nations.find({'_id': defenderID}, {'_id': 0}))[0]
                    loserData = list(db.Nations.find({'_id': attackerID}, {'_id': 0}))[0]
                    if not loserData['battleRating'] - 25 < 0:
                        db.Nations.update_one({'_id': defenderID}, {'$set': {'battleRating': winnerData['battleRating'] + 25}})
                        db.Nations.update_one({'_id': attackerID}, {'$set': {'battleRating': loserData['battleRating'] - 25}})
                    break #moves onto the next unit
                if defenderArmy[unit] == 0:
                    winnerData = list(db.Nations.find({'_id': attackerID}, {'_id': 0}))[0]
                    loserData = list(db.Nations.find({'_id': defenderID}, {'_id': 0}))[0]
                    if not loserData['battleRating'] - 25 < 0:
                        db.Nations.update_one({'_id': attackerID}, {'$set': {'battleRating': winnerData['battleRating'] + 25}})
                        db.Nations.update_one({'_id': defenderID}, {'$set': {'battleRating': loserData['battleRating'] - 25}})
                    break #moves onto the next unit
                numRounds += 1
    winner = winnerData['name']
    loser = loserData['name']

    if not loserData['battleRating'] - 25 < 0:
        loserBR = loserData['battleRating'] - 25
    loserBR = loserData['battleRating']
    
    battleSummary = {
        'winner': winner.upper(),
        'loser': loser.upper(),
        'winnerBattleRating': str(winnerData['battleRating'] + 25),
        'loserBattleRating': str(loserBR),
        'numRounds': str(numRounds),
        'attackerCasualties': str(attackerCasualties),
        'defenderCasualties': str(defenderCasualties),
    }
    #Debugging
    print('=====Battle Summary=====')
    print(winner.upper() + ' DEFEATED ' + loser.upper())
    print('Number of Battles: ', numRounds)
    print('Attacker Casualties:', attackerCasualties)
    print('Defender Casualties:', defenderCasualties)
    return battleSummary







