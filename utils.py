
import json
import pymongo
import os
import random
import itertools
import pprint
from purgo_malum import client
from dotenv import load_dotenv

from objects import nation

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
    return abs(int(playerOneRating) - int(playerTwoRating)) <= 300 

def playerExists(userID):
    return db.Nations.count_documents({'_id': userID}) > 0
    
"""GET DATA FUNCTIONS"""
def getUserStats(userID):
    print('DEBUG:', userID)
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

def getUserArmy(userID):
    return list(db.Army.find({'userID': userID}, {'_id': 0}))[0]

def getRankings(): #Must change to be only top 50
    return list(db.Nations.find().sort('battleRating', -1).limit(10))

def getAge(userID):
    return list(db.Nations.find({'_id': userID}, {'_id': 0}))[0]['age']

# def getCostList(unitCosts = unitCosts):
#     return unitCosts

"""UPDATE DATA FUNCTIONS"""

def updateResources(userID, resDict):
    db.Resources.update_one({'userID': userID}, {'$set': resDict})
    return

def updateResourceRate(userID, resDict):
    db.Resources.update_one({'userID': userID}, {'$set': resDict})
    return


def updateUnits(userID, unit, numUnits):
    data = list(db.Army.find({'userID': userID}, {'_id': 0}))[0]
    # pprint.pprint(data) debug
    db.Army.update_one({'userID': userID}, {'$set': {unit: data[unit] + int(numUnits)}})
    return 

def updateBuilding(userID, building, buildingDict):
    db.Nations.update_one({'_id': userID}, {'$set': {building: buildingDict[building]}}) # switches false to true and level -> 1
    return


"""GAME SERVICE FUNCTIONS """
def attackSequence(attackerID, defenderID): #problem  with different unit types fighting each other
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
        'shocktrooper': { 'lowerBound': 3, 'upperBound': 5 },
        'lasercannon': { 'lowerBound': 3, 'upperBound': 5 },
        'starfighter': { 'lowerBound': 3, 'upperBound': 5 },
        'battlecruiser': { 'lowerBound': 3, 'upperBound': 90000 },
        'deathstar': { 'lowerBound': 3, 'upperBound': 100000 },
    }
    attackerCasualties = {}
    defenderCasualties = {}
    random.seed(a=None)
    for unit in unitDiceRolls: #cycles through the same units 
        print(unit, attackerArmy[unit], defenderArmy[unit]) 
        if attackerArmy[unit] == 0 or defenderArmy[unit] == 0: #one person can have no units left
            pass
        else:
            while attackerArmy[unit] > 0 and defenderArmy[unit] > 0:
                print('UNNNNITTTT:', unit)
                attackerRoll = random.randint(unitDiceRolls[unit]['lowerBound'], unitDiceRolls[unit]['upperBound'])
                defenderRoll = random.randint(unitDiceRolls[unit]['lowerBound'], unitDiceRolls[unit]['upperBound'])
                print(attackerRoll, defenderRoll)
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
    #implement resource taking
    #implement taking of army
    battleSummary = {
        'winner': winnerData['name'].upper(),
        'loser': loserData['name'].upper(),
        'winnerBattleRating': str(winnerData['battleRating'] + 25),
        'loserBattleRating': str(loserData['battleRating'] - 25),
        'attackerCasualties': str(attackerCasualties),
        'defenderCasualties': str(defenderCasualties),
    }
    return battleSummary

def validateExecuteBuy(userID, unit, numUnits):
    data = list(db.Resources.find({'userID': userID}, {'_id': 0}))[0]
    unitCosts = { 
        'lancer': { 'food': 50, 'timber': 50, },
        'archer': { 'food': 50, 'timber': 50, },
        'calvalry': { 'food': 50, 'timber': 50, },
        'trebuchet': { 'food': 50, 'timber': 50, },
        'minutemen': { 'food': 50, 'timber': 50, },
        'general': { 'food': 50, 'timber': 50, },
        'cannon': { 'food': 50, 'timber': 50, },
        'infantry': { 'food': 50, 'timber': 50, },
        'tank': { 'food': 50, 'timber': 50, },
        'fighter': { 'food': 50, 'timber': 50, },
        'icbm': { 'food': 50, 'timber': 50, },
        'shocktrooper': { 'food': 50, 'timber': 50, },
        'lasercannon': { 'food': 50, 'timber': 50, },
        'starfighter': { 'food': 50, 'timber': 50, },
        'battlecruiser': { 'food': 50, 'timber': 50, },
        'deathstar': { 'food': 50, 'timber': 50, },
    }
    #calculates the the total cost for the unit you are buying
    for resource in unitCosts[unit]:
        unitCosts[unit][resource] *= int(numUnits)
    totalCost = unitCosts[unit]
    newResourceBalance = {}
    print(totalCost)
    # checks to see if you have enough resources
    for resource in totalCost:
        newResourceBalance[resource] = data[resource] - totalCost[resource]
        if data[resource] - totalCost[resource] < 0:
            print(data[resource] - totalCost[resource])
            return [False]
    return [True, newResourceBalance]

def buyBuilding(userID, building):
    rateIncrease = 100
    resData = list(db.Resources.find({'userID': userID}, {'_id': 0}))[0]
    pprint.pprint(resData)
    nationData = list(db.Nations.find({'_id': userID}, {'_id': 0}))[0]
    pprint.pprint(nationData)
    # resRate = data['']
    buildingCosts = { 
        'granary': { 'food': 50, 'timber': 50, },
        'watermill': { 'food': 50, 'timber': 50, },
        'quarry': { 'food': 50, 'timber': 50, },
        'market': { 'food': 50, 'timber': 50, },
        'oilrig': { 'food': 50, 'timber': 50, },
        'university': { 'food': 50, 'timber': 50, },
    }
    cost = buildingCosts[building]
    for resource in cost:
        resData[resource] -= cost[resource]
    updateResources(userID, resData)
    nationData[building]['numBuildings'] += 1
    nationData[building]['built'] = True
    if building == 'granary': 
        resData['foodrate'] += rateIncrease
    if building == 'watermill': 
        resData['timberrate'] += rateIncrease
    if building == 'quarry': 
        resData['metalrate'] += rateIncrease
    if building == 'oilrig': 
        resData['oilrate'] += rateIncrease
    if building == 'market': 
        resData['wealthrate'] += rateIncrease
    if building == 'university': 
        resData['knowledgerate'] += rateIncrease
    updateBuilding(userID, building, nationData)
    updateResourceRate(userID, resData)