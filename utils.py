'''
TODO:
1. Seperate the utility functions into their own files by category: ie. gets, update, helpers, checks, etc.
2. move settings into its own file

'''
import json
import pymongo
import os
import random
import time
import math
import nextcord
import schedule
import sys
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
    'enlightenment': 500,
    'modern': 1000,
    'space': 1500
}
steal_percentage = 0.15
bonus_loot_multiplier = 3
battle_rating_increase = 25 #how much one gains and loses
random.seed(a=None)
big_loot_bonus = 3 #how much attacking bonus loot obtained for winning
shield_length = 86400 #1 day shield
exploration_cooldown = 21600
alliance_member_cap = 50
countries = [
    'India',
    'China',
    'Japan',
    'Korea',
    'Mongolia',
    'Thailand',
    'Vietnam',
    'The Phillipines',
    'Singapore',
    'Malaysia',
    'Australia'
    'New Zealand',
    'America',
    'Britain',
    'France',
    'Germany',
    'Spain',
    'Switzerland',
    'Italy',
    'Greece',
    'The Netherlands',
    'Russia',
    'Sweden',
    'Norway',
    'Finland',
    'Poland',
    'Austria',
    'Turkey',
    'Portugal',
    'Morrocoo',
    'Saudia Arabia',
    'Egypt',
    'Zimbabwe',
    'Madagascar',
    'Ethiopia',
    'Niger',
    'Ghana',
    'Brazil',
    'Argentina',
    'Chile',
    'Mexico',
    'Peru'
]

"""BOOLEAN CHECK FUNCTIONS"""
def general_checks(user_id):
     if db.Nations.count_documents({'_id': user_id}) < 0:
         return (True, 'Please Create a Nation before using any command')
     return (False, 'Checks Passed')

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

def check_shop(userID, arg1, arg2):
    #get number of arguments
    print(arg1, arg2)
    if arg1 != None:
        num_args = arg1.lower().split()
        if not check_nation_exists(userID):
            return (True, 'User does not exist idiot!')
        if len(num_args) > 2:
            return(True, f'Incorrect parameters. Format: {prefix}shop or {prefix}shop unit number')
        if arg1 not in get_list_of_all_units():
            return(True, 'Unit does not exist')
        if arg2 != None and arg2.isnumeric() and int(arg2) <= 0:
            return(True, 'You must specify a positive number of units')
    return (False, 'OK')

def check_build(userID, arg1, arg2):
    age = get_age(userID)
    buildings = get_buildings_by_age(age)
    print(arg1, arg2)
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
        if arg2 != None and arg2.isnumeric() and int(arg2) <= 0:
            return(True, 'You must specify a positive number of units')
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
        #go through checks
        if has_shield(target_id, time.time()):
            return (True, 'This player has a shield, you can\'t attack them...')
        if get_age(user_id) != get_age(target_id):
            return (True, 'This player is in a different age you bully...')
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
    if time_passed_hours <= 6:
        time_remaining_seconds = max(0, 21600 - ((current_time - user_stats['last_explore'])))
        # Convert time remaining to hours, minutes, and seconds
        remaining_hours = time_remaining_seconds // 3600
        remaining_minutes, remaining_seconds = divmod(time_remaining_seconds % 3600, 60)
        return (True, f'```Next Expedition in: {remaining_hours} hours, {remaining_minutes} minutes, {int(remaining_seconds)} seconds```')
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

def check_age(ctx, user_id):
    what_you_must_research = get_list_of_research_by_age(get_age(user_id))
    has_reasearched = get_users_researched_list(user_id)
    if what_you_must_research != has_reasearched:
        return (True, '```You must research all technologies in your age before you advance```')
    return (False, 'OK')
def check_in_battle_rating_range(attackerID, defenderID):
    player_one_rating = json.dumps(list(db.Nations.find({'_id': attackerID}, {'_id': 0}))[0]['battle_rating'])
    player_two_rating = json.dumps(list(db.Nations.find({'_id': defenderID}, {'_id': 0}))[0]['battle_rating'])
    # print('DEBUG', 'RATINGS: ', player_one_rating, player_two_rating)
    return abs(int(player_one_rating) - int(player_two_rating)) <= battle_rating_range 

def check_research(ctx, user_id, arg1):
    user_research = get_list_of_research_by_age(get_age(user_id))

    if arg1 != None and arg1 not in user_research:
        return (True, '```That is not a researchable topic IDIOT! Or you do not have access to the topic in your current era.```')
    if arg1 in get_users_researched_list(user_id):
        return (True, '```You have already researched this!```')
    return (False, 'OK')

def player_exists_via_id(userID):
    return db.Nations.count_documents({'_id': userID}) > 0

def player_exists_via_username(username):
    return db.Nations.count_documents({'username': username}) > 0

def has_shield(defenderID, currTime):
    return list(db.Nations.find({'_id': defenderID}, {'_id': 0}))[0]['shield'] >= currTime

def has_army(user_id):
    armyData = get_user_army(user_id)
    units = get_list_of_all_units()
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

def get_users_researched_list(user_id):
    return db.Nations.find_one({'_id': user_id}, {'researched_list': 1})['researched_list']

def get_user_wonders(user_id):
     return db.Nations.find_one({'_id': user_id}, {'owned_wonders': 1})['owned_wonders']

def get_user_username(user_id):
     return db.Nations.find_one({'_id': user_id}, {'username': 1})[0]['username']

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

def get_user_defense_buildings(user_id): # could be more dynamic
    return db.Nations.find({'_id': user_id}, {'_id': 0, 'keep': 1, 'castle': 1, 'fortress': 1, 'army_base': 1, 'planetary_fortress': 1})[0]

def get_list_of_resources():
    return ['food', 'timber', 'metal', 'oil', 'wealth', 'knowledge']

def get_list_of_units_by_age(era): #returns a list of the type of units available to the user
    if era in get_all_units_info():
        return list(get_all_units_info()[era].keys())
    else:
        return []
    
def get_list_of_hero_units_by_era(era):
    hero_units = []
    if era in get_all_units_info():
        units_info = get_all_units_info()[era]
        hero_units = [unit_name for unit_name, info in units_info.items() if info.get('hero', False)]
    return hero_units

def get_list_of_all_units():
    all_unit_names = []
    for era, units_info in get_all_units_info().items():
        era_unit_names = list(units_info.keys())
        all_unit_names.extend(era_unit_names)
    return all_unit_names

def get_list_of_normal_units_by_age(age):
    if age not in get_all_units_info():
        return []  # Return an empty list for invalid era

    normal_units = [unit_name for unit_name, unit_info in get_all_units_info()[age].items() if not unit_info['hero']]
    return normal_units

def get_buildings_costs_by_age(age):
    all_building_infos = get_all_building_infos()
    return all_building_infos.get(age.lower(), None)

def get_list_of_research_by_age(age):
    research_items = []
    research_info = get_all_research_info()
    if age in research_info:
        for research in research_info[age].keys():
            research_items.append(research)

    return research_items

def get_research_info_by_age(age):
    research_info = get_all_research_info()
    
    # Convert the age to lowercase to handle case-insensitivity
    age_lower = age.lower()

    if age_lower in research_info:
        return research_info[age_lower]
    else:
        return None  # Return None if the specified age is not found
    
