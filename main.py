from dotenv import load_dotenv
import nextcord
from nextcord.ext import commands
import os
import utils
import pymongo
import objects.nation, objects.resources, objects.army
import math
import time
import random
import pprint
import json
import string


load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
TOKEN = os.environ.get('DISCORDTOKEN')

mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot
intents = nextcord.Intents.default() #added this idk wtf this is
intents.message_content = True #added this idk wtf this is
client = commands.Bot(command_prefix = 'c!', intents=intents)#intents needed to get message from listener
client.remove_command('help') #allows me to override the default and write my own
prefix = client.command_prefix

"""SETTINGS"""
resource_claim_cap = 24

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    print('Currently in ' + str(len(client.guilds)) + ' servers!');
    print('We have ' + str(utils.get_num_users()) + ' active players!');

@client.command(name='help', aliases=['Help', 'HELP'])
async def help(ctx):
    prefix = 'c!'
    await ctx.send(
        '```========RULES========\n'
        'Create your own nation and attack other players.\n' 
        'Manage resources (Food, Timber, Metal, Oil, Wealth, Knowledge) and an army to grow stronger.\n'
        'Buildings mine respective resource at a certain rate per hour.\n' 
        'Build/Upgrade buildings to increase resource rate.\n' 
        'Buy units and attack other players for resources and battle rating.\n' 
        'You only get one nation for all servers and you cannot change your nation after creation!\n' 
        '========Commands========\n' +
        prefix + 'createnation "name" - Create a nation\n' +
        prefix + 'stats - Info on your nation\n' +
        prefix + 'leaderboard - View the rankings of everyone who plays\n' + 
        prefix + 'claim - Collect resources (every hour)\n' +
        prefix + 'ages - Info on ages\n' +
        prefix + 'nextage - Go to the next age!\n' +
        prefix + 'shop - Info on units you can purchase\n' + 
        prefix + 'shop [units] [number] - Buys n number of units\n' + 
        prefix + 'build - Info on buildings you can build\n' + 
        prefix + 'build [building] [number]- Build this building\n' +
        prefix + 'attack - Show a list of players you can attack\n' + 
        prefix + 'attack [@player] - Attack a player (wins +25, losses -25)\n' + 
        prefix + 'help - List of commands and rules\n```'
    )

@client.command(name='createnation', aliases=['CREATENATION', 'CreateNation', 'Createnation'])
async def createnation(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_createnation(user_id, arg)
    if error == True:
        await ctx.send(response)
    else:
        user_nation = objects.nation.CreateNation(user_id, server_id, username, arg, time.time())
        user_resources = objects.resources.CreateResources(user_id, username, arg, time.time())
        user_army = objects.army.CreateArmy(user_id, username, arg)
        db.Nations.insert_one(user_nation.__dict__)
        db.Resources.insert_one(user_resources.__dict__)
        db.Army.insert_one(user_army.__dict__)
        await ctx.send('Nation Created! Type ' + prefix + 'stats to show info about your nation!')

@client.command(name='stats', aliases=['Stats', 'STATS', 'stat', 'Stat', 'STAT'])
async def stats(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_stats(ctx, user_id, arg)
    if error == True:
        await ctx.send(response)
    else:
        #get army data
        data = utils.get_user_stats(response)
        armyData = utils.get_user_army(response)
        armyStr = ''
        for unit in armyData:
            if unit != '_id' and unit != '_id' and unit != 'username' and unit != 'name' and armyData[unit] != 0:
                armyStr += unit + ': ' + str(armyData[unit]) + '\n'
        await ctx.send(
            '```=======' + str(data['name']) + '=======\n'
            'Leader: ' + str(data['username']) + '\n' 
            'Age: ' + str(data['age']) + '\n'
            'Ability: ' + str(data['ability']) + '\n'
            'Battle Rating: ' + str(data['battle_rating']) + '\n'
            'Shield (When this person can be attacked): ' + str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['shield']))) + '\n'
            '======Resources======\n'
            'Food: ' + str(data['resources']['food']) + '\n'
            'Timber: ' + str(data['resources']['timber']) + '\n'
            'Metal: ' + str(data['resources']['metal']) + '\n'
            'Oil: ' + str(data['resources']['oil']) + '\n'
            'Wealth: ' + str(data['resources']['wealth']) + '\n'
            'Knowledge: ' + str(data['resources']['knowledge']) + '\n'
            '======Army====== \n'
            + armyStr +
            '======Buildings====== \n'
            'Granaries: ' + str(data['granary']) + '\n'
            'Lumbermills: ' + str(data['lumbermill']) + '\n'
            'Quarries: ' + str(data['quarry']) + '\n'
            'Oil Rigs: ' + str(data['oilrig']) + '\n'
            'Markets: ' + str(data['market']) + '\n'
            'Universities: ' + str(data['university']) + '\n```'
        )
    
