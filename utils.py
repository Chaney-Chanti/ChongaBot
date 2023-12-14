
import json
import pymongo
import os
import random
import time
import math
import schedule
from datetime import datetime, timedelta
from pytz import timezone
from dotenv import load_dotenv
import pprint

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
    'ancient': 100,
    'medieval': 200,
    'enlightment': 500,
    'modern': 1000,
    'space': 1500
}
steal_percentage = 0.1
bonus_loot_multiplier = 3
battle_rating_increase = 25
random.seed(a=None)
big_loot_bonus = 3
unit_capacities = { # probably move this into the units info section
    'explorer': 500,
    'caravan': 1000,
    'conquistador': 2000,
    'spy': 5000,
    'tradeship': 10000,
}
shield_length = 86400 #1 day shield

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

def check_shop(userID, arg, arg2):
    #get number of arguments
    if arg != None:
        arg = arg.lower()
        num_args = arg.split()
        if not check_nation_exists(userID):
            return (True, 'User does not exist idiot!')
        if len(num_args) > 2:
            return(True, f'Incorrect parameters. Format: {prefix}shop or {prefix}shop unit number')
        if arg not in get_all_units():
            return(True, 'Unit does not exist')
        if int(arg2) <= 0:
            return(True, 'You must specify a positive number of units')
    return (False, 'OK')

def check_build(userID, arg1, arg2):
    buildings = get_buildings()
    if arg1 != None and arg2 != None:
        arg1 = arg1.lower()
        arg2 = arg2.lower()
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
        if len(num_args) > 1:
            return(True, f'Incorrect parameters. Format: {prefix}attack or {prefix}attack username')
        if len(ctx.message.mentions) == 1:
            target_id = ctx.message.mentions[0].id
        else:
            target_id = get_user_id_from_username(arg)
        print(user_id, arg, target_id)
        #go through checks
        if has_shield(target_id, time.time()):
            return (True, 'This player has a shield, you can\'t attack them...')
        print('checking if user has army')
        if not has_army(user_id):
            return (True, 'Stop the cap you have no army...')
        if ctx.message.author.id == target_id:
            return (True, 'You cannot attack yourself...')
        if not player_exists_via_id(target_id):
            return (True, 'User does not exist idiot!')
        if not check_in_battle_rating_range(user_id, target_id):
            # battle_rating_range = data.get('battle_rating_range')
            return (True, f'Your battle rating is either to high or to low (+-{battle_rating_range})')
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
    print('time passed in hours', time_passed_hours)
    if time_passed_hours <= 6:
        time_remaining_seconds = 21600 - ((current_time - user_stats['last_explore']))
        print('time remaining in seconds', 21600 - (current_time - user_stats['last_explore']) % 3600)
        # Convert time remaining to hours, minutes, and seconds
        remaining_hours = time_remaining_seconds // 3600
        remaining_minutes, remaining_seconds = divmod(time_remaining_seconds % 3600, 60)
        print(remaining_hours, remaining_minutes, remaining_seconds)
        return (True, f'```Next Expedition in: {remaining_hours} hours, {remaining_minutes} minutes, {int(remaining_seconds)} seconds```')
    if user_army['explorer'] <= 0 and user_army['caravan'] <= 0 and user_army['conquistador'] <= 0 and user_army['spy'] <= 0 and user_army['tradeship'] <= 0:
        return (True, '```You do not have any exploration units```')
    # if not arg.isnumeric(): #to allocate units
    #     return (True, '```You must specify a number of units to send```')
    return (False, 'OK')

