
import json
import pymongo
import os
import random
import time
import math
import pprint
from dotenv import load_dotenv

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot
prefix = 'c!'

# with open('settings.json') as settings_file:
#     data = json.load(settings_file)

"""SETTINGS"""
battle_rating_range = 200
age_resource_rate_increases = {
    'stone': 100,
    'medieval': 200,
    'enlightment': 500,
    'modern': 1000,
    'space': 1500
}
steal_percentage = 0.1
bonus_loot_multiplier = 2
battle_rating_increase = 25
random.seed(a=None)
big_loot_bonus = 3
unit_capacities = {
    'explorer': 500,
    'caravan': 1000,
    'conquistador': 2000,
    'cargoship': 5000,
    'tradeship': 10000,
}

"""BOOLEAN CHECK FUNCTIONS"""
def check_nation_exists(user_id):
    return db.Nations.count_documents({'_id': user_id}) > 0

def check_createnation(userID, args):
    #if one argument is pass, len(arg) is length of the one arguement
    #if multiple arguments are passed, len(arg) is number of arguements
    num_args = args.split()
    if len(num_args) > 1:
        return(True, f'Incorrect parameters. Format: {prefix}createnation [name]')
    elif check_nation_exists(userID):
        return (True, 'Nation already exists! You may only have one nation for all servers!')
    elif len(args) > 25:
        return(True, 'Nation name is too long!')
    else:
        return (False, 'OK')
    
def check_stats(ctx, userID, arg):
    #get number of arguments
    if arg != None:
        num_args = arg.split()
        #go through checks
        if len(num_args) > 2:
            return(True, f'Incorrect parameters. Format: {prefix}stats or {prefix}stats username')
        if len(ctx.message.mentions) == 1:
            target_id = ctx.message.mentions[0].id
            if not player_exists_via_id(target_id):
                return (True, 'User does not exist idiot!')
            return (False, target_id)
        else:
            if not player_exists_via_username(arg):
                return (True, 'User does not exist idiot!')
            target_id = get_user_id_from_username(arg)
            return (False, target_id)
    return (False, userID)

def check_claim(userID):
    if not check_nation_exists(userID):
        return(True, 'User does not exist')
    return(False, 'OK')

def check_shop(userID, arg):
    #get number of arguments
    if arg != None:
        num_args = arg.split()
        if not check_nation_exists(userID):
            return (True, 'User does not exist idiot!')
        if len(num_args) > 2:
            return(True, f'Incorrect parameters. Format: {prefix}shop or {prefix}shop unit number')
        if arg not in get_all_units():
            print(arg, get_all_units)
            return(True, 'Unit does not exist')
    return (False, 'OK')

def check_build(userID, arg1, arg2):
    buildings = get_buildings()
    if arg1 != None and arg2 != None:
        num_args = arg1.split()
        if not check_nation_exists(userID):
            return (True, 'User does not exist idiot!')
        if len(num_args) > 2:
            return(True, f'Incorrect parameters. Format: {prefix}build or {prefix}build unit number')
        if arg1.lower() not in buildings:
            return(True, f'Building does not exist...')
        if not arg2.isnumeric():
            return (True, f'You have to specify a number of units to buy')
    return (False, 'OK')
        
def check_attack(ctx, user_id, arg):
    if arg != None: #only player is @ and username
        num_args = arg.split()
        #go through checks
        if len(num_args) > 1:
            return(True, f'Incorrect parameters. Format: {prefix}attack or {prefix}attack username')
        if has_shield(user_id, time.time()):
            return (True, 'This player has a shield, you can\'t attack them...')
        if not has_army(user_id):
            return (True, 'Stop the cap you have no army...')
        if len(ctx.message.mentions) == 1:
            target_id = ctx.message.mentions[0].id
            if ctx.message.author.id == user_id:
                return (True, 'You cannot attack yourself...')
            if not player_exists_via_id(target_id):
                return (True, 'User does not exist idiot!')
            if not check_in_battle_rating_range(user_id, target_id):
                # battle_rating_range = data.get('battle_rating_range')
                return (True, f'Your battle rating is either to high or to low (+-{battle_rating_range})')
            return (False, target_id)
        else:
            if not player_exists_via_username(arg):
                return (True, 'User does not exist idiot!')
            target_id = get_user_id_from_username(arg)
            if ctx.message.author.id == target_id:
                return (True, 'You cannot attack yourself...')
            if not check_in_battle_rating_range(user_id, target_id):
                return (True, f'Your battle rating is either to high or to low (+-{battle_rating_range})')
            return (False, target_id)
    return (False, user_id)