@client.command(name='leaderboard', aliases=['lb', 'Lb', 'LB', 'LEADERBOARD', 'Leaderboard', 'LeaderBoard'])
async def leaderboard(ctx, arg=None):
    user_rank, num_players = utils.get_user_rank(ctx.message.author.id)
    nations = utils.get_rankings()
    ranking_string = ''
    rank = 1
    for nation in nations:
        rank = str(rank)
        ranking_string = ranking_string + '======\nRank #' + rank +'\nOwner: ' + nation['username'] + '\nNation: ' + nation['name'] + '\nBattle Rating: ' + str(nation['battle_rating']) + '\n======'
        rank = int(rank)
        rank +=1
    await ctx.send('```' + 'Your Rank: ' + str(user_rank) + '/' + str(num_players) + '\n' + ranking_string + '```')


@client.command(name='claim', aliases=['c', 'Claim', 'CLAIM', 'collect', 'Collect', 'COLLECT'])
async def claim(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_claim(user_id)
    if error:
        await ctx.send(response)
        return

    current_time = time.time()
    data = utils.get_user_stats(user_id)
    time_passed_hours = (current_time - data['resources']['last_claim']) / 3600
    if time_passed_hours >= resource_claim_cap: #cap the resource collection to 1 day
            time_passed_hours = resource_claim_cap
    if time_passed_hours >= 1 : #as long as 1 hour has passed, we can collect
        updated_resources = {
            'last_claim': current_time,
            'food': math.ceil(data['resources']['food_rate'] * time_passed_hours + data['resources']['food']),
            'timber': math.ceil(data['resources']['timber_rate'] * time_passed_hours + data['resources']['timber']),
            'metal': math.ceil(data['resources']['metal_rate'] * time_passed_hours + data['resources']['metal']),
            'wealth': math.ceil(data['resources']['wealth_rate'] * time_passed_hours + data['resources']['wealth']),
            'oil': math.ceil(data['resources']['oil_rate'] * time_passed_hours + data['resources']['oil']),
            'knowledge': math.ceil(data['resources']['knowledge_rate'] * time_passed_hours + data['resources']['knowledge']),
        }

        db.Resources.update_one({'_id': user_id}, {'$set': updated_resources})
        resource_message = (
            f'```Resources Claimed:\n'
            f'Food: {updated_resources["food"] - data["resources"]["food"]}\n'
            f'Timber: {updated_resources["timber"] - data["resources"]["timber"]}\n'
            f'Metal: {updated_resources["metal"] - data["resources"]["metal"]}\n'
            f'Wealth: {updated_resources["wealth"] - data["resources"]["wealth"]}\n'
            f'Oil: {updated_resources["oil"] - data["resources"]["oil"]}\n'
            f'Knowledge: {updated_resources["knowledge"] - data["resources"]["knowledge"]}\n```'
        )
        await ctx.send(resource_message)
    else:
        next_claim = data['resources']['last_claim'] + 3600
        await ctx.send(f'```You have already claimed within the hour. Please wait another hour.\nNext Claim at: {time.strftime("%H:%M:%S", time.localtime(next_claim))}```')
        
@client.command(name='shop', aliases=['Shop', 'SHOP'])
async def shop(ctx, arg1=None, arg2=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_shop(user_id, arg1.lower())
    if error == True:
        await ctx.send(response)
    elif arg1 == None:
        age = utils.get_age(user_id)
        await ctx.send('```' + utils.display_units_in_era(age) + '```')
    else:
        age = utils.get_age(user_id)
        users_units = utils.get_users_available_units(age)
        
        unit = arg1
        num_units = arg2

        resourceCost = utils.validate_execute_shop(user_id, unit, num_units)
        if str(unit) not in users_units:
            await ctx.send('```This unit does not exist in the game or you do not have access to this unit.```')
        else:
            if not resourceCost[0]:
                await ctx.send('```You must construct additional pylons (not enough resources)```')
            utils.update_resources(user_id, resourceCost[1])
            utils.update_units(user_id, unit, num_units)
            await ctx.send('```Successfully bought ' + num_units + ' ' + unit + 's```')


@client.command(name='build', aliases=['Build', 'BUILD'])
async def build(ctx, arg1=None, arg2=None):
    userID, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_build(userID, arg1.lower(), arg2)
    if error:
        await ctx.send(response)
    elif arg1 is None and arg2 is None:
        building_costs = utils.get_buildings_costs()
        formatted_output = '```=====Buildings=====\n'
        for building, cost in building_costs.items():
            formatted_output += f'{building.capitalize()} - cost: {", ".join([f"{value} {resource}" for resource, value in cost.items()])}\n'
        formatted_output += '```'
        await ctx.channel.send(formatted_output)
    else:
        building = arg1
        num_build = int(arg2) if arg2 else 1
        if utils.buy_building(userID, building.lower(), num_build):
            await ctx.send(f'Successfully built {num_build} {building}(s)')
        else:
            await ctx.send('Bruh Moment... (not enough resources)')

@client.command(name='ages', aliases=['Ages', 'AGES', 'age', 'Age', 'AGE'])
async def ages(ctx):
    ageCosts = utils.get_age_costs()
    await ctx.send(
        '```Ages (Costs in Knowledge):\n ' + str(ageCosts) + '```'
    )

@client.command(name='nextage', aliases=['na', 'NA', 'NEXTAGE', 'Nextage', 'NextAge'])
async def next_age(ctx):
    user_id, server_id, username = utils.get_message_info(ctx)
    result = utils.upgrade_age(user_id)
    if result[0]:
        await ctx.send('```Successfully advanced to the ' + result[1] + ' age!```')
    else:
        await ctx.send('```You got no M\'s in ur bank account (not enough resources) or you\'re at most advanced age.```')

@client.command(name='attack', aliases=['ATTACK', 'Attack'])
async def attack(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_attack(ctx, user_id, arg)
    if error:
        await ctx.send(response)
    elif not arg:
        players = utils.get_victims(user_id)
        await ctx.channel.send(f'```Here Is A List of Players You Can Attack:\n{players}```')
    else:
        data = utils.attackSequence(user_id, response)
        battle_summary = (
            f'```=====BATTLE SUMMARY===== (TESTING)\n'
            f'{data["winner"]} DEFEATED {data["loser"]}\n'
            f'Winner: {data["winner_username"]} Loser: {data["loser_username"]}\n'
            f'{data["winner"]} left a message: {data["winner_motto"]}\n'
            f'{data["winner"]} Battle Rating: {data["winner_battle_rating"]} (+25)\n'
            f'{data["winner"]} Plundered {data["tribute"]}\n'
            f'{data["loser"]} Battle Rating: {data["loser_battle_rating"]} (-25)\n'
            f'Attacker Casualties: {data["attacker_casualties"]}\n'
            f'Defender Casualties: {data["defender_casualties"]}```'
        )

        attacker = await client.fetch_user(user_id)
        defender = await client.fetch_user(response)

        for user, role in [(attacker, 'ATTACKED'), (defender, 'DEFENDED AGAINST')]:
            await user.send(
                f'YOU {role} SOMEONE! (TESTING)\n'
                f'{battle_summary}'
            )
        await ctx.send(battle_summary)

@client.command(name='motto', aliases=['Motto', 'MOTTO'])
async def set_motto(ctx, *, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    user_stats = utils.get_user_stats(user_id)

    if arg:
        user_stats['motto'] = arg
        utils.update_nation(user_id, user_stats)
        await ctx.send(f"Your motto has been set to: `{arg}`")
    else:
        await ctx.send("Please provide a motto. Example: `c!motto Your motto goes here`")

#shows whats new this patch
@client.command(name='patch', aliases=['Patch', 'PATCH'])
async def display_patch(ctx, arg=None):
    await ctx.send('Feature coming soon...')

@client.command(name='explore', aliases=['Explore', 'EXPLORE'])
async def display_patch(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_explore(ctx, user_id, arg)
    if error == True:
        await ctx.send(response)
    else:
        user_army = utils.get_user_army(user_id)
        message = utils.explore(user_id, user_army)
        await ctx.send(message)

# @client.command(name='event', aliases=['Event', 'EVENT'])
# async def event(ctx, arg=None):
#     pass

client.run(TOKEN)