def check_motto(ctx, user_id, arg):
    profanity_words = ['']
    if len(arg) > 50:
        return (True, '```Motto limited to 50 characters...```')
    for word in arg:
        if word.lower() in profanity_words:
            return (True, '```Profanity detected...```')
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
        'ancient': {
            'slinger': { 
                'costs': {'food': 200},
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'clubman': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
            'spearman': { 
                'costs': {'food': 200, 'timber': 200, },
                'rolls': {'lowerbound': 1, 'upperbound': 15, },
            },
            'archer': { 
                'costs': {'food': 300, 'timber': 300, },
                'rolls': {'lowerbound': 1, 'upperbound': 20, },
            },
            'keep': { 
                'costs': {'timber': 2000, },
                'rolls': {'lowerbound': 10, 'upperbound': 50, },
            },
            'explorer': { 
                'costs': {'food': 1000, 'wealth': 200},
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
            },
        },
        'medieval': {
            'knight': { 
                'costs': {'food': 400, 'metal': 400, },
                'rolls': {'lowerbound': 10, 'upperbound': 20, },
            },
            'crossbowman': { 
                'costs': {'food': 400, 'timber': 500, },
                'rolls': {'lowerbound': 10, 'upperbound': 30, },
            },
            'cavalry': { 
                'costs': {'food': 500, 'metal': 500, },
                'rolls': {'lowerbound': 10, 'upperbound': 35, },
            },
            'trebuchet': { 
                'costs': {'timber': 600, 'metal': 600, },
                'rolls': {'lowerbound': 10, 'upperbound': 45, },
            },
            'war_elephant': { 
                'costs': {'food': 800, 'timber': 800, },
                'rolls': {'lowerbound': 20, 'upperbound': 80, },
            },
            'castle': { 
                'costs': {'food': 1000, 'timber': 1000, 'metal': 1000, 'wealth': 1000},
                'rolls': {'lowerbound': 30, 'upperbound': 100, },
            },
            'caravan': { 
                'costs': {'food': 1500},
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
            },
        },
        'enlightment': {
            'minutemen':{ 
                'costs': {'food': 1000, 'metal': 500, },
                'rolls': {'lowerbound': 20, 'upperbound': 40, },
            },
            'general': { 
                'costs': {'food': 1500},
                'rolls': {'lowerbound': 20, 'upperbound': 50, },
            },
            'cannon': { 
                'costs': {'timber': 1200, 'metal': 1200, },
                'rolls': {'lowerbound': 30, 'upperbound': 90, },
            },
            'armada': { 
                'costs': {'timber': 10000, 'metal': 10000, 'wealth': 10000 },
                'rolls': {'lowerbound': 80, 'upperbound': 200, },
            },
            'fortress': { 
                'costs': {'food': 20000, 'timber': 20000, 'metal': 20000, 'wealth': 20000},
                'rolls': {'lowerbound': 100, 'upperbound': 800, },
            },
            'conquistador': { 
                'costs': {'food': 2000,},
                'rolls': {'lowerbound': 10, 'upperbound': 20, },
            },
        },
        'modern': {
            'infantry': { 
                'costs': {'food': 2000, 'metal': 1000, 'wealth': 500},
                'rolls': {'lowerbound': 40, 'upperbound': 60, },
            },
            'tank': { 
                'costs': {'metal': 5000, 'wealth': 5000, 'oil': 5000},
                'rolls': {'lowerbound': 100, 'upperbound': 200, },
            },
            'fighter': { 
                'costs': {'metal': 6000, 'wealth': 6000, 'oil': 6000},
                'rolls': {'lowerbound': 100, 'upperbound': 250, },
            },
            'bomber': { 
                'costs': {'metal': 8000, 'wealth': 8000, 'oil': 8000},
                'rolls': {'lowerbound': 120, 'upperbound': 270, },
            },
            'battleship': { 
                'costs': {'metal': 10000, 'wealth': 10000, 'oil': 10000},
                'rolls': {'lowerbound': 200, 'upperbound': 400, },
            },
            'aircraft_carrier': { 
                'costs': {'metal': 20000, 'wealth': 20000, 'oil': 20000},
                'rolls': {'lowerbound': 500, 'upperbound': 1000, },
            },
            'icbm': { 
                'costs': {'metal': 50000, 'wealth': 50000, 'oil': 50000},
                'rolls': {'lowerbound': 1000, 'upperbound': 2000, },
            },
            'bunker': { 
                'costs': {'metal': 100000, 'wealth': 100000, 'oil': 100000},
                'rolls': {'lowerbound': 1500, 'upperbound': 4000, },
            },
            'spy': { 
                'costs': {'food': 4000,},
                'rolls': {'lowerbound': 10, 'upperbound': 20, },
            },
        },
        'space' : {
            'shocktrooper': { 
                'costs': {'food': 6000, 'metal': 6000, 'wealth': 6000},
                'rolls': {'lowerbound': 100, 'upperbound': 250, },
            },
            'lasercannon': { 
                'costs': {'metal': 10000, 'wealth': 10000, 'oil': 10000},
                'rolls': {'lowerbound': 250, 'upperbound': 450, },
            },
            'starfighter': { 
                'costs': {'metal': 50000, 'wealth': 50000, 'oil': 50000},
                'rolls': {'lowerbound': 750, 'upperbound': 1500, },
            },
            'battlecruiser': { 
                'costs': {'metal': 500000, 'wealth': 500000, 'oil': 500000},
                'rolls': {'lowerbound': 5000, 'upperbound': 10000, },
            },
            'deathstar': { 
                'costs': {'metal': 5000000, 'wealth': 5000000, 'oil': 5000000},
                'rolls': {'lowerbound': 20000, 'upperbound': 50000, },
            },
               'planetary_fortress': { 
                'costs': {'metal': 100000, 'wealth': 100000, 'oil': 100000},
                'rolls': {'lowerbound': 40000, 'upperbound': 100000, },
            },
               'tradeship': { 
                'costs': {'food': 5000, 'metal': 5000, 'wealth': 5000, 'oil': 5000},
                'rolls': {'lowerbound': 50, 'upperbound': 100, },
            },
        },
    }