def check_explore(ctx, user_id, arg):
    user_army = get_user_army(user_id)
    user_stats = get_user_stats(user_id)
    current_time = time.time()
    time_passed_hours = (current_time - user_stats['last_explore']) / 3600
    if time_passed_hours <= 1:
        return (True, '```You have already explored. Try again in an hour...```')
    if user_army['explorer'] <= 0 and user_army['caravan'] <= 0 and user_army['conquistadand'] <= 0 and user_army['cargoship'] <= 0 and user_army['tradeship'] <= 0:
        return (True, '```You do not have any exploration units```')
    # if not arg.isnumeric():
    #     return (True, '```You must specify a number of units to send```')
    return (False, 'OK')

def check_in_battle_rating_range(attackerID, defenderID):
    player_one_rating = json.dumps(list(db.Nations.find({'_id': attackerID}, {'_id': 0}))[0]['battle_rating'])
    player_two_rating = json.dumps(list(db.Nations.find({'_id': defenderID}, {'_id': 0}))[0]['battle_rating'])
    # print('DEBUG', 'RATINGS: ', player_one_rating, player_two_rating)
    return abs(int(player_one_rating) - int(player_two_rating)) <= battle_rating_range 

def player_exists_via_id(userID):
    return db.Nations.count_documents({'_id': userID}) > 0

def player_exists_via_username(username):
    return db.Nations.count_documents({'username': username}) > 0

def has_shield(defenderID, currTime):
    return list(db.Nations.find({'_id': defenderID}, {'_id': 0}))[0]['shield'] >= currTime

def has_army(user_id):
    armyData = get_user_army(user_id)
    units = get_all_units()
    for unit in armyData:
        if unit in units and armyData[unit] > 0 :
            return True
    return False
            
"""GET DATA FUNCTIONS"""
def get_message_info(message_data):
    # print('DEBUG: ', message_data)
    return (message_data.author.id, message_data.guild.id, message_data.author.name)

def get_user_id_from_username(username):
    return db.Nations.find({'username': username}, {'_id': 1})[0]['_id']

def get_user_stats(user_id):
    return list(db.Nations.aggregate([
        {'$match': {'_id': user_id}},
        {
            '$lookup': {
                'from': 'Resources',
                'localField': '_id',
                'foreignField': '_id',
                'as': 'resources',
            }
        },
        {
            '$unwind': "$resources"
        },
    ]))[0]

def get_all_units(): #returns a list of all units
    all_unit_info = get_all_units_info()
    all_units = []
    for era_units in all_unit_info.values():
        for unit_name in era_units:
            all_units.append(unit_name)
    return all_units

def get_unit_names_by_age(age):
    all_units_info = get_all_units_info()
    
    if age in all_units_info:
        units_info_for_age = all_units_info[age]
        return list(units_info_for_age.keys())
    else:
        return []

def get_all_units_info():
    return {
        'stone': {
            'slinger': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'clubman': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'spearman': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'archer': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'keep': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'explorer': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
        },
        'medieval': {
            'knight': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'crossbowman': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'cavalry': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'trebuchet': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'war_elephant': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'castle': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'caravan': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
        },
        'enlightment': {
            'minutemen':{ 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'general': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'cannon': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'armada': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'fortress': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'conquistador': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
        },
        'modern': {
            'infantry': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'tank': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'fighter': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'bomber': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'battleship': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'aircraft_carrier': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'icbm': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'bunker': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'cargoship': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },

        },
        'space' : {
            'shocktrooper': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'lasercannon': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'starfighter': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'battlecruiser': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'deathstar': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
               'planetary_fortress': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
               'tradeship': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
        },
    }

