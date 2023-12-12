from dotenv import load_dotenv
import nextcord
from nextcord.ext import commands
import os
import utils
import pymongo
import objects.nation, objects.resources, objects.army
import math
import time
import datetime
import pprint
import random
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

@client.command(name='help', aliases=['Help', 'HELP'], description='See list of commands')
async def help(ctx):
    embed = nextcord.Embed(title="c!help", description='help command for if you are acoustic')
    for command in client.walk_commands():
        description = command.description
        if not description or description is None or description ==  '':
            description = 'No Description Provided'
        embed.add_field(name=f'`d!{command.name}{command.signature if command.signature is not None else ""}`', value=description)
    await ctx.send(embed=embed)

@client.command(name='createnation', aliases=['CREATENATION', 'CreateNation', 'Createnation'], description='Create your nation, MUST BE ALL ONE WORD!')
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

@client.command(name='stats', aliases=['Stats', 'STATS', 'stat', 'Stat', 'STAT'], description='View statistics on your nation')
async def stats(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_stats(ctx, user_id, arg)

    if error:
        await ctx.send(response)
    else:
        data = utils.get_user_stats(response)
        army_data = utils.get_user_army(response)

        # Calculate remaining shield time
        now = datetime.datetime.utcnow()
        remaining_shield_time = max(0, (data['shield'] - now.timestamp()))

        # Create the embed
        embed = nextcord.Embed(title=f"======= {data['name']} =======", color=0x00ff00)
        embed.add_field(name="Leader", value=data['username'], inline=True)
        embed.add_field(name="Age", value=data['age'], inline=True)
        embed.add_field(name="Motto", value=data['motto'], inline=True)
        embed.add_field(name="Wonder", value=data['wonder'], inline=True)
        embed.add_field(name="Alliance", value='coming soon...', inline=True)
        embed.add_field(name="Battle Rating", value=data['battle_rating'], inline=True)
        embed.add_field(name="Remaining Shield Time",
                        value=str(datetime.timedelta(seconds=remaining_shield_time)), inline=True)

        # Resources
        embed.add_field(name="======= Resources =======",
                        value=f"Food: {data['resources']['food']}\n"
                              f"Timber: {data['resources']['timber']}\n"
                              f"Metal: {data['resources']['metal']}\n"
                              f"Oil: {data['resources']['oil']}\n"
                              f"Wealth: {data['resources']['wealth']}\n"
                              f"Knowledge: {data['resources']['knowledge']}", inline=False)

        # Army
        army_str = '\n'.join([f"{unit}: {army_data[unit]}" for unit in army_data if
                             unit not in ['_id', 'username', 'name'] and army_data[unit] != 0])
        embed.add_field(name="======= Army =======", value=army_str, inline=False)

        # Buildings
        embed.add_field(name="======= Buildings =======",
                        value=f"Granaries: {data['granary']}\n"
                              f"Lumbermills: {data['lumbermill']}\n"
                              f"Quarries: {data['quarry']}\n"
                              f"Oil Rigs: {data['oilrig']}\n"
                              f"Markets: {data['market']}\n"
                              f"Universities: {data['university']}", inline=False)

        await ctx.send(embed=embed)
    
@client.command(name='leaderboard', aliases=['lb', 'Lb', 'LB', 'LEADERBOARD', 'Leaderboard', 'LeaderBoard'], description='See top 10 players in battle rating')
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

@client.command(name='claim', aliases=['c', 'Claim', 'CLAIM', 'collect', 'Collect', 'COLLECT'], description='Collect resources every hour')
async def claim(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_claim(user_id)
    
    if error:
        await ctx.send(response)
        return

    current_time = time.time()
    data = utils.get_user_stats(user_id)
    time_passed_hours = (current_time - data['resources']['last_claim']) / 3600

    if time_passed_hours >= resource_claim_cap:  # cap the resource collection to 1 day
        time_passed_hours = resource_claim_cap
    
    food_bonus = timber_bonus = metal_bonus = wealth_bonus = oil_bonus = knowledge_bonus = 1
    if data['wonder'] == 'hanging_gardens':
        food_bonus = 1.25
    if data['wonder'] == 'the_black_forest':
        timber_bonus = 1.25
    if data['wonder'] == 'the_chongalayas':
        metal_bonus = 1.25
    if data['wonder'] == 'the_rivers_of_chonga':
        wealth_bonus = 1.25
    if data['wonder'] == 'the_oil_fields_of_chonga':
        oil_bonus = 1.25
    if data['wonder'] == 'palace_of_versailles':
        knowledge_bonus = 1.25

    if time_passed_hours >= 1:  # as long as 1 hour has passed, we can collect
        updated_resources = {
            'last_claim': current_time,
            'food': math.ceil(data['resources']['food_rate'] * time_passed_hours + data['resources']['food']) * food_bonus,
            'timber': math.ceil(data['resources']['timber_rate'] * time_passed_hours + data['resources']['timber']) * timber_bonus,
            'metal': math.ceil(data['resources']['metal_rate'] * time_passed_hours + data['resources']['metal']) * metal_bonus,
            'wealth': math.ceil(data['resources']['wealth_rate'] * time_passed_hours + data['resources']['wealth']) * wealth_bonus,
            'oil': math.ceil(data['resources']['oil_rate'] * time_passed_hours + data['resources']['oil']) * oil_bonus,
            'knowledge': math.ceil(data['resources']['knowledge_rate'] * time_passed_hours + data['resources']['knowledge']) * knowledge_bonus,
        }

        db.Resources.update_one({'_id': user_id}, {'$set': updated_resources})

        # Prepare the Discord embed for resources claimed
        embed = nextcord.Embed(
            title='Resources Claimed',
            description=(
                f'Food: {updated_resources["food"] - data["resources"]["food"]}\n'
                f'Timber: {updated_resources["timber"] - data["resources"]["timber"]}\n'
                f'Metal: {updated_resources["metal"] - data["resources"]["metal"]}\n'
                f'Wealth: {updated_resources["wealth"] - data["resources"]["wealth"]}\n'
                f'Oil: {updated_resources["oil"] - data["resources"]["oil"]}\n'
                f'Knowledge: {updated_resources["knowledge"] - data["resources"]["knowledge"]}\n'
            ),
            color=0x00ff00  # Set the color of the embed as needed
        )

        await ctx.send(embed=embed)
    else:
        # Calculate time remaining until the next claim
        time_remaining_seconds = 3600 - (current_time - data['resources']['last_claim']) % 3600

        # Convert time remaining to hours, minutes, and seconds
        remaining_hours, remaining_seconds = divmod(time_remaining_seconds, 3600)
        remaining_minutes, remaining_seconds = divmod(remaining_seconds, 60)

        # Prepare the Discord embed for the time remaining message
        embed = nextcord.Embed(
            title='Already Claimed Within the Hour',
            description=(
                f'You have already claimed within the hour. Please wait another hour.\n'
                f'Next Claim in: {remaining_hours} hours, {remaining_minutes} minutes, {remaining_seconds} seconds'
            ),
            color=0xff0000  # Set the color of the embed as needed
        )

        await ctx.send(embed=embed)
    
@client.command(name='shop', aliases=['Shop', 'SHOP'], description='See unit prices and purchase unit')
async def shop(ctx, arg1=None, arg2=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_shop(user_id, arg1)
    
    if error:
        embed = nextcord.Embed(description=response, color=0xff0000)
        await ctx.send(embed=embed)
    elif arg1 is None:
        age = utils.get_age(user_id)
        units_info = utils.display_units_in_era(age)
        embed = nextcord.Embed(title=f'Units Information ({age.capitalize()} Era)', description=f'```{units_info}```', color=0x00ff00)
        await ctx.send(embed=embed)
    else:
        age = utils.get_age(user_id)
        users_units = utils.get_users_available_units(age)
        unit = arg1
        num_units = arg2
        resource_cost = utils.validate_execute_shop(user_id, unit, num_units)
        if str(unit) not in users_units:
            embed = nextcord.Embed(description='This unit does not exist in the game or you do not have access to this unit.', color=0xff0000)
            await ctx.send(embed=embed)
        else:
            if not resource_cost[0]:
                embed = nextcord.Embed(description='You must construct additional pylons (not enough resources)', color=0xff0000)
                await ctx.send(embed=embed)
            utils.update_resources(user_id, resource_cost[1])
            utils.update_units(user_id, unit, num_units)
            embed = nextcord.Embed(description=f'```Successfully bought {num_units} {unit}s```', color=0x00ff00)
            await ctx.send(embed=embed)

@client.command(name='build', aliases=['Build', 'BUILD'], description='See building prices, and build buildings')
async def build(ctx, arg1=None, arg2=None):
    userID, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_build(userID, arg1, arg2)

    if error:
        await ctx.send(response)
    elif arg1 is None and arg2 is None:
        building_costs = utils.get_buildings_costs()
        
        embed = nextcord.Embed(title='Building Costs', color=0x00ff00)
        
        for building, cost in building_costs.items():
            cost_str = ', '.join([f'{value} {resource}' for resource, value in cost.items()])
            embed.add_field(name=building.capitalize(), value=f'Cost: {cost_str}', inline=False)

        await ctx.send(embed=embed)
    else:
        building = arg1
        num_build = int(arg2) if arg2 else 1

        if utils.buy_building(userID, building.lower(), num_build):
            await ctx.send(f'Successfully built {num_build} {building}(s)')
        else:
            await ctx.send('Bruh Moment... (not enough resources)')

@client.command(name='ages', aliases=['Ages', 'AGES', 'age', 'Age', 'AGE'], description='See cost of moving to the next age')
async def ages(ctx):
    age_costs = utils.get_age_costs()
    # Create the embed
    embed = nextcord.Embed(title="Ages (Costs in Knowledge)", color=0x00ff00)
    for age, cost in age_costs.items():
        embed.add_field(name=age.capitalize(), value=f"Cost: {cost} Knowledge", inline=False)
    await ctx.send(embed=embed)

@client.command(name='nextage', aliases=['na', 'NA', 'NEXTAGE', 'Nextage', 'NextAge'])
async def next_age(ctx):
    user_id, server_id, username = utils.get_message_info(ctx)
    result = utils.upgrade_age(user_id)
    if result[0]:
        await ctx.send('```Successfully advanced to the ' + result[1] + ' age!```')
    else:
        await ctx.send('```You got no M\'s in ur bank account (not enough resources) or you\'re at most advanced age.```')

@client.command(name='attack', aliases=['ATTACK', 'Attack'], description='See who you can attack, and attack other players')
async def attack(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_attack(ctx, user_id, arg)

    if error:
        await ctx.send(response)
    elif not arg:
        players = utils.get_victims(user_id)
        # Format the list of players into a string
        players_str = ', '.join(players)
        embed = nextcord.Embed(
            title='Players You Can Attack',
            description=f'Here is a list of players you can attack: {players_str}',
            color=0xff0000  # Set the color of the embed as needed
        )
        await ctx.channel.send(embed=embed)
    else:
        data = utils.attackSequence(user_id, response)

        embed = nextcord.Embed(
            title='BATTLE SUMMARY (TESTING)',
            description=f'{data["winner"]} DEFEATED {data["loser"]}',
            color=0xff0000  # You can set the color of the embed here
        )

        embed.add_field(name='Winner', value=f'{data["winner_username"]}')
        embed.add_field(name='Loser', value=f'{data["loser_username"]}')
        embed.add_field(name='Winner Left You A Message', value=f'{data["winner_motto"]}', inline=False)
        embed.add_field(name='Winner Battle Rating', value=f'{data["winner_battle_rating"]} (+25)')
        embed.add_field(name='Loser Battle Rating', value=f'{data["loser_battle_rating"]} (-25)')
        embed.add_field(name='Plundered', value=f'{data["tribute"]}')
        embed.add_field(name='Attacker Casualties', value=f'{data["attacker_casualties"]}')
        embed.add_field(name='Defender Casualties', value=f'{data["defender_casualties"]}')

        await ctx.send(embed=embed)

        attacker = await client.fetch_user(user_id)
        defender = await client.fetch_user(response)

        for user, role in [(attacker, 'ATTACKED'), (defender, 'DEFENDED AGAINST')]:
            await user.send(embed=embed)

@client.command(name='motto', aliases=['Motto', 'MOTTO'], description='Set your motto to leave a msg for enemies')
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
@client.command(name='patch', aliases=['Patch', 'PATCH'], description='See list of patch notes')
async def display_patch(ctx, arg=None):
    await ctx.send(
    '```New UI using embeds!\n'
    'New age before medieval is the ancient age!\n'
    'New units in all ages\n'
    'New defense units used for defending with higher rolls but cannot be used to attack\n'
    'New exploration units used to explore the world of chonga and trigger events\n'
    'Added wonders that now give special benefits\n'
    'Small quality of life updates like W/L ratio, username included in batte summary, less strict command names\n'
    'New commands: c!explore c!motto c!patch```'
    )

@client.command(name='explore', aliases=['Explore', 'EXPLORE'], description='Send out exploration units to trigger events')
async def display_patch(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_explore(ctx, user_id, arg)
    if error == True:
        await ctx.send(response)
    else:
        user_army = utils.get_user_army(user_id)
        message = utils.explore(user_id, user_army)
        await ctx.send(message)

@client.command(name='wonder', aliases=['Wonder', 'WONDER', 'wonders', 'Wonders', 'WONDERS'], description='See and activate wonders you own')
async def wonder(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    user_stats = utils.get_user_stats(user_id)

    if arg is None:
        embed = nextcord.Embed(title=f'{username}\'s Owned Wonders', description='\n'.join(user_stats['owned_wonders']), color=0x00ff00)
        await ctx.send(embed=embed)
    elif arg.lower() == 'list':
        wonders_list = utils.get_wonder_list()

        formatted_wonders = [utils.format_wonder_name(name) for name in wonders_list]

        embed = nextcord.Embed(title='Available Wonders', description='\n'.join(formatted_wonders), color=0x0000ff)
        await ctx.send(embed=embed)
    elif arg in utils.get_wonder_list():
        db.Nations.update_one({'_id': user_id}, {'$set': {'wonder': arg}})
        await ctx.send(f'```Activated wonder: {arg}```')
    else:
        await ctx.send('```You did not type a wonder you have.```')

# #i want to dm users for updates like maintenance
# @client.command(name='announce', aliases=['Announce', 'ANNOUNCE'])
# async def announce(ctx, arg=None):
#     await ctx.send('Command coming soon...')

# #trigger random events with storyline
# @client.command(name='event', aliases=['Event', 'EVENT'])
# async def event(ctx, arg=None):
#     await ctx.send('Command coming soon...')

# #
# @client.command(name='event', aliases=['Event', 'EVENT'])
# async def event(ctx, arg=None):
#     await ctx.send('Command coming soon...')

client.run(TOKEN)