def get_events():
    pass

def get_exploration_events():
  return {
    (0.00, 0.35): { #free resources
        'free_resources': 'free_resources',
        'ancient': 1000,
        'medieval': 5000,
        'enlightenment': 10000,
        'modern': 20000,
        'space': 40000,
    },
    (0.35, 0.70): { #free units
        'free_units': 'free_units',
        'ancient': get_unit_names_by_age('ancient'),
        'medieval': get_unit_names_by_age('medieval'),
        'enlightenment': get_unit_names_by_age('enlightment'),
        'modern': get_unit_names_by_age('modern'),
        'space': get_unit_names_by_age('space'),
    },
    (0.70, 0.90): { #resource rate increases
        'trade_route': 'trade_route',
        'ancient': 100,
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
        'ancient': 1000,
        'medieval': 5000,
        'enlightenment': 10000,
        'modern': 20000,
        'space': 40000,
    },
    (0.99, 1.01): { #wonder
        'wonder': 'wonder',
        'ancient': [],
        'medieval': [],
        'enlightenment': [],
        'modern': [],
        'space': [],
    },
}

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
        'medival': 200000,
        'englightment': 500000,
        'modern': 1000000,
        'space': 2000000,
    }
    return ageCosts

def get_wonder_info():
    return {
        'ancient': {
            # 'pyramids': {
            #     'desc': 'increase'
            # },
            # 'colossus': {
            #     'desc': 'increase'
            # },
            'hanging_gardens': {
                'desc': 'increase food production by 1.25x',
                'bonus': 1.25,
            },
            # 'machu_picchu': {
            #     'desc': 'increase'
            # },
            # 'temple_of_zeus': {
            #     'desc': 'increase'
            # },
            'the_great_wall_of_chonga': {
                'desc': 'increase rolls for defense units by 1.25x',
                'bonus': 1.25,
            }
        },
        'medieval': {
            'terra_chonga_army': {
                 'desc': 'buy one get one free unit',
                 'bonus': 1
            },
            'colloseum': {
                 'desc': 'increase unit rolls by 1.25x (not defense units)',
                 'bonus': 1.25,
            },
            'the_black_forest': {
                 'desc': 'increase timber production by 1.25x',
                 'bonus': 1.25,
            },
            # 'forbidden_city_of_chonga': {
            #      'desc': 'increase'
            # },
        },
        'enlightment': {
            'palace_of_versailles': {
                'desc': 'increase knowledge production by 1.25x',
                'bonus': 1.25,
            },
            'the_chongalayas': {
                'desc': 'increase metal production by 1.25x',
                'bonus': 1.25,
            },
            # 'taj_mahal': {
            #     'desc': 'increase'
            # },
        },
        'modern': {
            'the_rivers_of_chonga': {
                'desc': 'increase wealth production by 1.25x',
                'bonus': 1.25,
            },
            'supercollider': {
                'desc': 'if attacked by icbm, reduce roll by 75%',
                'bonus': .25,
            },
            'the_oil_fields_of_chonga': {
                'desc': 'increase oil production by 1.25x',
                'bonus': 1.25,
            },
            # 'eiffel_tower': {
            #     'desc': 'increase'
            # },
            # 'empire_state_building': {
            #     'desc': 'increase'
            # },
            # 'birj_khalifa': {
            #     'desc': 'increase'
            # },
            # 'big_ben': {
            #     'desc': 'increase'
            # },
        },
        'space':{
            # 'nebula_of_visions': {
            #     'desc': 'increase'
            # },
            # 'the_answer_to_infinity': {
            #     'desc': 'increase'
            # },
            'white_hole': {
                'desc': 'get 1.25x resources per claim',
                'bonus': 1.25,
            },
            'galatic_empire': {
                'desc': 'increase collection rate by 10000 of every resource',
                'bonus': 10000,
            },
        },
    }

