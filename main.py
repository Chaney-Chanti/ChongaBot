from dotenv import load_dotenv
import nextcord
from nextcord.ext import commands
import os
import utils
import pymongo
import objects.nation, objects.resources, objects.army
from views.exploration_view import ExplorationView
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

@client.before_invoke
async def preprocessing(ctx):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.general_checks(user_id)
    if error:
        print(response)
        raise commands.CommandError("Checks failed.")
    else:
        print(response)

@client.command(name='help', aliases=['Help', 'HELP'], description='See list of commands')
async def help(ctx):
    embed = nextcord.Embed(title=f"{prefix}help", description='help command for if you are acoustic')
    for command in client.walk_commands():
        description = command.description
        if not description or description is None or description ==  '':
            description = 'No Description Provided'
        embed.add_field(name=f'`{prefix}{command.name}{command.signature if command.signature is not None else ""}`', value=description)
    await ctx.send(embed=embed)

@client.command(name='createnation', aliases=['CREATENATION', 'CreateNation', 'Createnation'], description='Create your nation, MUST BE ALL ONE WORD!')
async def create_nation(ctx, arg=None):
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
        remaining_shield_time = max(0, (data['shield'] - time.time()))
        remaining_claim_time = max(0, 3600 - (time.time() - data['resources']['last_claim']) % 3600)
        remaining_exploration_time = max(0, 21600 - ((time.time() - data['last_explore'])))
        # Create the embed
        embed = nextcord.Embed(title=f"======= {data['name']} =======", color=0x00ff00)
        embed.add_field(name="Leader", value=data['username'], inline=True)
        embed.add_field(name="Age", value=data['age'], inline=True)
        embed.add_field(name="Motto", value=data['motto'], inline=True)
        wonder_string = ''
        for wonder in data['owned_wonders']:
            wonder_string += utils.format_string(wonder) + ', '
        embed.add_field(name="Wonders", value=wonder_string, inline=True)
        embed.add_field(name="Alliance", value=data['alliance'], inline=True)
        embed.add_field(name="Battle Rating", value=data['battle_rating'], inline=True)
        embed.add_field(name="Remaining Shield Time",
                        value=str(datetime.timedelta(seconds=remaining_shield_time)).split('.')[0], inline=True)
        embed.add_field(name="Claim Cooldown",
                        value=str(datetime.timedelta(seconds=remaining_claim_time)).split('.')[0], inline=True)
        embed.add_field(name="Exploration Cooldown",
                        value=str(datetime.timedelta(seconds=remaining_exploration_time)).split('.')[0], inline=True)
        
        research_string = ''
        for research_topic in data['researched_list']:
            research_string += utils.format_string(research_topic) + ', '
        embed.add_field(name="======= Researched ========", value=research_string)

        # Resources
        embed.add_field(name="======= Resources =======",
                        value=f"```Food: {data['resources']['food']}           {data['resources']['food_rate']}/hr```"
                              f"```Timber: {data['resources']['timber']}         {data['resources']['timber_rate']}/hr```"
                              f"```Metal: {data['resources']['metal']}          {data['resources']['metal_rate']}/hr```"
                              f"```Oil: {data['resources']['oil']}            {data['resources']['oil_rate']}/hr```"
                              f"```Wealth: {data['resources']['wealth']}         {data['resources']['wealth_rate']}/hr```"
                              f"```Knowledge: {data['resources']['knowledge']}      {data['resources']['knowledge_rate']}/hr```", inline=False)

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
                              f"Universities: {data['university']}\n" 
                              f"Keeps: {data['keep']} | "
                              f"Castles: {data['castle']} | " 
                              f"Fortresses: {data['fortress']} | " 
                              f"Army Bases: {data['army_base']} | " 
                              f"Planetary Fortress: {data['planetary_fortress']}", inline=False)

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
    
    # food_bonus = timber_bonus = metal_bonus = wealth_bonus = oil_bonus = knowledge_bonus = 1
    # if 'hanging_gardens' in data['owned_wonders']:
    #     food_bonus = 2
    # if 'the_black_forest' in data['owned_wonders']:
    #     timber_bonus = 2
    # if 'the_chongalayas' in data['owned_wonders']:
    #     metal_bonus = 2
    # if 'the_rivers_of_chonga' in data['owned_wonders']:
    #     wealth_bonus = 2
    # if 'the_oil_fields_of_chonga' in data['owned_wonders']:
    #     oil_bonus = 2
    # if 'palace_of_versailles' in data['owned_wonders']:
    #     knowledge_bonus = 2

    if time_passed_hours >= 1:  # as long as 1 hour has passed, we can collect
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
        time_remaining_seconds = max(0, 3600 - (current_time - data['resources']['last_claim']) % 3600)

        # Convert time remaining to hours, minutes, and seconds
        remaining_hours, remaining_seconds = divmod(time_remaining_seconds, 3600)
        remaining_minutes, remaining_seconds = divmod(remaining_seconds, 60)

        # Prepare the Discord embed for the time remaining message
        embed = nextcord.Embed(
            title='Already Claimed Within the Hour',
            description=(
                f'You have already claimed within the hour. Please wait another hour.\n'
                f'Next Claim in: {remaining_hours} hours, {remaining_minutes} minutes, {int(remaining_seconds)} seconds'
            ),
            color=0xff0000  # Set the color of the embed as needed
        )
        await ctx.send(embed=embed)
    
