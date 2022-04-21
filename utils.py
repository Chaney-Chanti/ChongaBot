
from functools import WRAPPER_ASSIGNMENTS
import json
import pymongo
import os
import random
import time
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

def canAttack(defenderID, currTime):
    return list(db.Nations.find({'_id': defenderID}, {'_id': 0}))[0]['shield']['epoch'] + 86400 < currTime
    
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

def getUnitsData():
    pass

def getBuildingsData():
    pass

def getAgeData():
    pass

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

def updateNation(userID, data):
    db.Nations.update_one({'_id': userID}, {'$set': data}) # switches false to true and level -> 1

"""GAME SERVICE FUNCTIONS """
def attackSequence(attackerID, defenderID): #problem  with different unit types fighting each other
    attackerArmy = list(db.Army.find({'userID': attackerID}, {'_id': 0}))[0]
    defenderArmy = list(db.Army.find({'userID': defenderID}, {'_id': 0}))[0]
    attackerArmyKeyList = list(attackerArmy.keys())
    defenderArmyKeyList = list(defenderArmy.keys())
    unitDiceRolls = {
        'lancer': { 'lowerBound': 1, 'upperBound': 5},
        'archer': { 'lowerBound': 1, 'upperBound': 15},
        'calvalry': { 'lowerBound': 1, 'upperBound': 30},
        'trebuchet': {'lowerBound': 1, 'upperBound': 50},
        'minutemen': { 'lowerBound': 1, 'upperBound': 50},
        'general': { 'lowerBound': 1, 'upperBound': 5},
        'cannon': { 'lowerBound': 1, 'upperBound': 5 },
        'infantry': { 'lowerBound': 1, 'upperBound': 5 },
        'tank': { 'lowerBound': 1, 'upperBound': 5 },
        'fighter': { 'lowerBound': 1, 'upperBound': 5 },
        'bomber': { 'lowerBound': 1, 'upperBound': 5 },
        'icbm': { 'lowerBound': 1, 'upperBound': 5 },
        'shocktrooper': { 'lowerBound': 1, 'upperBound': 5 },
        'lasercannon': { 'lowerBound': 1, 'upperBound': 5 },
        'starfighter': { 'lowerBound': 1, 'upperBound': 5 },
        'battlecruiser': { 'lowerBound': 1, 'upperBound': 90000 }, 
        'deathstar': { 'lowerBound': 1, 'upperBound': 100000 },
    }
    attackerCasualties = {}
    defenderCasualties = {}
    random.seed(a=None)
    i = j = 3
    while i < len(attackerArmyKeyList) and j < len(defenderArmyKeyList):      
        attackerUnitCount = attackerArmy[attackerArmyKeyList[i]] #reults to a string index
        defenderUnitCount = defenderArmy[defenderArmyKeyList[j]] #reults to a string index
        if attackerUnitCount == 0:
            i += 1
            winner = [defenderID, defenderCasualties, defenderArmy]
            loser = [attackerID, attackerCasualties, attackerArmy]
        elif defenderUnitCount == 0:
            j += 1
            winner = [attackerID, attackerCasualties, attackerArmy]
            loser = [defenderID, defenderCasualties, defenderArmy]
        else:
            attackerRoll = random.randint(unitDiceRolls[attackerArmyKeyList[i]]['lowerBound'], unitDiceRolls[attackerArmyKeyList[i]]['upperBound'])
            defenderRoll = random.randint(unitDiceRolls[defenderArmyKeyList[j]]['lowerBound'], unitDiceRolls[defenderArmyKeyList[j]]['upperBound'])
            if attackerRoll > defenderRoll:
                if defenderArmyKeyList[j] in defenderCasualties:
                    defenderCasualties[defenderArmyKeyList[j]] += 1 # I want to avoid setting the values to 0 in the dict and just write to it
                else: 
                    defenderCasualties[defenderArmyKeyList[j]] = 1
                defenderArmy[defenderArmyKeyList[j]] -= 1
                winner = [attackerID, attackerCasualties, attackerArmy]
                loser = [defenderID, defenderCasualties, defenderArmy]
            elif attackerRoll < defenderRoll:
                if attackerArmyKeyList[i] in attackerCasualties:
                    attackerCasualties[attackerArmyKeyList[i]] += 1 # I want to avoid setting the values to 0 in the dict and just write to it
                else: 
                    attackerCasualties[attackerArmyKeyList[i]] = 1
                attackerArmy[attackerArmyKeyList[i]] -= 1
                winner = [defenderID, defenderCasualties, defenderArmy]
                loser = [attackerID, attackerCasualties, attackerArmy]

    #Update users' battle rating
    loserData = list(db.Nations.find({'_id': loser[0]}, {'_id': 0}))[0]
    winnerData = list(db.Nations.find({'_id': winner[0]}, {'_id': 0}))[0]
    db.Nations.update_one({'_id': winner[0]}, {'$set': {'battleRating': winnerData['battleRating'] + 25}})
    if loserData['battleRating'] - 25 >= 0:
        db.Nations.update_one({'_id': loser[0]}, {'$set': {'battleRating': loserData['battleRating'] - 25}})
        loserRating = loserData['battleRating'] - 25
    if loserData['battleRating'] - 25 < 0:
        db.Nations.update_one({'_id': loser[0]}, {'$set': {'battleRating': 0}})
        loserRating = 0
    #Update users Army from casualties
    attackerArmy.pop('userID', None)
    db.Army.update_one({'userID': winner[0]}, {'$set': winner[2]})
    db.Army.update_one({'userID': loser[0]}, {'$set': loser[2]})
    db.Nation.update_one({'userID': loser[0]}, {'$set': {'shield': {'epoch': time.time()}}})    
    #Add tribute (steal 20% of resources)
    loserResources = list(db.Resources.find({'userID': loser[0]}, {'_id': 0}))[0]
    winnerResources = list(db.Resources.find({'userID': winner[0]}, {'_id': 0}))[0]
    resList = ['food', 'timber', 'metal', 'wealth', 'oil', 'knowledge']
    for resource in loserResources:
        if resource in resList:
            amount = loserResources[resource] * 0.2
            winnerResources[resource] = loserResources[resource] + amount
            loserResources[resource] = loserResources[resource] - amount
    db.Resources.update_one({'userID': winner[0]}, {'$set': winnerResources})
    db.Resources.update_one({'userID': loser[0]}, {'$set': loserResources})

    battleSummary = {
        'winner': winnerData['name'].upper(),
        'loser': loserData['name'].upper(),
        'winnerBattleRating': str(winnerData['battleRating'] + 25),
        'loserBattleRating': str(loserRating),
        'attackerCasualties': str(attackerCasualties),
        'defenderCasualties': str(defenderCasualties),
    }
    return battleSummary