def get_events():
    pass

def get_exploration_events():
  return {
    (0.00, 0.35): { #free resources
        'free_resources': 'free_resources',
        'stone': 1000,
        'medieval': 5000,
        'enlightenment': 10000,
        'modern': 20000,
        'space': 40000,
    },
    (0.35, 0.70): { #free units
        'free_units': 'free_units',
        'stone': get_unit_names_by_age('stone'),
        'medieval': get_unit_names_by_age('medieval'),
        'enlightenment': get_unit_names_by_age('enlightment'),
        'modern': get_unit_names_by_age('modern'),
        'space': get_unit_names_by_age('space'),
    },
    (0.70, 0.90): { #trade route
        'trade_route': 'trade_route',
        'stone': 100,
        'medieval': 200,
        'enlightenment': 500,
        'modern': 1000,
        'space': 2000,
    },
    (0.90, 0.95): { #tough_journey
        'tough_journey': 'tough_journey',
    },
    (0.95, 0.96): { #pirates
        'pirates': 'pirates',
    },
    (0.96, 0.99): { #big_loot
        'big_loot': 'big_loot',
        'stone': 1000,
        'medieval': 5000,
        'enlightenment': 10000,
        'modern': 20000,
        'space': 40000,
    },
    (0.99, 1.00): { #wonder
        'wonder': 'wonder',
        'stone': [],
        'medieval': [],
        'enlightenment': [],
        'modern': [],
        'space': [],
    },
}