#returns a list of all the wonders
def get_wonder_list():
    wonders_list = []
    wonders_data = get_wonder_info()
    for age, wonders in wonders_data.items():
        wonders_list.extend(wonders.keys())
    return wonders_list

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
def battle_rating_rewards():
    pass

def attackSequence(attacker_id, defender_id):
    attacker_army = list(db.Army.find({'_id': attacker_id}, {'_id': 0}))[0]
    defender_army = list(db.Army.find({'_id': defender_id}, {'_id': 0}))[0]
    attacker_stats = get_user_stats(attacker_id)
    defender_stats = get_user_stats(defender_id)

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
    #by default set attacker to winner in the case the defender has no army
    winner = [attacker_id, attacker_casualties, attacker_army]
    loser = [defender_id, defender_casualties, defender_army]
    
    while i < len(attacker_army_key_list) and j < len(defender_army_key_list):      
        attacker_unit_count = attacker_army[attacker_army_key_list[i]]
        defender_unit_count = defender_army[defender_army_key_list[j]]
        # print('DEBUG', 'ATTACKER_UNIT_COUNT:', attacker_unit_count, 'DEFENDER_UNIT_COUNT', defender_unit_count)
        if attacker_unit_count == 0: #attacker has no units left, for the specific unit
            i += 1 #move to next unit in the list
        elif defender_unit_count == 0: #defender has no units left, for the specific unit
            j += 1 #move to next unit in the list
        else: #combat simulation
            attackerRoll = random.randint(unit_dice_rolls[attacker_army_key_list[i]]['lowerbound'], unit_dice_rolls[attacker_army_key_list[i]]['upperbound'])
            defenderRoll = random.randint(unit_dice_rolls[defender_army_key_list[j]]['lowerbound'], unit_dice_rolls[defender_army_key_list[j]]['upperbound'])

            #roll processing
            if attacker_stats['wonder'] == 'colloseum' and unit_dice_rolls[attacker_army_key_list[i]] not in ['keep', 'castle', 'fortress', 'bunker', 'planetary_fortress']:
                attackerRoll *= 1.25
            if defender_stats['wonder'] == 'colloseum' and unit_dice_rolls[attacker_army_key_list[i]] not in ['keep', 'castle', 'fortress', 'bunker', 'planetary_fortress']:
                defenderRoll *= 1.25
            if attacker_stats['wonder'] == 'the_great_wall_of_chonga' and unit_dice_rolls[attacker_army_key_list[i]] in ['keep', 'castle', 'fortress', 'bunker', 'planetary_fortress']:
                attackerRoll *= 1.25
            if defender_stats['wonder'] == 'the_great_wall_of_chonga' and unit_dice_rolls[attacker_army_key_list[i]] in ['keep', 'castle', 'fortress', 'bunker', 'planetary_fortress']:
                defenderRoll *= 1.25
            if attacker_stats['wonder'] == 'supercollider' and unit_dice_rolls[attacker_army_key_list[i]] == 'icbm':
                defenderRoll *= .25
            if defender_stats['wonder'] == 'supercollider' and unit_dice_rolls[attacker_army_key_list[i]] == 'icbm':
                attackerRoll *= .25

            if attackerRoll > defenderRoll:
                #update casualties
                if defender_army_key_list[j] in defender_casualties:
                    defender_casualties[defender_army_key_list[j]] += 1 #increment casualty counter
                else: 
                    defender_casualties[defender_army_key_list[j]] = 1 #set casualty counter if new unit
                defender_army[defender_army_key_list[j]] -= 1 #reduce army by lost unit
                winner = [attacker_id, attacker_casualties, attacker_army]
                loser = [defender_id, defender_casualties, defender_army]
            elif attackerRoll < defenderRoll:
                #update casualties
                if attacker_army_key_list[i] in attacker_casualties:
                    attacker_casualties[attacker_army_key_list[i]] += 1 #increment casualty counter
                else: 
                    attacker_casualties[attacker_army_key_list[i]] = 1 #set casualty counter if new unit
                attacker_army[attacker_army_key_list[i]] -= 1 #reduce army by lost unit
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
        db.Nations.update_one({'_id': loser[0]}, {'$set': {'battle_rating': loser_data['battle_rating'] - battle_rating_increase, 'shield': time.time() + shield_length}})
        loserRating = loser_data['battle_rating'] - battle_rating_increase
    if loser_data['battle_rating'] - battle_rating_increase < 0:
        db.Nations.update_one({'_id': loser[0]}, {'$set': {'battle_rating': 0, 'shield': time.time() + shield_length}})
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