def get_normal_units():
    filtered_units = {}
    units_info = get_all_units_info()  # Assuming you have a function get_all_units_info() that provides the unit information

    for age, age_units in units_info.items():
        filtered_age_units = {unit_name: unit_info for unit_name, unit_info in age_units.items() if not unit_info.get('hero', False)}
        if filtered_age_units:
            filtered_units[age] = filtered_age_units

    return filtered_units

def get_combat_wonders(users_wonders):
    wonder_info = get_list_of_wonder_info()
    combat_buffing_wonders = []
    combat_nerfing_wonders = []
    for wonder in users_wonders:
        if wonder_info[wonder]['civil'] == False:
            print(wonder_info[wonder])
            if wonder_info[wonder]['type'] == 'buff':
                combat_buffing_wonders.append(wonder)
            if wonder_info[wonder]['type'] == 'nerf':
                combat_nerfing_wonders.append(wonder)
    return (combat_buffing_wonders, combat_nerfing_wonders)

def get_hero_units():
    filtered_units = {}
    units_info = get_all_units_info()
    for age, age_units in units_info.items():
        filtered_age_units = {unit_name: unit_info for unit_name, unit_info in age_units.items() if unit_info.get('hero', True)}
        if filtered_age_units:
            filtered_units[age] = filtered_age_units

    return filtered_units

def get_unit_counters(): # keep in lists to potentially add more counters
    return {
        'building': ['melee'],
        'melee': ['ranged'],
        'ranged': ['light'],
        'light': ['heavy'],
        'heavy': ['building']
    }   

def get_all_research_info(): # return just research info, costs are in knowledge
    return {
        'ancient': {
            'pastures': { 
                'costs': 200,
                'desc': 'increases your current food production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'food_rate',
            },
            'carpentry': { 
                'costs': 200,
                'desc': 'increases your current timber production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'timber_rate',
            },      
            'metal_alloys': { 
                'costs': 200,
                'desc': 'increases your current metal production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'metal_rate',
            },
            'trading': { 
                'costs': 200,
                'desc': 'increases your current wealth production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'wealth_rate',
            },
            'paper': { 
                'costs': 200,
                'desc': 'increases your current knowledge production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'knowledge_rate',
            },
        },
        'medieval': {
            'indentured_servitude': { 
                'costs': 200,
                'desc': 'increases your current food production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'food_rate',                
            },
            'construction': { 
                'costs': 200,
                'desc': 'increases your current timber production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'timber_rate',
            },      
            'steel': { 
                'costs': 200,
                'desc': 'increases your current metal production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'metal_rate',
            },
            'currency': { 
                'costs': 200,
                'desc': 'increases your current wealth production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'wealth_rate',
            },
            'scientists': { 
                'costs': 200,
                'desc': 'increases your current knowledge production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'knowledge_rate',
            },
        },
        'enlightenment': {
            'plantations': { 
                'costs': 200,
                'desc': 'increases your current food production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'food_rate',
            },
            'engineering': { 
                'costs': 200,
                'desc': 'increases your current timber production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'timber_rate',
            },      
            'dynamite': { 
                'costs': 200,
                'desc': 'increases your current metal production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'metal_rate',
            },
            'standard_oil': { 
                'costs': 200,
                'desc': 'increases your current oil production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'oil_rate',
            },
            'imperialism': { 
                'costs': 200,
                'desc': 'increases your current wealth production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'knowledge_rate',

            },
            'philosophy': { 
                'costs': 200,
                'desc': 'increases your current knowledge production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'knowledge_rate',
            },
        },
        'modern': {
            'tractors': { 
                'costs': 200,
                'desc': 'increases your current food production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'food_rate',
            },
            'chainsaws': { 
                'costs': 200,
                'desc': 'increases your current timber production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'timber_rate',
            },      
            'the_boring_company': { 
                'costs': 200,
                'desc': 'increases your current metal production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'metal_rate'
            },
            'oil_refinery': { 
                'costs': 200,
                'desc': 'increases your current oil production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'oil_rate',
            },
            'capitalism': { 
                'costs': 200,
                'desc': 'increases your current wealth production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'wealth_rate',
            },
            'supercomputers': { 
                'costs': 200,
                'desc': 'increases your current knowledge production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'knowledge_rate',
            },
        },
        'space': {
            'terraforming': { 
                'costs': 200,
                'desc': 'increases your current food production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'food_rate',
            },
            'auto_tree_regeneration': { 
                'costs': 200,
                'desc': 'increases your current timber production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'timber_rate',
            },      
            'asteroid_mining': { 
                'costs': 200,
                'desc': 'increases your current metal production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'metal_rate',
            },
            'star_oil': { 
                'costs': 200,
                'desc': 'increases your current oil production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'oil_rate',
            },
            'galatic_trade': { 
                'costs': 200,
                'desc': 'increases your current wealth production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'wealth_rate',
            },
            'space_station': { 
                'costs': 200,
                'desc': 'increases your current knowledge production by 1.25x',
                'bonus': 1.25,
                'resource_rate': 'knowledge_rate',
            },
        },
    }

def get_all_bosses():
    return {
        'ancient': {
            'the_great_kingdom': {

            }
        },
        'medieval': {
            'the_inquisitors': {

            },
            'vinland': {

            },
            'the_black_beard_crew': {
            
            },
        },
        'enlightenment': {
            'vide_the_wicked': {

            },
            'paradis_island': {
                
            }
        },
        'modern': {
            ''
        },
        'space': {
            'the_galactic_empire': {

            },
            'the_jedi_order': {

            },
            'the_void_emperor': {

            },
            'the_zerg': {

            },
            'the_protoss': {

            },
            'the_terran': {

            },
            'kang_the_conquorer': {

            },
        }
    }