def explore(user_id, user_army):
    data = get_user_stats(user_id)
    user_age = get_age(user_id)
    explorer_units = ['explorer', 'caravan', 'conquistador', 'spy', 'cargoship', 'tradeship']
    users_explorer_units = {key: user_army[key] for key in explorer_units if key in user_army}
    event_chance = round(random.uniform(0, 1), 2) #generate random float between 0 and 1 (inclusive) with decimals to 2 places
    #find which event occurred
    for (lowerbound, upperbound), event in get_exploration_events().items():
        if lowerbound <= event_chance < upperbound:
            break
    if(event).get('free_resources') is not None:
        resources_gained = event[user_age]
        updated_resources = {}  # Initialize an empty dictionary to store the updated values

        for unit in users_explorer_units:
            num_units = user_army[unit]  # results in the number of units
            # Iterate over each resource and update it in a cumulative manner
            for resource in ['food', 'timber', 'metal', 'wealth', 'oil', 'knowledge']:
                resource_key = resource  # Key in the data dictionary
                updated_resources[resource_key] = data['resources'][resource_key] + (resources_gained * unit_capacities[unit])
                # Update the data dictionary with the new value
                data['resources'][resource_key] = updated_resources[resource_key]

        update_resources(user_id, updated_resources)
        db.Nations.update_one({'_id': user_id}, {'$set': {'last_explore': time.time()}})
        return('```Your units befriended a nearby nation whom brough back gifts!\n' 
               + str(updated_resources[resource_key]) + ' (of every resource)```')
    elif(event).get('free_units') is not None:
        users_available_units = event[user_age]

        non_combat_units = ['keep', 'castle', 'fortress', 'bunker', 'planetary_fortress']
        start_index = users_available_units.index(non_combat_units[0])
        end_index = start_index + len(non_combat_units)
        # Remove the sublist using slicing
        result_list = users_available_units[:start_index] + users_available_units[end_index:]

        num_units = random.randint(3,7)
        random_unit = random.choice(result_list)
        # pprint.pprint(user_army)
        user_army[random_unit] += num_units
        db.Army.update_one({'_id': user_id}, {'$set': user_army})
        db.Nations.update_one({'_id': user_id}, {'$set': {'last_explore': time.time()}})
        return('```Your units recruited some mercenaries!' 
               + '\nRecruited: ' + str(num_units) + ' ' + str(random_unit) + 's```')
    elif(event).get('trade_route') is not None:
        resource_rate_gain = event[user_age]
        updated_resources_rates = {
            'food_rate': data['resources']['food_rate'] + resource_rate_gain,
            'timber_rate': data['resources']['timber_rate'] + resource_rate_gain,
            'metal_rate': data['resources']['metal_rate'] + resource_rate_gain,
            'wealth_rate': data['resources']['wealth_rate'] + resource_rate_gain,
            'oil_rate': data['resources']['oil_rate'] + resource_rate_gain,
            'knowledge_rate': data['resources']['knowledge_rate'] + resource_rate_gain,
        }
        
        update_resources(user_id, updated_resources_rates)
        db.Nations.update_one({'_id': user_id}, {'$set': {'last_explore': time.time()}})
        return('```Your units discovered a trade route with China!\n' 
               + 'resource rate increased by ' + str(resource_rate_gain) + '```')
    elif(event).get('tough_journey') is not None:
        for unit in explorer_units:
            user_army[unit] = math.floor(user_army[unit]/2)
        db.Army.update_one({'_id': user_id}, {'$set': user_army})
        db.Nations.update_one({'_id': user_id}, {'$set': {'last_explore': time.time()}})
        return('```You exploration units had a tough journey... you lost half your men\n' 
               + 'Casualties: ' + str(math.floor(user_army[unit]/2)) + '```')
    elif(event).get('pirates') is not None:
        for unit in explorer_units:
            user_army[unit] = 0
        db.Army.update_one({'_id': user_id}, {'$set': user_army})
        db.Nations.update_one({'_id': user_id}, {'$set': {'last_explore': time.time()}})
        return('You were attacked by pirates, all your units died')
    elif(event).get('big_loot') is not None:
        resources_gained = event[user_age]
        updated_resources = {}  # Initialize an empty dictionary to store the updated values

        for unit in users_explorer_units:
            num_units = user_army[unit]  # results in the number of units
            # Iterate over each resource and update it in a cumulative manner
            for resource in ['food', 'timber', 'metal', 'wealth', 'oil', 'knowledge']:
                resource_key = resource  # Key in the data dictionary
                updated_resources[resource_key] = data['resources'][resource_key] + ((resources_gained * big_loot_bonus) * unit_capacities[unit])
                # Update the data dictionary with the new value
                data['resources'][resource_key] = updated_resources[resource_key]
        update_resources(user_id, updated_resources)
        db.Nations.update_one({'_id': user_id}, {'$set': {'last_explore': time.time()}})
        return('```Your units conquered a small nation and brought back tribute!\n' +
               'Collected: ' + str(updated_resources[resource_key]) + ' (every resource)```')
    elif(event).get('wonder') is not None:
        print('Your units discovered a wonder!')
        # pprint.pprint(user_stats)

def get_users_available_units(age): # maybe make a for loop and loop through unit costs or dice rolls
    all_unit_info = get_all_units_info()
    unit_list = []
    for era, units in all_unit_info.items():
        if era.lower() == age.lower():
            unit_list.extend(units.keys())
    return unit_list

def get_unit_costs():
    all_unit_info = get_all_units_info()
    simplified_costs = {}
    for era, era_units in all_unit_info.items():
        for unit_name, unit_info in era_units.items():
            costs = unit_info.get('costs', {})
            simplified_costs[unit_name] = costs
    return simplified_costs

def get_unit_dice_rolls():
    all_unit_info = get_all_units_info()
    simplified_rolls = {}
    for era, era_units in all_unit_info.items():
        for unit_name, unit_info in era_units.items():
            rolls = unit_info.get('rolls', {})
            lower_bound = rolls.get('lowerbound')
            upper_bound = rolls.get('upperbound')
            simplified_rolls[unit_name] = {'lowerbound': lower_bound, 'upperbound': upper_bound}
    return simplified_rolls


def get_user_army(user_id):
    return list(db.Army.find({'_id': user_id}, {'_id': 0}))[0]

def get_rankings(): #Must change to be only top 50
    return list(db.Nations.find().sort([('battle_rating', -1), ('_id', -1)]).limit(10))

