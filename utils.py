
import json
import pymongo
import os
import random
import time
import math
import pprint
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
    print(attackerID, defenderID)
    playerOneRating = json.dumps(list(db.Nations.find({'_id': attackerID}, {'_id': 0}))[0]['battleRating'])
    playerTwoRating = json.dumps(list(db.Nations.find({'_id': defenderID}, {'_id': 0}))[0]['battleRating'])
    return abs(int(playerOneRating) - int(playerTwoRating)) <= 200 

def playerExistsViaID(userID):
    return db.Nations.count_documents({'_id': userID}) > 0

def playerExistsViaUsername(username):
    return db.Nations.count_documents({'username': username}) > 0

def hasShield(defenderID, currTime):
    idFilter = '_id'
    if '#' in str(defenderID):
        idFilter = 'username'
    return list(db.Nations.find({idFilter: defenderID}, {idFilter: 0}))[0]['shield'] + 86400 > currTime

"""GET DATA FUNCTIONS"""
def getUserIDFromUsername(username):
    return db.Nations.find({'username': username}, {'userID': 1})[0]['_id']

def getUserStats(userID):
    idFilter = '_id'
    if '#' in str(userID):
        idFilter = 'username'
    return list(db.Nations.aggregate([
        {'$match': {idFilter: userID}},
        {
            '$lookup': {
                'from': 'Resources',
                'localField': idFilter,
                'foreignField': 'userID',
                'as': 'resources',
            }
        },
        {
            '$unwind': "$resources"
        },
    ]))[0]

def getUnits():
    return ['lancer', 'archer', 'calvalry', 'trebuchet', 
    'minutement', 'general', 'cannon', 
    'infantry', 'tank', 'fighter', 'bomber', 'icbm',
    'shocktrooper', 'starfighter', 'lasercannon', 'battlecruiser', 'deathstar']

def getUserArmy(userID):
    return list(db.Army.find({'userID': userID}, {'_id': 0}))[0]

def getRankings(): #Must change to be only top 50
    return list(db.Nations.find().sort('battleRating', -1).limit(10))

def getAge(userID):
    return list(db.Nations.find({'_id': userID}, {'_id': 0}))[0]['age']

def getVictims(userID):
    userBR = list(db.Nations.find({'_id': userID}, {'_id': 0}))[0]['battleRating']
    upperRange = userBR + 200
    lowerRange = userBR - 200
    #Might need refactor for a lot of players
    playerList = list(db.Nations.find().sort('battleRating', -1).limit(10))
    attackablePlayers = []
    attackablePlayersSmall = []
    for player in playerList:
        print(int(player['shield']) < time.time())
        if player['battleRating'] in range(lowerRange, upperRange) and int(player['shield']) < time.time():
            if not player['_id'] == userID: #Exclude self player
                attackablePlayers.append(player['username'])
    if len(attackablePlayers) > 10:
        for i in range(0,10):
            rand = random.sample(range(len(attackablePlayers)), 10)
            attackablePlayersSmall.append(attackablePlayers[rand])
        return attackablePlayersSmall
    return attackablePlayers
def getUnitsCosts(): #im not sure how dynamic this is? can i just change as i please?
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
        'bomber': { 'metal': 3000, 'oil': 3000, 'wealth': 3000},
        'icbm': { 'metal': 10000, 'oil': 10000, 'wealth': 10000},
        'shocktrooper': { 'metal': 2000, 'oil': 500, 'wealth': 2000},
        'lasercannon': { 'metal': 15000, 'oil': 15000, 'wealth': 15000},
        'starfighter': { 'metal': 25000, 'oil': 20000, 'wealth': 20000},
        'battlecruiser': { 'metal': 30000, 'oil': 30000, 'wealth': 30000},
        'deathstar': { 'metal': 100000, 'oil': 100000, 'wealth': 100000},
    }
    return unitCosts

def getBuildingsCosts():
    buildingCosts = { 
        'granary': { 'timber': 1000, 'metal': 1000, },
        'lumbermill': { 'timber': 3000, 'metal': 3000, },
        'quarry': { 'timber': 3000, 'metal': 3000, },
        'oilrig': { 'metal': 5000, 'wealth': 5000, },
        'market': { 'food': 1000, 'timber': 1000, 'wealth': 1000,},
        'university': { 'timber': 1500, 'metal': 1500, 'wealth': 1500,},
    }
    return buildingCosts

def getAgeCosts():
    ageCosts = {
        'Enlightment': 50000,
        'Modern': 200000,
        'Space': 1000000,
    }
    return ageCosts