def explore(user_id, user_army):
    data = get_user_stats(user_id)
    user_age = get_age(user_id)
    explorer_units = ['explorer', 'caravan', 'conquistador', 'spy', 'tradeship']
    users_explorer_units = {key: user_army[key] for key in explorer_units if key in user_army}
    event_chance = round(random.uniform(0, 1), 2) #generate random float between 0 and 1 (inclusive) with decimals to 2 places
    #find which event occurred
    for (lowerbound, upperbound), event in get_exploration_events().items():
        if lowerbound <= event_chance < upperbound:
            break
    if(event).get('free_resources') is not None:
        resources_gained = event[user_age]
        updated_resources = {}  # Initialize an empty dictionary to store the updated values

        num_units = 0
        for unit in users_explorer_units:
            num_units += user_army[unit]  # results in the number of units for each explorer unit
        # Iterate over each resource and update it in a cumulative manner
        for resource in ['food', 'timber', 'metal', 'wealth', 'oil', 'knowledge']:
            resource_key = resource  # Key in the data dictionary
            updated_resources[resource_key] = data['resources'][resource_key] + (resources_gained * num_units)
            # Update the data dictionary with the new value
            data['resources'][resource_key] = updated_resources[resource_key]

        update_resources(user_id, updated_resources)
        db.Nations.update_one({'_id': user_id}, {'$set': {'last_explore': time.time()}})
        return('```Your units befriended a nearby nation whom brough back gifts!\n' 
               + str(resources_gained * num_units) + ' (of every resource)```')
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
        num_units = 0
        for unit in users_explorer_units:
            num_units += user_army[unit]  # results in the number of units
            # Iterate over each resource and update it in a cumulative manner
        for resource in ['food', 'timber', 'metal', 'wealth', 'oil', 'knowledge']:
            resource_key = resource  # Key in the data dictionary
            updated_resources[resource_key] = data['resources'][resource_key] + ((resources_gained * big_loot_bonus) * num_units)
            # Update the data dictionary with the new value
            data['resources'][resource_key] = updated_resources[resource_key]
        update_resources(user_id, updated_resources)
        db.Nations.update_one({'_id': user_id}, {'$set': {'last_explore': time.time()}})
        return('```Your units conquered a small nation and brought back tribute!\n' +
               'Collected: ' + str((resources_gained * big_loot_bonus) * num_units) + ' (every resource)```')
    elif(event).get('wonder') is not None:
        print('Your units discovered a wonder!')
        wonder = random.choice(list(get_wonder_info()[user_age].keys()))
        db.Nations.update_one({'_id': user_id}, {'$set': {'last_explore': time.time()}})
        db.Nations.update_one({'_id': user_id}, {'$set': {'wonder': wonder}})
        return('```Your units discovered wonder!!!\nWonder: ' + format_wonder_name(wonder) + '```')
        
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
def format_unit_info(unit, data):
    costs_str = ', '.join([f'{resource.capitalize()}: {cost}' for resource, cost in data['costs'].items()])
    rolls_str = f'Rolls: {data["rolls"]["lowerbound"]}-{data["rolls"]["upperbound"]}'
    return f'{unit.capitalize()} - Costs: {costs_str} | {rolls_str}'

def format_wonder_name(name):
    words = name.split('_')
    formatted_name = ' '.join(word.capitalize() for word in words)
    return formatted_name

def display_units_in_era(era):
    units_info = get_all_units_info()
    formatted_output = f'===== Units Information ({era.capitalize()} Era) =====\n'

    if era.lower() in units_info:
        for unit, data in units_info[era.lower()].items():
            formatted_output += format_unit_info(unit, data) + '\n'
    else:
        formatted_output += f'No units available for the {era.capitalize()} Era.\n'

    return formatted_output

def direct_message_user():
    pass