def get_user_rank(user_id): #Must change to be only top 50
    allPlayersSorted = list(db.Nations.find().sort([('battle_rating', -1), ('_id', -1)]).limit(10))
    numPlayers = db.Nations.count_documents({})
    for i in range(len(allPlayersSorted)):
        if allPlayersSorted[i]['_id'] == user_id:
            return i+1, numPlayers

def get_age(user_id):
    return list(db.Nations.find({'_id': user_id}, {'_id': 0}))[0]['age']

def get_victims(user_id):
    userBR = list(db.Nations.find({'_id': user_id}, {'_id': 0}))[0]['battle_rating']
    upperRange = userBR + battle_rating_range
    lowerRange = userBR - battle_rating_range
    #Might need refactor for a lot of players
    playerList = list(db.Nations.find().sort('battle_rating', -1))
    attackablePlayers = []
    for player in playerList:
        if player['battle_rating'] in range(lowerRange, upperRange) and not has_shield(player['_id'], time.time()):
            if not player['_id'] == user_id: #Exclude self player
                attackablePlayers.append(player['username'])
    return attackablePlayers

def get_buildings():
    return ['granary', 'lumbermill', 'quarry', 'oilrig', 'oil rig', 'market', 'university']

def get_buildings_costs():
    buildingCosts = { 
        'granary': { 'timber': 1000, 'metal': 1000, },
        'lumbermill': { 'timber': 3000, 'metal': 3000, },
        'quarry': { 'timber': 3000, 'metal': 3000, },
        'oilrig': { 'metal': 5000, 'wealth': 5000, },
        'market': { 'food': 1000, 'timber': 1000, 'wealth': 1000,},
        'university': { 'timber': 1500, 'metal': 1500, 'wealth': 1500,},
    }
    return buildingCosts

def get_age_costs():
    ageCosts = {
        'medival': 100000,
        'englightment': 500000,
        'modern': 1000000,
        'space': 2000000,
    }
    return ageCosts


def get_num_users():
    return db.Nations.count_documents({})

"""UPDATE DATA FUNCTIONS"""
def update_resources(userID, resDict):
    db.Resources.update_one({'_id': userID}, {'$set': resDict})
    return

def update_resource_rate(userID, resDict):
    db.Resources.update_one({'_id': userID}, {'$set': resDict})
    return

def update_units(userID, unit, numUnits):
    data = list(db.Army.find({'_id': userID}, {'_id': 0}))[0]
    db.Army.update_one({'_id': userID}, {'$set': {unit: data[unit] + int(numUnits)}})
    return 

def update_building(userID, building, buildingDict):
    db.Nations.update_one({'_id': userID}, {'$set': {building: buildingDict[building]}}) # switches false to true and level -> 1
    return

def update_nation(userID, data):
    db.Nations.update_one({'_id': userID}, {'$set': data}) # switches false to true and level -> 1