def getUnitDiceRolls():
    unitDiceRolls = {
        'lancer': { 'lowerBound': 1, 'upperBound': 5},
        'archer': { 'lowerBound': 1, 'upperBound': 15},
        'calvalry': { 'lowerBound': 1, 'upperBound': 30},
        'trebuchet': {'lowerBound': 1, 'upperBound': 50},
        'minutemen': { 'lowerBound': 1, 'upperBound': 50},
        'general': { 'lowerBound': 1, 'upperBound': 60},
        'cannon': { 'lowerBound': 1, 'upperBound': 80},
        'infantry': { 'lowerBound': 1, 'upperBound': 100},
        'tank': { 'lowerBound': 1, 'upperBound': 1000},
        'fighter': { 'lowerBound': 1, 'upperBound': 10000},
        'bomber': { 'lowerBound': 1, 'upperBound': 30000},
        'icbm': { 'lowerBound': 1, 'upperBound': 100000},
        'shocktrooper': { 'lowerBound': 1, 'upperBound': 10000},
        'lasercannon': { 'lowerBound': 1, 'upperBound': 100000},
        'starfighter': { 'lowerBound': 1, 'upperBound': 500000},
        'battlecruiser': { 'lowerBound': 1, 'upperBound': 700000}, 
        'deathstar': { 'lowerBound': 1, 'upperBound': 10000000},
    }
    return unitDiceRolls

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
    unitDiceRolls = getUnitDiceRolls()
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
    loserData = list(db.Nations.find({'userID': loser[0]}))
    if len(loserData) == 0:
        loserData = list(db.Nations.find({'_id': loser[0]}))[0]
        loserSearch = '_id'
        loserResSearch = 'userID'
    else:
        loserData = loserData[0]
        loserSearch = 'username'
        loserResSearch = 'username'
    winnerData = list(db.Nations.find({'userID': winner[0]}))
    if len(winnerData) == 0:
        winnerData = list(db.Nations.find({'_id': winner[0]}))[0]
        winnerSearch = '_id'
        winnnerResSearch = 'userID'
    else:
        winnerData = winnerData[0]
        winnerSearch = 'username'
        winnnerResSearch = 'username'
    db.Nations.update_one({winnerSearch: winner[0]}, {'$set': {'battleRating': winnerData['battleRating'] + 25}})
    if loserData['battleRating'] - 25 >= 0:
        # db.Nations.update_one({loserSearch: loser[0]}, {'$set': {'battleRating': loserData['battleRating'] - 25, 'shield': time.time() + 86400}})
        loserRating = loserData['battleRating'] - 25
    if loserData['battleRating'] - 25 < 0:
        # db.Nations.update_one({loserSearch: loser[0]}, {'$set': {'battleRating': 0, 'shield': time.time() + 86400}})
        loserRating = 0
    #Update users Army from casualties
    attackerArmy.pop('userID', None)
    print('Winner:', winner[0], '\n', winner[1], '\n', winner[2])
    print('Loser:', loser[0], '\n', loser[1], '\n',loser[2])
    db.Army.update_one({'userID': winner[0]}, {'$set': winner[2]})
    db.Army.update_one({'userID': loser[0]}, {'$set': loser[2]})
    #Add tribute (steal 20% of resources + 3x bonus loot)
    # print(loserSearch, loser[0], winnerSearch, winner[0])
    loserResources = list(db.Resources.find({loserResSearch: loser[0]}))[0]
    winnerResources = list(db.Resources.find({winnnerResSearch: winner[0]}))[0]
    resList = ['food', 'timber', 'metal', 'wealth', 'oil', 'knowledge']
    totalBonusLoot = {}
    for resource in loserResources:
        if resource in resList:
            amount = math.ceil(loserResources[resource] * 0.2)
            winnerResources[resource] = loserResources[resource] + amount
            loserResources[resource] = loserResources[resource] - amount
            bonusLoot = amount * 3
            totalBonusLoot[resource] = bonusLoot
            winnerResources[resource] += bonusLoot
    db.Resources.update_one({winnnerResSearch: winner[0]}, {'$set': winnerResources})
    db.Resources.update_one({loserResSearch: loser[0]}, {'$set': loserResources})

    battleSummary = {
        'winner': winnerData['name'].upper(),
        'loser': loserData['name'].upper(),
        'winnerBattleRating': str(winnerData['battleRating'] + 25),
        'tribute': totalBonusLoot,
        'loserBattleRating': str(loserRating),
        'attackerCasualties': str(attackerCasualties),
        'defenderCasualties': str(defenderCasualties),
    }
    return battleSummary

def validateExecuteBuy(userID, unit, numUnits):
    data = list(db.Resources.find({'userID': userID}, {'_id': 0}))[0]
    unitCosts = getUnitsCosts()
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
            # print(data[resource] - totalCost[resource])
            return [False]
    return [True, newResourceBalance]

def buyBuilding(userID, building, numBuild):
    numBuild = int(numBuild)
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
    nationData = list(db.Nations.find({'_id': userID}, {'_id': 0}))[0]

    buildingCosts = getBuildingsCosts()
    cost = buildingCosts[building]
    
    for resource in cost:
        if resData[resource] - cost[resource] * numBuild >= 0:
            resData[resource] -= cost[resource] * numBuild
            updateResources(userID, resData)
        else:
            return False
    nationData[building]['built'] = True
    nationData[building]['numBuildings'] += numBuild
    if building == 'granary': 
        resData['foodrate'] += rateIncrease * numBuild
    if building == 'lumbermill': 
        resData['timberrate'] += rateIncrease * numBuild
    if building == 'quarry': 
        resData['metalrate'] += rateIncrease * numBuild
    if building == 'oilrig': 
        resData['oilrate'] += rateIncrease * numBuild
    if building == 'market': 
        resData['wealthrate'] += rateIncrease * numBuild
    if building == 'university': 
        resData['knowledgerate'] += rateIncrease * numBuild
    updateBuilding(userID, building, nationData)
    updateResourceRate(userID, resData)
    return True

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
    ageCosts = getAgeCosts()
    if userData['resources']['knowledge'] - ageCosts[nextAge] > 0:
        knowledgeCost = {'knowledge': userData['resources']['knowledge'] - ageCosts[nextAge]}
        updateResources(userID, knowledgeCost)
        updateNation(userID, {'age': nextAge})        
        return [True, nextAge]
    return [False, nextAge]