def get_all_units_info(): # return all units including heroes infos
    return {
        'ancient': {
            'slinger': { 
                'costs': {'food': 200},
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
                'combat_type': 'attack',
                'type': 'ranged',
                'hero': False,
            },
            'clubman': { 
                'costs': {'food': 100, 'timber': 100, },
                'rolls': {'lowerbound': 1, 'upperbound': 10, },
                'combat_type': 'attack',
                'type': 'melee',
                'hero': False,
            },
            'spearman': { 
                'costs': {'food': 300},
                'rolls': {'lowerbound': 1, 'upperbound': 15, },
                'combat_type': 'attack',
                'type': 'melee',
                'hero': False,
            },
            'archer': { 
                'costs': {'food': 400},
                'rolls': {'lowerbound': 1, 'upperbound': 20, },
                'combat_type': 'attack',
                'type': 'ranged',
                'hero': False,
            },
            'horseman': { 
                'costs': {'food': 400},
                'rolls': {'lowerbound': 1, 'upperbound': 20, },
                'combat_type': 'attack',
                'type': 'light',
                'hero': False,
            },
            'catapult': { 
                'costs': {'food': 400},
                'rolls': {'lowerbound': 1, 'upperbound': 20, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'cleopatra': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'ugly ass woman',
                'hero': True
            },
            'alexander_the_great': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'conquered the world in his 20s yet ur here playing chongabot',
                'hero': True,
            },
            'ramesses_ii': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'ramjamnutslam',
                'hero': True,
            },
            'atilla_the_hun': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'chad',
                'hero': True,

            },
            'caesar': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'CAAEEEEESAAAAEEEEERRRRRR',
                'hero': True,
            },
        },
        'medieval': {
            'knight': { 
                'costs': {'food': 1000, 'metal': 1000, },
                'rolls': {'lowerbound': 10, 'upperbound': 20, },
                'combat_type': 'attack',
                'type': 'melee',
                'hero': False,
            },
            'crossbowman': { 
                'costs': {'food': 1000, 'timber': 500, },
                'rolls': {'lowerbound': 10, 'upperbound': 30, },
                'combat_type': 'attack',
                'type': 'ranged',
                'hero': False,
            },
            'cavalry': { 
                'costs': {'food': 1500, 'metal': 1500, },
                'rolls': {'lowerbound': 10, 'upperbound': 35, },
                'combat_type': 'attack',
                'type': 'light',
                'hero': False,
            },
            'trebuchet': { 
                'costs': {'timber': 3000, 'metal': 3000, },
                'rolls': {'lowerbound': 10, 'upperbound': 45, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'war_elephant': { 
                'costs': {'food': 5000, 'metal': 3000, },
                'rolls': {'lowerbound': 20, 'upperbound': 80, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
             'king_arthur': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'desc': 'timothee chalamet',
                'type': 'melee',
                'hero': True,
            },
            'genghis_khan': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'buff asian guy with beard',
                'hero': True,
            },
            'william_the_conqueror': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'british guy',
                'hero': True,
            },
            'marco_polo': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'buffer',
                'type': None,
                'desc': '1.25x the exploration value',
                'hero': True,
            },
            'robinhood': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'ranged',
                'desc': 'steal an xtra 10% from enemies after attacking',
                'hero': True,
            },
            'leonardo_da_vinci': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'buffer',
                'type': None,
                'desc': 'reduce cost of researching by 1.25x',
                'hero': True,
            },
        },
        'enlightenment': {
            'minutemen':{ 
                'costs': {'food': 2000, 'metal': 2000, },
                'rolls': {'lowerbound': 20, 'upperbound': 40, },
                'combat_type': 'attack',
                'type': 'ranged',
                'hero': False,
            },
            'general': { 
                'costs': {'food': 2000, 'metal': 3000, },
                'rolls': {'lowerbound': 20, 'upperbound': 50, },
                'combat_type': 'attack',
                'type': 'light',
                'hero': False,
            },
            'cannon': { 
                'costs': {'timber': 2000, 'metal': 5000, },
                'rolls': {'lowerbound': 30, 'upperbound': 90, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'napolean': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'french guy',
                'hero': True,
            },
            'king_henry_viii': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'english guy',
                'hero': True,
            },
            'george_washington': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'light',
                'desc': 'british guy posing as an american',
                'hero': True,
            },
            'louis_xiv': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'light',
                'desc': 'another french guy',
                'hero': True,
            },
            'armada': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'heavy',
                'desc': 'how many ship?',                  
                'hero': True,
            }
        },
        'modern': {
            'commando': { 
                'costs': {'food': 2000, 'metal': 1000, 'wealth': 500},
                'rolls': {'lowerbound': 40, 'upperbound': 60, },
                'combat_type': 'attack',
                'type': 'melee',
                'hero': False,
            },
            'infantry': { 
                'costs': {'food': 2000, 'metal': 1000, 'wealth': 500},
                'rolls': {'lowerbound': 40, 'upperbound': 60, },
                'combat_type': 'attack',
                'type': 'ranged',
                'hero': False,
            },
            'tank': { 
                'costs': {'metal': 5000, 'wealth': 5000, 'oil': 5000},
                'rolls': {'lowerbound': 100, 'upperbound': 200, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'fighter': { 
                'costs': {'metal': 6000, 'wealth': 6000, 'oil': 6000},
                'rolls': {'lowerbound': 100, 'upperbound': 250, },
                'combat_type': 'attack',
                'type': 'light',
                'hero': False,
            },
            'bomber': { 
                'costs': {'metal': 8000, 'wealth': 8000, 'oil': 8000},
                'rolls': {'lowerbound': 120, 'upperbound': 270, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'submarine': { 
                'costs': {'metal': 10000, 'wealth': 10000, 'oil': 10000},
                'rolls': {'lowerbound': 200, 'upperbound': 400, },
                'combat_type': 'attack',
                'type': 'light',
                'hero': False,
            },
            'battleship': { 
                'costs': {'metal': 10000, 'wealth': 10000, 'oil': 10000},
                'rolls': {'lowerbound': 200, 'upperbound': 400, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'aircraft_carrier': { 
                'costs': {'metal': 20000, 'wealth': 20000, 'oil': 20000},
                'rolls': {'lowerbound': 500, 'upperbound': 1000, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'icbm': { 
                'costs': {'metal': 50000, 'wealth': 50000, 'oil': 50000},
                'rolls': {'lowerbound': 1000, 'upperbound': 2000, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'albert_einstein': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'buffer',
                'type': 'melee',
                'desc': 'cheapens the cost of research by 1.25x',
                'hero': True,
            },
            'mao_zedong': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'uuh ur chinese',
                'hero': True,
            },
            'winston_churchill': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'light',
                'desc': 'british guy in a tank',
                'hero': True,
            },
            'oppenheimer': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'buffer',
                'type': 'melee',
                'desc': 'allows you to buy the ICBM',
                'hero': True,
            },
            'warren_buffet': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'buffer',
                'type': 'melee',
                'desc': 'Gives you access to the c!invest command allowing you to invest in the irl stock market',
                'hero': True,
            },
        },
        'space' : {
            'shocktrooper': { 
                'costs': {'food': 6000, 'metal': 6000, 'wealth': 6000},
                'rolls': {'lowerbound': 100, 'upperbound': 250, },
                'combat_type': 'attack',
                'type': 'ranged',
                'hero': False,
            },
            'lasercannon': { 
                'costs': {'metal': 10000, 'wealth': 10000, 'oil': 10000},
                'rolls': {'lowerbound': 250, 'upperbound': 450, },
                'combat_type': 'attack',
                'type': 'light',
                'hero': False,
            },
            'thor': { 
                'costs': {'metal': 10000, 'wealth': 10000, 'oil': 10000},
                'rolls': {'lowerbound': 250, 'upperbound': 450, },
                'combat_type': 'attack',
                'type': 'light',
                'hero': False,
            },
            'starfighter': { 
                'costs': {'metal': 50000, 'wealth': 50000, 'oil': 50000},
                'rolls': {'lowerbound': 750, 'upperbound': 1500, },
                'combat_type': 'attack',
                'type': 'light',
                'hero': False,
            },
            'battlecruiser': { 
                'costs': {'metal': 500000, 'wealth': 500000, 'oil': 500000},
                'rolls': {'lowerbound': 5000, 'upperbound': 10000, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'deathstar': { 
                'costs': {'metal': 5000000, 'wealth': 5000000, 'oil': 5000000},
                'rolls': {'lowerbound': 50000, 'upperbound': 1000000, },
                'combat_type': 'attack',
                'type': 'heavy',
                'hero': False,
            },
            'cad_bane': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'heavy',
                'desc': 'doubles the amount of merceneries you can hire',
                'hero': True,
            },
            'the_malevolence': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'melee',
                'desc': 'green midget with a lightsaber',
                'hero': True,
            },
            'space_battleship_yamato': {
                'rolls': {'lowerbound': 1, 'upperbound': 5, },
                'combat_type': 'attack',
                'type': 'heavy',
                'desc': 'beeg sheep',
                'hero': True,
            },
        },
    }

def get_all_defense_unit_info():
    return {
        'ancient': {
            'keep': { 
                'costs': {'timber': 2000, },
                'rolls': {'lowerbound': 5, 'upperbound': 50, },
                'type': 'defense',
            },
        },
        'medieval': {
            'castle': { 
                'costs': {'food': 5000, 'timber': 5000, 'metal': 5000, 'wealth': 5000},
                'rolls': {'lowerbound': 30, 'upperbound': 100, },
                'type': 'defense',
            },
        },
        'enlightenment': {
            'fortress': { 
                'costs': {'food': 20000, 'timber': 20000, 'metal': 20000, 'wealth': 20000},
                'rolls': {'lowerbound': 100, 'upperbound': 400, },
            },
        },
        'modern': {
            'bunker': { 
                'costs': {'metal': 100000, 'wealth': 100000, 'oil': 100000},
                'rolls': {'lowerbound': 1000, 'upperbound': 4000, },
                'type': 'defense',
            },
        },
        'space' : {
               'planetary_fortress': { 
                'costs': {'metal': 100000, 'wealth': 100000, 'oil': 100000},
                'rolls': {'lowerbound': 40000, 'upperbound': 100000, },
                'type': 'defense',
            },
        },
    }

def get_exploration_events_chances():
  return {
    (0.00, 0.25): { #free resources
        'free_resources': {
            'ancient': {
                'lowerbound': 100,
                'upperbound': 10000
            },
            'medieval': {
                'lowerbound': 500,
                'upperbound': 20000
            },
            'enlightenment': {
                'lowerbound': 1000,
                'upperbound': 30000
            },
            'modern': {
                'lowerbound': 3000,
                'upperbound': 35000
            },
            'space': {
                'lowerbound': 5000,
                'upperbound': 40000,
            },
        },
    },
    (0.25, 0.50): { #free units
        'free_units': {
            'ancient': get_list_of_normal_units_by_age('ancient'),
            'medieval': get_list_of_normal_units_by_age('medieval'),
            'enlightenment': get_list_of_normal_units_by_age('enlightenment'),
            'modern': get_list_of_normal_units_by_age('modern'),
            'space': get_list_of_normal_units_by_age('space'),
        },
    },
    (0.50, 0.7): { #resource rate increases
        'trade_route': {
            'ancient': 100,
            'medieval': 200,
            'enlightenment': 500,
            'modern': 1000,
            'space': 2000,
        },
    },
    (0.70, 0.80): { #resource rate increases
        'hero_unit': {
            'ancient': get_list_of_hero_units_by_era('ancient'),
            'medieval': get_list_of_hero_units_by_era('medieval'),
            'enlightenment': get_list_of_hero_units_by_era('enlightenment'),
            'modern': get_list_of_hero_units_by_era('modern'),
            'space': get_list_of_hero_units_by_era('space'),
        },
    },
    (0.80, 0.90): { #pirates
        'pirates': {
            'ancient': (1,5),
            'medieval': (2,5),
            'enlightenment': (2,8),
            'modern': (2,10),
            'space': (2,20),
        },
    },
    (0.90, 1.00): { #wonder
        'wonder': {
            'ancient': get_list_of_wonders_by_age('ancient'),
            'medieval': get_list_of_wonders_by_age('medieval'),
            'enlightenment': get_list_of_wonders_by_age('enlightenment'),
            'modern': get_list_of_wonders_by_age('modern'),
            'space': get_list_of_wonders_by_age('space'),
        },
    },
}

#returns a list of units from that age
def get_users_available_units(age):
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
    return list(db.Army.find({'_id': user_id}, {'_id': 0, 'name': 0, 'username': 0}))[0]

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
    upper_range = userBR + battle_rating_range
    lower_range = userBR - battle_rating_range
    #Might need refactor for a lot of players
    player_list = list(db.Nations.find().sort('battle_rating', -1))
    attackable_players = []
    for player in player_list:
        if player['battle_rating'] in range(lower_range, upper_range) and not has_shield(player['_id'], time.time()):
            if not player['_id'] == user_id: #Exclude self player
                attackable_players.append(player['username'])
    return attackable_players

def get_buildings_by_age(age): #returns a list of the buildings in an era, for the future i want to maybe change building names
    all_building_info = get_all_building_infos()
    return all_building_info[age].keys()

def get_list_of_defense_buildings():
    defense_buildings = []
    building_info = get_all_building_infos()
    for era in building_info.values():
        for building in era.values():
            if building['type'] == 'defense':
                defense_buildings.append(list(building.keys())[0])

def get_all_building_infos():
    return {
        'ancient': {
            'granary': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'lumbermill': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'quarry': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'market': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'university': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'keep': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rolls': {'lowerbound': 100, 'upperbound': 200},
                'type': 'defense'
            }
        },
        'medieval': {
            'granary': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'lumbermill': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'quarry': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'market': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'university': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'castle': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rolls': {'lowerbound': 100, 'upperbound': 200},
                'type': 'defense'
            }
        },
        'enlightenment': {
            'granary': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'lumbermill': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'quarry':{
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'market': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'university': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'fortress': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rolls': {'lowerbound': 100, 'upperbound': 200},
                'type': 'defense'
            }
        },
        'modern': {
            'granary': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'lumbermill': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'quarry': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'oilrig': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'market': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'university': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'army_base': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rolls': {'lowerbound': 100, 'upperbound': 200},
                'type': 'defense'
            }
        },
        'space': {
            'granary': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'lumbermill': { # increases all resources
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'quarry': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'oilrig': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'market': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'university': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rate_increase': 100,
                'type': 'civil'
            },
            'planetary_fortress': {
                'costs': { 'timber': 1000, 'metal': 1000, },
                'rolls': {'lowerbound': 100, 'upperbound': 200},
                'type': 'defense'
            }
        },
    }

def get_age_costs():
    ageCosts = {
        'medieval': 200000,
        'enlightenment': 1000000,
        'modern': 2000000,
        'space': 10000000,
    }
    return ageCosts
def get_user_resources(user_id):
    return list(db.Resources.find({'_id': user_id}, {'_id': 0}))[0]

def get_list_of_wonders_by_age(age):
    wonders_info = get_wonder_info()
    eras = ['ancient', 'medieval', 'enlightenment', 'modern', 'space']
    if age not in eras:
        return {}
    return {era: wonders_info[era] for era in eras[:eras.index(age) + 1]}

def get_wonder_info():
    return {
        'ancient': {
            'pyramids': {
                'desc': 'cuts the cost of buildings by 25%',
                'bonus': .75,
                'civil': True,
            },
            'colossus': {
                'desc': 'decrease enemy units rolls by 25%',
                'bonus': .75,
                'civil': False,
                'type': 'nerf',
            },
            'hanging_gardens': {
                'desc': 'increase food production by 25%',
                'bonus': 1.25,
                'civil': True,
            },
            'the_great_wall_of_chonga': {
                'desc': 'increase rolls for defense units by 25%',
                'bonus': 1.25,
                'civil': True,
                'type': 'buff',
            }
        },
        'medieval': {
            'terra_chonga_army': {
                'desc': 'buy one get one free unit',
                'bonus': 2,
                'civil': True,
            },
            'colloseum': {
                'desc': 'increase unit rolls by 25% (not defense units)',
                'bonus': 1.25,
                'civil': False,
                'type': 'buff',
            },
            'the_black_forest': {
                 'desc': 'increase timber production by 25%',
                 'bonus': 1.25,
                 'civil': True,
            },
        },
        'enlightenment': {
            'palace_of_versailles': {
                'desc': 'increase knowledge production by 25%',
                'bonus': 1.25,
                'civil': True,
            },
            'the_chongalayas': {
                'desc': 'increase metal production by 25%',
                'bonus': 1.25,
                'civil': True,
            },
        },
        'modern': {
            'the_rivers_of_chonga': {
                'desc': 'increase wealth production by 25%',
                'bonus': 1.25,
                'civil': True,
            },
            'supercollider': {
                'desc': 'if attacked by icbm, reduce roll by 25%',
                'bonus': .75,
                'civil': False,
                'type': 'nerf'

            },
            'the_oil_fields_of_chonga': {
                'desc': 'increase oil production by 25%',
                'bonus': 1.25,
                'civil': True,
            },
        },
        'space':{
            'white_hole': {
                'desc': 'get 1.25x resources per claim',
                'bonus': .75,
                'civil': True,
            },
            'galatic_empire': {
                'desc': 'increase collection rate by 10000 of every resource',
                'bonus': 10000,
                'civil': True,
            },
        },
    }

def get_list_of_wonder_info():
    flat_wonder_info = {} 
    for era, wonders in get_wonder_info().items():
        for wonder, info in wonders.items():
            key = f"{wonder}"
            flat_wonder_info[key] = info

    return flat_wonder_info

def get_num_users():
    return db.Nations.count_documents({})

"""UPDATE DATA FUNCTIONS"""
def update_resources(user_id, res_dict):
    db.Resources.update_one({'_id': user_id}, {'$set': res_dict})
    return

def update_resource_rate(user_id, res_dict):
    db.Resources.update_one({'_id': user_id}, {'$set': res_dict})
    return

def update_units(user_id, unit, num_units):
    data = list(db.Army.find({'_id': user_id}, {'_id': 0}))[0]
    db.Army.update_one({'_id': user_id}, {'$set': {unit: data[unit] + int(num_units)}})
    return 

def update_army(user_id, army_dict):
    print(army_dict)
    db.Army.update_many({'_id': user_id}, {'$set': army_dict})
    return


def update_building(user_id, building, building_dict):
    db.Nations.update_one({'_id': user_id}, {'$set': {building: building_dict[building]}}) # switches false to true and level -> 1
    return

def update_nation(user_id, data):
    db.Nations.update_one({'_id': user_id}, {'$set': data}) # switches false to true and level -> 1

"""GAME SERVICE FUNCTIONS """
def battle_rating_rewards():
    pass

#returns the winner/loser, and casualties
def pirate_attack_sequence(user_id, pirate_army):
    attacker_army = list(db.Army.find({'_id': user_id}, {'_id': 0}))[0]
    attacker_stats = get_user_stats(user_id)

    attacker_army_key_list = list(attacker_army.keys())
    defender_army_key_list = list(pirate_army.keys())
    unit_dice_rolls = get_unit_dice_rolls()
    attacker_casualties = {}
    defender_casualties = {}
    i = 2
    j = 0 # becuase pirates dont have data like a real user



    #by default set attacker to winner in the case the defender has no army
    winner = ['user', attacker_casualties, attacker_army]
    loser = ['pirates', defender_casualties, pirate_army]
    
    while i < len(attacker_army_key_list) and j < len(defender_army_key_list):
        attacker_unit_count = attacker_army[attacker_army_key_list[i]]
        defender_unit_count = pirate_army[defender_army_key_list[j]]
        if attacker_unit_count == 0: #attacker has no units left, for the specific unit
            i += 1 #move to next unit in the list
        elif defender_unit_count == 0: #defender has no units left, for the specific unit
            j += 1 #move to next unit in the list
        else: #combat simulation
            attacker_unit_type = attacker_army_key_list[i]
            defender_unit_type = defender_army_key_list[j]
        
            attackerRoll = random.randint(unit_dice_rolls[attacker_unit_type]['lowerbound'], unit_dice_rolls[attacker_unit_type]['upperbound'])
            defenderRoll = random.randint(unit_dice_rolls[defender_unit_type]['lowerbound'], unit_dice_rolls[defender_unit_type]['upperbound'])

            # #roll processing
            # if attacker_stats['wonder'] == 'colloseum' and unit_dice_rolls[attacker_army_key_list[i]] not in ['keep', 'castle', 'fortress', 'bunker', 'planetary_fortress']:
            #     attackerRoll *= 1.25
            # if attacker_stats['wonder'] == 'the_great_wall_of_chonga' and unit_dice_rolls[attacker_army_key_list[i]] in ['keep', 'castle', 'fortress', 'bunker', 'planetary_fortress']:
            #     attackerRoll *= 1.25
            # if attacker_stats['wonder'] == 'supercollider' and unit_dice_rolls[attacker_army_key_list[i]] == 'icbm':
            #     defenderRoll *= .25
        
            if attackerRoll > defenderRoll:
                #update casualties
                if defender_army_key_list[j] in defender_casualties:
                    defender_casualties[defender_army_key_list[j]] += 1 #increment casualty counter
                else: 
                    defender_casualties[defender_army_key_list[j]] = 1 #set casualty counter if new unit
                pirate_army[defender_army_key_list[j]] -= 1 #reduce army by lost unit
                winner = [attacker_stats['name'], attacker_casualties, pirate_army]
                loser = ['PIRATES', defender_casualties, pirate_army]
            elif attackerRoll < defenderRoll:
                #update casualties
                if attacker_army_key_list[i] in attacker_casualties:
                    attacker_casualties[attacker_army_key_list[i]] += 1 #increment casualty counter
                else: 
                    attacker_casualties[attacker_army_key_list[i]] = 1 #set casualty counter if new unit
                attacker_army[attacker_army_key_list[i]] -= 1 #reduce army by lost unit
                winner = ['PIRATES', defender_casualties, pirate_army]
                loser = [attacker_stats['name'], attacker_casualties, attacker_army]

            total_bonus_loot = 10000

    # for resource in loser_resources:
    #     if resource in res_list:
    #         amount_taken = math.ceil(loser_resources[resource] * steal_percentage) #steal 10%
    #         winner_resources[resource] = winner_resources[resource] + (amount_taken * bonus_loot_multiplier)
    #         loser_resources[resource] = loser_resources[resource] - amount_taken
    #         total_bonus_loot[resource] = (amount_taken)

    # db.Resources.update_one({'_id': winner[0]}, {'$set': winner_resources})
    # db.Resources.update_one({'_id': loser[0]}, {'$set': loser_resources})

    if winner[0] == attacker_stats['name']:
        db.Army.update_one({'_id': user_id}, {'$set': winner[2]})
    else:
        db.Army.update_one({'_id': user_id}, {'$set': loser[2]})

    battle_summary = {
        'winner': winner[0].upper(),
        'loser': loser[0].upper(),
        'tribute': total_bonus_loot,
        'attacker_casualties': str(attacker_casualties),
        'pirate_casualties': str(defender_casualties),
    }
    return battle_summary

def research(user_id, research_topic):
    age = get_age(user_id)
    user_resources = get_user_resources(user_id)
    research_info = get_research_info_by_age(age)
    resource_rate = research_info[research_topic]['resource_rate']
    if user_resources['knowledge'] - research_info[research_topic]['costs'] < 0:
        return(False, 'You did not have enough knowledge loser')
    print(user_resources, resource_rate)
    update_resources(user_id, {'knowledge': user_resources['knowledge'] - research_info[research_topic]['costs']})
    new_rate = math.ceil(user_resources[resource_rate] * research_info[research_topic]['bonus'])
    update_resource_rate(user_id, {resource_rate: new_rate})
    db.Nations.update_one({'_id': user_id}, {'$push': {'researched_list': research_topic}})
    return(True, f'Successfully researched {research_topic}')


def formulate_army(): # combine defense buldings with army units and shuffle them 
    pass

def form_pvp_armies(attacker_id, defender_id):
    attacker_army = get_user_army(attacker_id)
    attacker_buildings = get_user_defense_buildings(attacker_id)
    attacker_stats = get_user_stats(attacker_id)
    defender_army = get_user_army(defender_id)
    defender_stats = get_user_stats(defender_id)
    defender_buildings = get_user_defense_buildings(defender_id)

    attacker_army_combined = {**attacker_army, **attacker_buildings}
    defender_army_combined = {**defender_army, **defender_buildings}

    return (attacker_stats, attacker_army_combined, defender_stats, defender_army_combined)

def form_attacker_army(attacker_id):
    pass

def form_alliance_army(alliance_id):
    pass

def award_tribute(winner_id, loser_id):
    loser_resources = list(db.Resources.find({'_id': loser_id}))[0]
    winner_resources = list(db.Resources.find({'_id': winner_id}))[0]
    res_list = ['food', 'timber', 'metal', 'wealth', 'oil', 'knowledge'] #there are other fields aside from resources
    total_bonus_loot = {} #used for summary
    for resource in loser_resources:
        if resource in res_list:
            amount_taken = math.ceil(loser_resources[resource] * steal_percentage) #steal 10%
            winner_resources[resource] = winner_resources[resource] + (amount_taken * bonus_loot_multiplier)
            loser_resources[resource] = loser_resources[resource] - amount_taken
            total_bonus_loot[resource] = (amount_taken)
    db.Resources.update_one({'_id': winner_id}, {'$set': winner_resources})
    db.Resources.update_one({'_id': loser_id}, {'$set': loser_resources})
    return winner_resources

def generate_battle_summary(winner_name: str, loser_name: str, winner_username=None, loser_username=None, motto=None, 
                            winner_battle_rating=None, loser_battle_rating=None, tribute,
                            attacker_casualties: dict, defender_casualties: dict):
    return {
        'winner': winner_name.upper(), # player, pirate, boss, alliance
        'loser': loser_name.upper(), # player, pirate, boss, alliance
        'winner_username': winner_username, #x
        'loser_username': loser_username, #x
        'winner_motto': motto, #x
        'winner_battle_rating': str(winner_battle_rating + battle_rating_increase), #x
        'loser_battle_rating': str(loser_battle_rating - battle_rating_increase), #x
        'tribute': tribute,
        'attacker_casualties': attacker_casualties,
        'defender_casualties': defender_casualties,
    }

# def generate_battle_summary(*args, **kwargs):

#     summary = {}

#attacker_army can be pvp, player attacking pirate
#defender_army can be pvp, pirate army, boss army 
def attack_sequence(attacker_stats, attacker_army, defender_stats, defender_army):
    #look into shuffling or ways for counters
    all_unit_info = remove_era_information(get_all_units_info())
    attacker_army_key_list = list(attacker_army.keys())
    defender_army_key_list = list(defender_army.keys())
    attacker_casualties = {}
    defender_casualties = {}

    i = j = 0
    while i < len(attacker_army_key_list) and j < len(defender_army_key_list):
        attacker_unit_count = attacker_army[attacker_army_key_list[i]]
        defender_unit_count = defender_army[defender_army_key_list[j]]
        # print('DEBUG', 'ATTACKER_UNIT_COUNT:', attacker_unit_count, 'DEFENDER_UNIT_COUNT', defender_unit_count)
        if attacker_unit_count == 0:
            i += 1
        elif defender_unit_count == 0:
            j += 1
        else:
            attacker_unit = attacker_army_key_list[i]
            defender_unit = defender_army_key_list[j]
            attacker_roll = random.randint(all_unit_info[attacker_unit]['rolls']['lowerbound'], all_unit_info[attacker_unit]['rolls']['upperbound'])
            defender_roll = random.randint(all_unit_info[defender_unit]['rolls']['lowerbound'], all_unit_info[defender_unit]['rolls']['upperbound'])

            # roll processing
            attacker_roll, defender_roll = roll_modifier(attacker_stats, attacker_roll, all_unit_info[attacker_unit]['type'], 
                                                         defender_stats, defender_roll, all_unit_info[defender_unit]['type'])

            #update casualties
            if attacker_roll > defender_roll:
                if defender_army_key_list[j] in defender_casualties:
                    defender_casualties[defender_army_key_list[j]] += 1
                else: 
                    defender_casualties[defender_army_key_list[j]] = 1
                defender_army[defender_army_key_list[j]] -= 1
            elif attacker_roll < defender_roll:
                if attacker_army_key_list[i] in attacker_casualties:
                    attacker_casualties[attacker_army_key_list[i]] += 1
                else: 
                    attacker_casualties[attacker_army_key_list[i]] = 1
                attacker_army[attacker_army_key_list[i]] -= 1

    if j > i:
        winner = 'attacker'
    if i < j:
        winner = 'defender'

    return (attacker_army, attacker_casualties, defender_army, defender_casualties, winner)

def roll_modifier(attacker_stats, attacker_roll, attacker_type, defender_stats, defender_roll, defender_type):
    wonder_info = get_list_of_wonder_info()
    unit_counters = get_unit_counters
    attacker_buff_wonders, attacker_nerf_wonders = get_combat_wonders(attacker_stats['owned_wonders'])
    defender_buff_wonders, defender_nerf_wonders = get_combat_wonders(defender_stats['owned_wonders'])
    for wonder in attacker_buff_wonders + defender_nerf_wonders:
        attacker_roll *= wonder_info[wonder]['bonus']
    for wonder in defender_buff_wonders + attacker_nerf_wonders:
        defender_roll *= wonder_info[wonder]['bonus']
    if defender_type in unit_counters[attacker_type]:
        attacker_roll *= 1.2
    if attacker_type in unit_counters[defender_type]:
        defender_type *= 1.2
    return(attacker_roll, defender_roll) 

def extract_wonder_names(data):
    wonders_list = []

    for era, wonders in data.items():
        for wonder in wonders:
            wonders_list.append(wonder)

    return wonders_list


def extract_hero_names(data):
    heroes_list = []

    for era, era_data in data.items():
        for hero_type, heroes in era_data.items():
            for hero_name in heroes.keys():
                heroes_list.append(hero_name)

    return heroes_list

def get_exploration_options(user_id, user_army):
    user_age = get_age(user_id)
    event_options = []
    for i in range(0,3):
        event_chance = round(random.uniform(0, 1), 2) #generate random float between 0 and 1 (inclusive) with decimals to 2 places
        for (lowerbound, upperbound), event in get_exploration_events_chances().items():
            if lowerbound <= event_chance < upperbound:
                # print(event_chance, lowerbound, upperbound)
                if 'free_resources' in event:
                    res_amt = random.randint(event['free_resources'][user_age]['lowerbound'], event['free_resources'][user_age]['upperbound'])
                    event_data = {
                        'type': 'free_resources',
                        'label': f'Befriend A Nation',
                        'data': res_amt,
                    }
                elif 'free_units' in event:
                    unit = random.choice(event['free_units'][user_age])
                    print(unit)
                    event_data = {
                        'type': 'free_units',
                        'label': 'Hire Merceneries',
                        'data': {
                            'unit': unit,
                            'num_units': random.randint(3,15),
                        }, 
                    }
                elif 'trade_route' in event:
                    event_data = {
                        'type': 'trade_route',
                        'label': 'Discover A Trade Route',
                        'data': event['trade_route'][user_age],
                    }
                elif 'hero_unit' in event:
                    users_available_heroes = get_list_of_hero_units_by_era(user_age)
                    users_heroes = [] 
                    for unit in user_army.keys():
                        if unit in users_available_heroes and user_army[unit] == 1:
                            users_heroes.append(unit)

                    users_available_heroes_set = set(users_available_heroes)
                    users_heroes_set = set(users_heroes)
                    remaining_heroes =  users_available_heroes_set - users_heroes_set
                    remaining_heroes = list(remaining_heroes)

                    hero = random.choice(remaining_heroes)
                    event_data = {
                        'type': 'free_hero',
                        'label': 'Recruit A Hero',
                        'data': hero,
                    }
                elif 'wonder' in event:
                    users_wonders = db.Nations.find_one({'_id': user_id}, {'owned_wonders': 1})['owned_wonders']
                    users_available_wonders = extract_wonder_names(event['wonder'][user_age])
                    users_wonders_set = set(users_wonders)
                    user_available_wonders_set = set(users_available_wonders)
                    remaining_wonders = user_available_wonders_set - users_wonders_set
                    remaining_wonders = list(remaining_wonders)
                    if remaining_wonders == []:
                        print('No more avaiable wonders in your era')
                        i -= 1
                        continue
                    wonder = random.choice(remaining_wonders)
                    event_data = {
                        'type': 'wonder',
                        'label': 'Discover A Wonder',
                        'data': wonder,
                    }
                elif 'pirates' in event:
                    users_units = get_list_of_hero_units_by_era(user_age)
                    # users_units.remove('heroes')
                    non_combat_units = ['keep', 'castle', 'fortress', 'bunker', 'planetary_fortress']
                    for unit in non_combat_units:
                        if unit in users_units:
                            users_units.remove(unit)

                    pirate_army = {}
                    for i, unit in enumerate(users_units):
                        weight_factor = i+1
                        pirate_army[unit] = random.randint(1,20) // weight_factor #scale the number of units down as you get to the stronger units in an age
                    event_data = {
                        'type': 'pirates',
                        'label': 'Pirates',
                        'data': pirate_army,
                    }
                else:
                    event_data = {
                        'type': 'error',
                        'label': 'error',
                        'data': 'error',
                    } 
                event_options.append(event_data)
    return event_options 
        
def validate_execute_shop(userID, unit, num_units):
    data = list(db.Resources.find({'_id': userID}, {'_id': 0}))[0]
    unit_costs = get_unit_costs()
    #Calculates the the total cost for the unit you are buying
    for resource in unit_costs[unit]:
        unit_costs[unit][resource] *= int(num_units)
    total_cost = unit_costs[unit]
    new_resource_balance = {}
    #Checks to see if you have enough resources
    for resource in total_cost:
        new_resource_balance[resource] = data[resource] - total_cost[resource]
        if data[resource] - total_cost[resource] < 0:
            return [False]
    return [True, new_resource_balance]

def execute_explore(user_id, selected_exploration_option):
    if selected_exploration_option['type'] == 'free_resources':
        print('Giving Free Resources')
        data = get_user_stats(user_id)
        for resource in ['food', 'timber', 'metal', 'wealth', 'oil', 'knowledge']:
            new_total_res = data['resources'][resource] + selected_exploration_option['data']
            db.Resources.update_one({'_id': user_id}, {'$set': {resource: new_total_res}})
        return nextcord.Embed(
            title='Exploration Result',
            description='You befriended a nearby nation and received gifts!',
            color=0x00ff00,
        ).add_field(
            name='Gifts Received',
            value=f'{selected_exploration_option["data"]} (of every resource)',
        )

    if selected_exploration_option['type'] == 'free_units':
        print('Giving Free Units')
        user_army = get_user_army(user_id)
        pprint.pprint(user_army)
        print(selected_exploration_option)
        num_units_inc = user_army[selected_exploration_option['data']['unit']] + selected_exploration_option['data']['num_units']
        db.Army.update_one({'_id': user_id}, {'$set': {selected_exploration_option['data']['unit']: num_units_inc}})
        return nextcord.Embed(
            title='Exploration Result',
            description='You recruited some mercenaries!',
            color=0x00ff00,
        ).add_field(
            name='Recruited',
            value=f'{selected_exploration_option["data"]["num_units"]} {selected_exploration_option["data"]["unit"]}s',
        )

    if selected_exploration_option['type'] == 'trade_route':
        print('Giving Free Trade Route')
        country = random.choice(countries)
        data = get_user_stats(user_id)
        for resource_rate in ['food_rate', 'timber_rate', 'metal_rate', 'wealth_rate', 'oil_rate', 'knowledge_rate']:
            new_total_res_rate = data['resources'][resource_rate] + selected_exploration_option['data']
            db.Resources.update_one({'_id': user_id}, {'$set': {resource_rate: new_total_res_rate}})
        return nextcord.Embed(
            title='Exploration Result',
            description=f'Your units discovered a trade route with {country}',
            color=0x00ff00,
        ).add_field(
            name='Resource Rate Increased',
            value=f'By {selected_exploration_option["data"]}',
        )

    if selected_exploration_option['type'] == 'free_hero':
        print('Giving Free Hero')
        db.Army.update_one({'_id': user_id}, {'$set': {selected_exploration_option['data']: 1}})
        return nextcord.Embed(
            title='Exploration Result',
            description=f'{selected_exploration_option["data"]} has joined your ranks!',
            color=0x00ff00,
        )

    if selected_exploration_option['type'] == 'wonder':
        db.Nations.update_one({'_id': user_id}, {'$push': {'owned_wonders': selected_exploration_option['data']}})
        return nextcord.Embed(
            title='Exploration Result',
            description=f'Your units discovered a wonder: {selected_exploration_option["data"].replace("_", " ").capitalize()}',
            color=0x00ff00,
        )

    if selected_exploration_option['type'] == 'pirates':
        user_army = get_user_army(user_id)
        data = pirate_attack_sequence(user_id, selected_exploration_option['data'])
        embed = nextcord.Embed(
            title='BATTLE SUMMARY (TESTING)',
            description=f'{data["winner"]} DEFEATED {data["loser"]}',
            color=0xff0000,
        )

        embed.add_field(name='Winner', value=f'{data["winner"]}')
        embed.add_field(name='Loser', value=f'{data["loser"]}')
        embed.add_field(name='Plundered', value=f'{data["tribute"]}')
        embed.add_field(name='Attacker Casualties', value=f'{data["attacker_casualties"]}')
        embed.add_field(name='Pirate Casualties', value=f'{data["pirate_casualties"]}')

        return embed

def buy_building(user_id, building, num_build):
    num_build = int(num_build)
    age = get_age(user_id)
    user_army = get_user_army(user_id)
    rate_increase = age_resource_rate_increases[age]
    res_data = list(db.Resources.find({'_id': user_id}, {'_id': 0}))[0]
    nation_data = list(db.Nations.find({'_id': user_id}, {'_id': 0}))[0]
    building_costs = get_buildings_costs_by_age(age)
    print(building_costs)
    for resource in building_costs[building]['costs']:
        print(resource)
        if res_data[resource] - (building_costs[building]['costs'][resource] * num_build) >= 0:
            res_data[resource] -= (building_costs[building]['costs'][resource] * num_build)
        else:
            return False
        
    update_resources(user_id, res_data)
    nation_data[building] += num_build
    if building == 'granary': 
        res_data['food_rate'] += rate_increase * num_build
    elif building == 'lumbermill' or building == 'lumber mill': 
        res_data['timber_rate'] += rate_increase * num_build
    elif building == 'quarry': 
        res_data['metal_rate'] += rate_increase * num_build
    elif building == 'oilrig' or building == 'oil rig': 
        res_data['oil_rate'] += rate_increase * num_build
    elif building == 'market': 
        res_data['wealth_rate'] += rate_increase * num_build
    elif building == 'university': 
        res_data['knowledge_rate'] += rate_increase * num_build
    elif building in get_list_of_defense_buildings():
        user_army[building] += num_build
    update_building(user_id, building, nation_data)
    update_resource_rate(user_id, res_data)
    return True

def upgrade_age(user_id):
    user_data = get_user_stats(user_id)
    # pprint.pprint(user_data)    
    if user_data['age'] == 'ancient':
        next_age = 'medieval'
    if user_data['age'] == 'medieval':
        next_age = 'enlightenment'
    elif user_data['age'] == 'enlightenment':
        next_age = 'modern'
    elif user_data['age'] == 'modern':
        next_age = 'space'
    elif user_data['age'] == 'space':
        next_age = ''
    if next_age == '':
        return [False, next_age]
    ageCosts = get_age_costs()
    if user_data['resources']['knowledge'] - ageCosts[next_age] > 0:
        knowledge_cost = {'knowledge': user_data['resources']['knowledge'] - ageCosts[next_age]}
        update_resources(user_id, knowledge_cost)
        update_nation(user_id, {'age': next_age})        
        return [True, next_age]
    return [False, next_age]

"""HELPER FUNCTIONS"""
def format_unit_info(unit, data):
    costs_data = data.get('costs', {})
    costs_str = ', '.join([f'{resource.capitalize()}: {cost}' for resource, cost in costs_data.items()])
    
    rolls_data = data.get('rolls', {})
    rolls_str = f'Rolls: {rolls_data.get("lowerbound", 0)}-{rolls_data.get("upperbound", 0)}'
    
    combat_type_str = f'Combat Type: {data.get("combat_type", "N/A").capitalize()}'
    
    unit_type_str = f'Type: {data.get("type", "N/A").capitalize()}' if data.get("type") else ''
    
    hero_str = 'Hero' if data.get('hero', False) else 'Normal'
    
    return f'{unit.capitalize()} - {combat_type_str} | {unit_type_str} | {costs_str} | {rolls_str} | {hero_str}'

def display_units_in_era(era):
    units_info = get_all_units_info()
    formatted_output = f'===== Units Information ({era.capitalize()} Era) =====\n'
    if era.lower() in units_info:
        for unit, data in units_info[era.lower()].items():
            formatted_output += format_unit_info(unit, data) + '\n'
    else:
        formatted_output += f'No units available for the {era.capitalize()} Era.\n'

    return formatted_output

# def display_normal_units(age):
#     units_info = get_all_units_info()

#     if age not in units_info:
#         return "Invalid age. Please choose a valid age: ancient, medieval, enlightenment, modern, space."

#     normal_units = {unit_name: unit_info for unit_name, unit_info in units_info[age].items() if not unit_info['hero']}

#     if not normal_units:
#         return f"No normal units found for the {age} age."

#     embed = nextcord.Embed(title=f"Normal Units Information - {age.capitalize()}", color=0x0000ff)

#     for unit_name, unit_info in normal_units.items():
#         cost_str = ', '.join([f"{resource.capitalize()}: {cost}" for resource, cost in unit_info['costs'].items()])
#         rolls_str = f"Rolls: {unit_info['rolls']['lowerbound']} - {unit_info['rolls']['upperbound']}"
#         combat_type_str = f"Combat Type: {unit_info['combat_type'].capitalize()}"
#         unit_type_str = f"Type: {unit_info['type'].capitalize()}" if unit_info['type'] else ""

#         unit_description = f"{cost_str}\n{rolls_str}\n{combat_type_str}\n{unit_type_str}"
#         embed.add_field(name=f"{unit_name.capitalize()} ({'Hero' if unit_info['hero'] else 'Normal'})", value=unit_description, inline=False)

#     return embed

def format_string(input_string):
    words = input_string.split('_')
    formatted_words = [word.capitalize() for word in words]
    formatted_string = ' '.join(formatted_words)
    return formatted_string

def calculate_max(thing_to_buy, type, user_stats): # fix later
    age = user_stats['age']
    if type == 'unit':
        unit_costs = get_unit_costs()
        pprint.pprint(unit_costs)
        num_units = sys.maxsize
        for res in unit_costs[thing_to_buy]:
            num_units = min(num_units, math.floor(user_stats['resources'][res] / unit_costs[thing_to_buy][res]))
        # print('calcualted max:', num_units)
        return num_units

    elif type == 'building':
        building_costs = get_buildings_costs_by_age(age)
        print(building_costs)
        num_buildings = sys.maxsize
        for resource in building_costs[thing_to_buy]['costs']:
            print(resource)
            num_buildings = min(num_buildings, math.floor(user_stats['resources'][resource] / building_costs[thing_to_buy]['costs'][resource]))
        return num_buildings


def remove_era_information(input_dict):
    result_dict = {}
    for era, units in input_dict.items():
        result_dict.update(units)
    return result_dict