"""GAME SERVICE FUNCTIONS """
def attackSequence(attacker_id, defender_id):
    attacker_army = list(db.Army.find({'_id': attacker_id}, {'_id': 0}))[0]
    defender_army = list(db.Army.find({'_id': defender_id}, {'_id': 0}))[0]
    
    #This is to not let add defense units to attackers force
    non_combat_units = ['keep', 'castle', 'fortress', 'bunker', 'planetary_fortress']
    for unit in non_combat_units:
        if unit in attacker_army:
            del attacker_army[unit]

    attacker_army_key_list = list(attacker_army.keys())
    defender_army_key_list = list(defender_army.keys())
    unit_dice_rolls = get_unit_dice_rolls()
    attacker_casualties = {}
    defender_casualties = {}
    i = j = 2 # i think im trying to skip user info and go straight to army data
    while i < len(attacker_army_key_list) and j < len(defender_army_key_list):      
        attacker_unit_count = attacker_army[attacker_army_key_list[i]]
        defender_unit_count = defender_army[defender_army_key_list[j]]
        # print('DEBUG', 'ATTACKER_UNIT_COUNT:', attacker_unit_count, 'DEFENDER_UNIT_COUNT', defender_unit_count)
        if attacker_unit_count == 0: #attacker has no units left, for the specific unit
            print('attacker unit', attacker_army_key_list[i])
            print('defender unit', defender_army_key_list[j])
            i += 1 #move to next unit in the list
            winner = [defender_id, defender_casualties, defender_army]
            loser = [attacker_id, attacker_casualties, attacker_army]
        if defender_unit_count == 0: #defender has no units left, for the specific unit
            j += 1 #move to next unit in the list
            winner = [attacker_id, attacker_casualties, attacker_army]
            loser = [defender_id, defender_casualties, defender_army]
        else: #combat simulation
            attackerRoll = random.randint(unit_dice_rolls[attacker_army_key_list[i]]['lowerbound'], unit_dice_rolls[attacker_army_key_list[i]]['upperbound'])
            defenderRoll = random.randint(unit_dice_rolls[defender_army_key_list[j]]['lowerbound'], unit_dice_rolls[defender_army_key_list[j]]['upperbound'])
            if attackerRoll > defenderRoll:
                #update casualties
                if defender_army_key_list[j] in defender_casualties:
                    defender_casualties[defender_army_key_list[j]] += 1 #increment casualty counter
                else: 
                    defender_casualties[defender_army_key_list[j]] = 1 #set casualty counter if new unit
                #reduce army by lost unit
                defender_army[defender_army_key_list[j]] -= 1
                winner = [attacker_id, attacker_casualties, attacker_army]
                loser = [defender_id, defender_casualties, defender_army]
            elif attackerRoll < defenderRoll:
                #update casualties
                if attacker_army_key_list[i] in attacker_casualties:
                    attacker_casualties[attacker_army_key_list[i]] += 1 #increment casualty counter
                else: 
                    attacker_casualties[attacker_army_key_list[i]] = 1 #set casualty counter if new unit
                #reduce army by lost unit
                attacker_army[attacker_army_key_list[i]] -= 1
                winner = [defender_id, defender_casualties, defender_army]
                loser = [attacker_id, attacker_casualties, attacker_army]

    #Update users' battle rating and shields
    loser_data = list(db.Nations.find({'_id': loser[0]}))
    # pprint.pprint(loserData)
    if len(loser_data) == 0:
        loser_data = list(db.Nations.find({'_id': loser[0]}))[0]
    else:
        loser_data = loser_data[0]
       
    winner_data = list(db.Nations.find({'_id': winner[0]}))
    if len(winner_data) == 0:
        winner_data = list(db.Nations.find({'_id': winner[0]}))[0]
    else:
        winner_data = winner_data[0]
    db.Nations.update_one({'_id': winner[0]}, {'$set': {'battle_rating': winner_data['battle_rating'] + battle_rating_increase}})
    if loser_data['battle_rating'] - battle_rating_increase >= 0:
        db.Nations.update_one({'_id': loser[0]}, {'$set': {'battle_rating': loser_data['battle_rating'] - battle_rating_increase, 'shield': time.time() + 86400}})
        loserRating = loser_data['battle_rating'] - battle_rating_increase
    if loser_data['battle_rating'] - battle_rating_increase < 0:
        db.Nations.update_one({'_id': loser[0]}, {'$set': {'battle_rating': 0, 'shield': time.time() + 86400}})
        loserRating = 0
    #Update users Army from casualties
    attacker_army.pop('_id', None)
    db.Army.update_one({'_id': winner[0]}, {'$set': winner[2]})
    db.Army.update_one({'_id': loser[0]}, {'$set': loser[2]})
    #Add tribute (steal 20% of resources + 3x bonus loot)
    loserResources = list(db.Resources.find({'_id': loser[0]}))[0]
    winnerResources = list(db.Resources.find({'_id': winner[0]}))[0]
    resList = ['food', 'timber', 'metal', 'wealth', 'oil', 'knowledge'] #there are other fields aside from resources
    totalBonusLoot = {} #used for summary
    for resource in loserResources:
        if resource in resList:
            amountTaken = math.ceil(loserResources[resource] * steal_percentage) #steal 10%
            winnerResources[resource] = winnerResources[resource] + (amountTaken * bonus_loot_multiplier)
            loserResources[resource] = loserResources[resource] - amountTaken
            totalBonusLoot[resource] = (amountTaken)
    db.Resources.update_one({'_id': winner[0]}, {'$set': winnerResources})
    db.Resources.update_one({'_id': loser[0]}, {'$set': loserResources})

    pprint.pprint(winner_data)
    pprint.pprint(loser_data)
    battleSummary = {
        'winner': winner_data['name'].upper(),
        'loser': loser_data['name'].upper(),
        'winner_username': winner_data['username'],
        'loser_username': loser_data['username'],
        'winner_motto': winner_data['motto'],
        'winner_battle_rating': str(winner_data['battle_rating'] + battle_rating_increase),
        'loser_battle_rating': str(winner_data['battle_rating'] - battle_rating_increase),
        'tribute': totalBonusLoot,
        'loser_battle_rating': str(loserRating),
        'attacker_casualties': str(attacker_casualties),
        'defender_casualties': str(defender_casualties),
    }
    return battleSummary