@client.command(name='train', aliases=['Train', 'TRAIN'], description='See unit prices and purchase unit')
async def shop(ctx, arg1=None, arg2=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_shop(user_id, arg1, arg2)
    user_stats = utils.get_user_stats(user_id)

    if error:
        embed = nextcord.Embed(description=response, color=0xff0000)
        await ctx.send(embed=embed)
    elif arg1 is None:
        age = utils.get_age(user_id)
        units_info = utils.get_normal_units()[age]
        print(units_info)
        embed = nextcord.Embed(title='Hero Units Information', color=0xffd700)  # You can customize the color as needed
        for unit_name, unit_info in units_info.items():
                rolls_str = f"Rolls: {unit_info['rolls']['lowerbound']} - {unit_info['rolls']['upperbound']}"
                combat_type_str = f"Combat Type: {unit_info['combat_type'].capitalize()}"
                unit_type_str = f"Type: {unit_info['type'].capitalize()}" if unit_info['type'] else ""
                unit_description = f"{rolls_str}\n{combat_type_str}\n{unit_type_str}"

                embed.add_field(name=f"{unit_name.capitalize()}", value=unit_description, inline=False)

        await ctx.send(embed=embed)
    else:
        age = utils.get_age(user_id)
        users_units = utils.get_users_available_units(age)
        user_stats = utils.get_user_stats(user_id)

        unit = arg1
        num_units = arg2
        if arg2 == None:
            num_units = 1
        if arg2 == 'max':
            num_units = utils.calculate_max(unit, 'unit', user_stats)

        resource_cost = utils.validate_execute_shop(user_id, unit, num_units)
        if str(unit) not in users_units:
            embed = nextcord.Embed(description='This unit does not exist in the game or you do not have access to this unit.', color=0xff0000)
            await ctx.send(embed=embed)
        else:
            if not resource_cost[0]:
                embed = nextcord.Embed(description='You must construct additional pylons (not enough resources)', color=0xff0000)
                await ctx.send(embed=embed)
                return
            utils.update_resource(user_id, resource_cost[1])
            multiplier = 1
            if 'terra_chonga_army' in user_stats['owned_wonders']:
                multiplier = 2
            utils.update_units(user_id, unit, num_units * multiplier)
            embed = nextcord.Embed(description=f'```Successfully bought {num_units * multiplier} {unit}s```', color=0x00ff00)
            await ctx.send(embed=embed)

@client.command(name='build', aliases=['Build', 'BUILD'], description='See building prices, and build buildings')
async def build(ctx, arg1=None, arg2=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_build(user_id, arg1, arg2)
    if error:
        await ctx.send(response)
    elif arg1 is None and arg2 is None:
        age = utils.get_age(user_id)
        building_costs = utils.get_buildings_costs_by_age(age)
        embed = nextcord.Embed(title='Building Costs', color=0x00ff00)
        for building, cost in building_costs.items():
            cost_lines = [f'{resource.capitalize()}: {value}' for resource, value in cost.items()]
            # cost_str = ', '.join(cost_lines)
            embed.add_field(name=building.capitalize(), value=f'{cost_lines}', inline=False)
        await ctx.send(embed=embed)
    else:
        building = arg1
        if arg2 == None:
            num_build = 1
        if arg2 != None and arg2.isnumeric():
            num_build = int(arg2)
        if arg2 == 'max':
            num_build = utils.calculate_max(building, 'building', utils.get_user_stats(user_id))
        if num_build > 0:
            if utils.buy_building(user_id, building.lower(), num_build):
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
    error, response = utils.check_age(ctx, user_id)
    if error:
        await ctx.send(f'{response}\n')
    result = utils.upgrade_age(user_id)
    if result[0]:
        await ctx.send('```Successfully advanced to the ' + result[1] + ' age!```')
    else:
        await ctx.send('```You got no M\'s in ur bank account (not enough knowledge) or you\'re at most advanced age.```')

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
            description=f'Here is a list of players you can attack:\n {players_str}',
            color=0xff0000  # Set the color of the embed as needed
        )
        await ctx.channel.send(embed=embed)
    else:
        attacker_stats, attacker_army, defender_stats, defender_army = utils.form_pvp_armies(user_id, response)
        #get casualties
        attacker_army, attacker_casualties, defender_army, defender_casualties, winner = utils.attack_sequence(attacker_stats, attacker_army, defender_stats, defender_army)
        #update armies
        print(attacker_army, defender_army)
        utils.update_army(user_id, attacker_army)
        utils.update_army(response, defender_army)
        #update resources
        if winner == 'attacker':
            winner_id = user_id
            loser_id = response
        if winner == 'defender':
            winner_id = response
            loser_id = user_id
        utils.award_tribute(winner_id, loser_id)
        #generate battle_summary
        utils.generate_battle_summary()

        user_stats = utils.get_user_stats(user_id)
        target_user_stats = utils.get_user_stats(response)

        embed = nextcord.Embed(
            title='BATTLE SUMMARY',
            description=f'{user_id["winner"]} DEFEATED {user_id["loser"]}',
            color=0xff0000  # You can set the color of the embed here
        )
        embed.add_field(name='Winner', value=f'{user_id["winner_username"]}')
        embed.add_field(name='Loser', value=f'{user_id["loser_username"]}')
        embed.add_field(name='Winner Left You A Message', value=f'{user_id["winner_motto"]}', inline=False)
        embed.add_field(name='Winner Battle Rating', value=f'{user_id["winner_battle_rating"]} (+25)')
        embed.add_field(name='Loser Battle Rating', value=f'{user_id["loser_battle_rating"]} (-25)')
        embed.add_field(name='Plundered', value=f'{user_id["tribute"]}')
        embed.add_field(name='Attacker Casualties', value=f'{user_id["attacker_casualties"]}')
        embed.add_field(name='Defender Casualties', value=f'{user_id["defender_casualties"]}')

        await ctx.send(embed=embed)

        attacker = await client.fetch_user(user_id)
        defender = await client.fetch_user(response)

        for user, role in [(attacker, 'ATTACKED'), (defender, 'DEFENDED AGAINST')]:
            await user.send(embed=embed)

@client.command(name='motto', aliases=['Motto', 'MOTTO'], description='Set your motto to leave a msg for enemies')
async def set_motto(ctx, *, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    user_stats = utils.get_user_stats(user_id)
    error, response = utils.check_motto(ctx, user_id, arg)
    if error:
        await ctx.send(response)
    elif arg:
        user_stats['motto'] = arg
        utils.update_nation(user_id, user_stats)
        await ctx.send(f"Your motto has been set to: `{arg}`")
    else:
        await ctx.send("Please provide a motto. Example: `c!motto Your motto goes here`")

#shows whats new this patch
@client.command(name='patch', aliases=['Patch', 'PATCH'], description='See list of patch notes')
async def display_patch(ctx, arg=None):
    await ctx.send(
    '``` Please Check the github README for more details'
    'You c!shop has been changed to c!train, additionally you can type \'unit max\' to puchase the max amount of units you can afford, same for c!build building max\n'
    'keeps, castles, fortresses, army_base, planetary_fortresses have been move to build instead of train\n'
    'You can only attack within your own age\n'
    'New hero units! you can get them by exploring!\n'
    'Exploring has been revamped, exploration units have been taken out and now works like TFT augments.\n'
    'Unit counters have been implemented. Check the github README for more details\n'
    'You can now research different things to increase production levels, you must also research everything in your age to go to the next age\n'
    'Alliances has been implemented\n'
    'Implemented Bosses for alliances\n'
    '\n'
    '```'
    )

@client.command(name='explore', aliases=['Explore', 'EXPLORE'], description='Send out exploration units to trigger events')
async def display_patch(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_explore(ctx, user_id, arg)
    if error == True:
        await ctx.send(response)
    else:
        async def callback(selected_option, interaction):
            msg_embed = utils.execute_explore(user_id, selected_option)
            await ctx.send(embed=msg_embed)

        user_army = utils.get_user_army(user_id)
        exploration_options = utils.get_exploration_options(user_id, user_army)
        exploration_view = ExplorationView(user_id, exploration_options, callback)
        await ctx.send('Please select one option', view=exploration_view)

@client.command(name='wonder', aliases=['Wonder', 'WONDER', 'wonders', 'Wonders', 'WONDERS', 'wonder list', 'Wonder List', 'WonderList', 'wonderlist'], 
                description='See information on wonders')
async def wonder(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    
    wonders_list = utils.get_wonder_info()
    embed = nextcord.Embed(title='Wonders Information', color=0x00ff00)  # You can customize the color as needed

    for era, wonders in wonders_list.items():
        era_field_value = ""
        for wonder_name, wonder_info in wonders.items():
            era_field_value += f"*{utils.format_string(wonder_name)}*: {wonder_info['desc']})\n"

        embed.add_field(name=f"{era.capitalize()} Era", value=era_field_value, inline=False)

    await ctx.send(embed=embed)

@client.command(name='announce', aliases=['Announce', 'ANNOUNCE'])
async def announce(ctx, *, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    if(ctx.message.author.id == 217413468410609664):
        user_ids = list(db.Nations.find({},{ "_id"}))
        user_ids = [user['_id'] for user in user_ids]
        chaneys_message = arg
        for user_id in user_ids:
            user = await client.fetch_user(user_id)
            await user.send(chaneys_message)
    else:
        await ctx.send('HAHA ur not Chaney!')

#trigger random events with storyline
@client.command(name='createalliance', aliases=['CREATEALLIANCE', 'CreateAlliance'])
async def event(ctx, arg=None):
    await ctx.send('Command coming soon...')

@client.command(name='research', aliases=['RESEARCH', 'Research'])
async def event(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    error, response = utils.check_research(ctx, user_id, arg)
    if error == True:
        await ctx.send(response)
    else:
        if arg == None:
            age = utils.get_age(user_id)
            research_info = utils.get_research_info_by_age(age)
            embed = nextcord.Embed(title=f"Research Information:", color=0x00ff00)
            for technology, details in research_info.items():
                cost = details['costs']
                embed.add_field(
                    name=f'{technology.capitalize()}',
                    value=f'Costs: {cost} knowledge \n Description: {details["desc"]}',
                    inline=False
                )

            # # Send the embed
            await ctx.send(embed=embed)
        else:
            status, response = utils.research(user_id, arg)
            await ctx.send(f'```{response}```')

#trigger random events with storyline
@client.command(name='hero', aliases=['Hero', 'HERO', 'heroes', 'Heroes', 'HEROES'])
async def event(ctx, arg=None):
    user_id, server_id, username = utils.get_message_info(ctx)
    age = utils.get_age(user_id)
    units_info = utils.get_hero_units()[age]
    embed = nextcord.Embed(title='Hero Units Information', color=0xffd700)  # You can customize the color as needed
    print(units_info)
    for unit_name, unit_info in units_info.items():
            rolls_str = f"Rolls: {unit_info['rolls']['lowerbound']} - {unit_info['rolls']['upperbound']}"
            combat_type_str = f"Combat Type: {unit_info['combat_type'].capitalize()}"
            unit_type_str = f"Type: {unit_info['type'].capitalize()}" if unit_info['type'] else ""
            unit_description = f"{rolls_str}\n{combat_type_str}\n{unit_type_str}\nDesc: {unit_info['desc']}"

            embed.add_field(name=f"{unit_name.capitalize()}", value=unit_description, inline=False)
    await ctx.send(embed=embed)

client.run(TOKEN)




