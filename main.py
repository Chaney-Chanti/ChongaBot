from dataclasses import dataclass
from dotenv import load_dotenv
import nextcord
import os
import utils
import json
import pymongo
import objects.nation
import objects.resources
import time
import pprint

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
TOKEN = os.environ.get('DISCORDTOKEN')

mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot
client = nextcord.Client()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    msgContent = message.content.split(' ')
    userID = message.author.id
    serverID = message.guild.id
    username = str(message.author)

    if message.content.startswith('/createNation'): 
        if len(msgContent) != 2:
             await message.channel.send('Incorrect parameters. Format: /createNation [name]')
        name = msgContent[1]
        userNation = objects.nation.createNation(userID, serverID, username, name)
        userResources = objects.resources.createResources(userID, username, name, time.time())
        if not utils.checkCreation(userID, name): #Note: we are double checking database here, fix later
            db.Nations.insert_one(userNation.__dict__)
            db.Resources.insert_one(userResources.__dict__)
            await message.channel.send('Nation Created! Type /stats to show info about your nation!')
        else:
            await message.channel.send('You either already have a nation or profanity was found in the creation...')
    elif message.content.startswith('/stats'):
        if len(msgContent) == 2:
            user = msgContent[1] 
        elif len(msgContent) == 1:
            user = message.author.id
        else:
             await message.channel.send('Incorrect parameters. Format: /stats or /stats [user]')
        data = utils.getUserStats(user)
        pprint.pprint(data)
        
        await message.channel.send( #Figure out a way to make this horizontal than like a column
            '=======' + str(data['name']) + '=======\n'
            'Owner: ' + str(data['username']) + '\n' 
            'Age: ' + str(data['age']) + '\n'
            'Ability: ' + str(data['ability']) + '\n'
            'BattleRating: ' + str(data['battleRating']) + '\n'
            '======Resources======\n'
            'Food: ' + str(data['resources']['food']) + '\n'
            'Timber: ' + str(data['resources']['timber']) + '\n'
            'Metal: ' + str(data['resources']['metal']) + '\n'
            'Oil: ' + str(data['resources']['oil']) + '\n'
            'Wealth: ' + str(data['resources']['wealth']) + '\n'
            'Knowledge: ' + str(data['resources']['knowledge']) + '\n'
            '======Buildings====== \n'
            'Granary Level: ' + str(data['granary']['level']) + '\n'
            'Water Mill Level: ' + str(data['waterMill']['level']) + '\n'
            'Quarry Level: ' + str(data['quarry']['level']) + '\n'
            'Oil Rig Level: ' + str(data['oilRig']['level']) + '\n'
            'Market Level: ' + str(data['market']['level']) + '\n'
            'University Level: ' + str(data['university']['level']) + '\n'
            'Market Level: ' + str(data['market']['level']) + '\n'
        )
    elif message.content.startswith('/rankings'):
        nations = utils.getRankings()
        rankingString = ''
        rank = 1
        for nation in nations:
            rank = str(rank)
            rankingString = rankingString + '======\nRank #' + rank +'\nOwner: ' + nation['username'] + '\nNation: ' + nation['name'] + '\nBattle Rating: ' + str(nation['battleRating']) + '\n======'
            rank = int(rank)
            rank +=1
        await message.channel.send(rankingString)

    elif message.content.startswith('/claim'):
        pass
    elif message.content.startswith('/army'):
        pass
    elif message.content.startswith('/buy'): 
        if len(msgContent) != 3:
            await message.channel.send('Incorrect parameters. Format: /buy [unit] [number]')

        unit = msgContent[1]
        number = msgContent[2]

        #I want pop culture references
        medievalList = ['Citizen', 'Lancer', 'Archer', 'Wizards', 'Dragons']
        enlightmentList = ['Citizen', 'Minutemen', 'Cannon']
        modernList = ['Citizen', 'Infantry', 'Tank', 'Fighter', 'Bomber', 'ICBM']
        spaceList = ['Citizen', 'Lazer Cannon', 'Starfighter', 'Battlecruiser', 'Death Star']

        age = utils.getAge(userID)
        resourceCost = utils.validateBuy(userID, number)

        if age == 'Medieval':
            unitList = medievalList
        elif age == 'Enlightment':
            unitList = enlightmentList
        elif age == 'Modern':
            unitList = modernList
        elif age == 'Space':
            unitList = spaceList
        
        if unit in unitList and resourceCost > 0:
            #Go through with the buy
            pass

    elif message.content.startswith('/attack'):
        if len(msgContent) != 2 or len(message.mentions) == 0:
            await message.channel.send('Incorrect parameters. Format: /attack [player]')
        elif not utils.playerExists(message.mentions[0].id):
            await message.channel.send('This player does not exist')
        elif utils.checkBattleRatingRange(userID, message.mentions[0].id):
            await message.channel.send('Player is ranked too either to high or below you')
        else: 
            attackerID = userID
            defenderID = message.mentions[0].id 
            utils.attackSequence(attackerID, defenderID)
        
    elif message.content.startswith('/Chongahelp'): #Don't know how to make commands not conflict with other bots
        await message.channel.send(
            '========RULES========\n'
            'Create your own nation and attack other players.\n' 
            'Manage resources (Food, Timber, Metal, Oil, Wealth, Knowledge) to grow stronger.\n'
            'Citizens mine all resources at a certain rate.\n' 
            'You only get one nation for all servers.\n' 
            '========Commands========\n' 
            '/createNation [name] - Create a nation\n' 
            '/stats - View what your resources are\n' 
            '/rankings - View the rankings of everyone who plays\n' 
            '/buy [units] [number] - Buys n number of units\n'
            '/attack [player] - Attack a player\n'
            '/Chongahelp [player] - List of commands and rules\n'
        )
        
client.run(TOKEN)