def validate_execute_shop(userID, unit, numUnits):
    data = list(db.Resources.find({'_id': userID}, {'_id': 0}))[0]
    unit_costs = get_unit_costs()
    #Calculates the the total cost for the unit you are buying
    for resource in unit_costs[unit]:
        unit_costs[unit][resource] *= int(numUnits)
    totalCost = unit_costs[unit]
    newResourceBalance = {}
    #Checks to see if you have enough resources
    for resource in totalCost:
        newResourceBalance[resource] = data[resource] - totalCost[resource]
        if data[resource] - totalCost[resource] < 0:
            return [False]
    return [True, newResourceBalance]

def buy_building(user_id, building, num_build):
    num_build = int(num_build)
    age = get_age(user_id)
    rate_increase = age_resource_rate_increases[age]
    res_data = list(db.Resources.find({'_id': user_id}, {'_id': 0}))[0]
    nation_data = list(db.Nations.find({'_id': user_id}, {'_id': 0}))[0]

    buildingCosts = get_buildings_costs()
    cost = buildingCosts[building]
    
    for resource in cost:
        if res_data[resource] - cost[resource] * num_build >= 0:
            res_data[resource] -= cost[resource] * num_build
            update_resources(user_id, res_data)
        else:
            return False
    nation_data[building] += num_build
    if building == 'granary': 
        res_data['food_rate'] += rate_increase * num_build
    if building == 'lumbermill' or building == 'lumber mill': 
        res_data['timber_rate'] += rate_increase * num_build
    if building == 'quarry': 
        res_data['metal_rate'] += rate_increase * num_build
    if building == 'oilrig' or building == 'oil rig': 
        res_data['oil_rate'] += rate_increase * num_build
    if building == 'market': 
        res_data['wealth_rate'] += rate_increase * num_build
    if building == 'university': 
        res_data['knowledge_rate'] += rate_increase * num_build
    update_building(user_id, building, nation_data)
    update_resource_rate(user_id, res_data)
    return True

def upgrade_age(userID):
    userData = get_user_stats(userID)
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
    ageCosts = get_age_costs()
    if userData['resources']['knowledge'] - ageCosts[nextAge] > 0:
        knowledgeCost = {'knowledge': userData['resources']['knowledge'] - ageCosts[nextAge]}
        update_resources(userID, knowledgeCost)
        update_nation(userID, {'age': nextAge})        
        return [True, nextAge]
    return [False, nextAge]

"""HELPER FUNCTIONS"""
def format_unit_info(unit, costs, rolls):
    return (
        f'{unit.capitalize()} - '
        f'Costs: {costs["food"]} food, {costs["timber"]} timber | '
        f'Rolls: {rolls["lowerbound"]}-{rolls["upperbound"]}'
    )

def display_units_in_era(era):
    units_info = get_all_units_info()
    formatted_output = f'===== Units Information ({era.capitalize()} Era) =====\n'

    if era.lower() in units_info:
        for unit, data in units_info[era.lower()].items():
            formatted_output += format_unit_info(unit, data['costs'], data['rolls']) + '\n'
    else:
        formatted_output += f'No units available for the {era.capitalize()} Era.\n'

    return formatted_output

def direct_message_user():
    pass