def validateExecuteBuy(userID, unit, numUnits):
    data = list(db.Resources.find({'userID': userID}, {'_id': 0}))[0]
    unitCosts = { 
        'lancer': { 'food': 50, 'timber': 50, },
        'archer': { 'food': 100, 'timber': 100, },
        'calvalry': { 'food': 200, 'timber': 200, },
        'trebuchet': { 'food': 300, 'timber': 300, },
        'minutemen': { 'food': 100, 'metal': 100, },
        'general': { 'food': 200, 'metal': 200, 'wealth': 100},
        'cannon': { 'food': 200, 'timber': 100, 'metal': 200, 'wealth': 100},
        'infantry': { 'food': 300, 'metal': 300, 'wealth': 300},
        'tank': { 'metal': 1000, 'oil': 1000, 'wealth': 1000},
        'fighter': { 'metal': 2000, 'oil': 2000, 'wealth': 2000},
        'icbm': { 'metal': 10000, 'oil': 10000, 'wealth': 10000},
        'shocktrooper': { 'metal': 2000, 'oil': 500, 'metal': 2000},
        'lasercannon': { 'metal': 15000, 'oil': 15000, 'wealth': 15000},
        'starfighter': { 'metal': 25000, 'oil': 20000, 'wealth': 20000},
        'battlecruiser': { 'metal': 30000, 'oil': 30000, 'wealth': 30000},
        'deathstar': { 'metal': 100000, 'oil': 100000, 'wealth': 100000},
    }
    #Calculates the the total cost for the unit you are buying
    for resource in unitCosts[unit]:
        unitCosts[unit][resource] *= int(numUnits)
    totalCost = unitCosts[unit]
    newResourceBalance = {}
    print(totalCost)
    #Checks to see if you have enough resources
    for resource in totalCost:
        newResourceBalance[resource] = data[resource] - totalCost[resource]
        if data[resource] - totalCost[resource] < 0:
            print(data[resource] - totalCost[resource])
            return [False]
    return [True, newResourceBalance]

def buyBuilding(userID, building):
    age = getAge(userID)
    if age == 'Medieval':
        rateIncrease = 100
    elif age == 'Enlightment':
        rateIncrease = 200    
    if age == 'Modern':
        rateIncrease = 300
    if age == 'Space':
        rateIncrease = 400
    resData = list(db.Resources.find({'userID': userID}, {'_id': 0}))[0]
    pprint.pprint(resData)
    nationData = list(db.Nations.find({'_id': userID}, {'_id': 0}))[0]
    pprint.pprint(nationData)
    buildingCosts = { 
        'granary': { 'timber': 1000, 'metal': 1000, },
        'lumbermill': { 'timber': 3000, 'metal': 3000, },
        'quarry': { 'timber': 3000, 'metal': 3000, },
        'oilrig': { 'metal': 5000, 'wealth': 5000, },
        'market': { 'food': 1000, 'timber': 1000, 'wealth': 1000,},
        'university': { 'timber': 1500, 'metal': 1500, 'wealth': 1500,},
    }
    cost = buildingCosts[building]
    
    for resource in cost:
        if resData[resource] - cost[resource] >= 0:
            resData[resource] -= cost[resource]
            updateResources(userID, resData)
            nationData[building]['numBuildings'] += 1
            nationData[building]['built'] = True
            if building == 'granary': 
                resData['foodrate'] += rateIncrease
            if building == 'lumbermill': 
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
            return True
        else:
            return False

def upgradeAge(userID):
    userData = getUserStats(userID)
    # pprint.pprint(userData)    
    if userData['age'] == 'Medieval':
        nextAge = 'Enlightment'
    elif userData['age'] == 'Enlightment':
        nextAge = 'Modern'
    elif userData['age'] == 'Modern':
        nextAge = 'Space'
    elif userData['age'] == 'Space':
        nextAge = ''
    if nextAge == '':
        return [False, nextAge]
    ageCosts = {
        'Enlightment': 50000,
        'Modern': 200000,
        'Space': 1000000,
    }
    if userData['resources']['knowledge'] - ageCosts[nextAge] > 0:
        knowledgeCost = {'knowledge': userData['resources']['knowledge'] - ageCosts[nextAge]}
        updateResources(userID, knowledgeCost)
        updateNation(userID, {'age': nextAge})        
        return [True, nextAge]
    return [False, nextAge]
