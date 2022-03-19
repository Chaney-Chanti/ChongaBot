from dotenv import load_dotenv
import nextcord
import os
import utils
import json
import pymongo
import objects.nation
import subprocess

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
TOKEN = os.environ.get('DISCORDTOKEN')

mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot
client = nextcord.Client()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    # subprocess.Popen('py -3 bgProcessing.py')

@client.event
async def on_message(message):
    print(message.content)
    if message.author == client.user:
        return
    msgContent = message.content.split(' ')
    print(msgContent)
    userID = message.author.id
    serverID = message.guild.id
    username = str(message.author)

    if message.content.startswith('/createNation'): 
        if len(msgContent) != 3:
             await message.channel.send('Incorrect parameters. Format: /createNation [name] [ability]')
        name = msgContent[1]
        ability = msgContent[2]
        userNation = objects.nation.createNation(userID, serverID, username, name, ability)
        if not utils.checkCreation(userID, name):
            db.Nations.insert_one(userNation.__dict__)
            await message.channel.send('Nation Created! Type /stats to show info about your nation!')
        else:
            await message.channel.send('You either already have a nation, or profanity was found in the creation...')
    if message.content.startswith('/stats'):
        if len(msgContent) == 2:
            user = msgContent[1] #Doesn't work I need to figure out @players
        elif len(msgContent) == 1:
            user = message.author.id
        else:
             await message.channel.send('Incorrect parameters. Format: /stats or /stats [user]')
        resources = utils.getUserStats(user)
        resources = json.loads(resources)
        await message.channel.send( #Figure out a way to make this horizontal than like a column
            '=======' + str(resources[0]['name']) + '=======\n'
            'Owner: ' + str(resources[0]['username']) + '\n' 
            'Age: ' + str(resources[0]['age']) + '\n'
            'Ability: ' + str(resources[0]['ability']) + '\n'
            'Population: ' + str(resources[0]['population']) + '\n'
            'Shield: ' + str(resources[0]['shield']['timer']) + '\n'
            '======Resources======\n'
            'Food: ' + str(resources[0]['food']) + '\n'
            'Timber: ' + str(resources[0]['timber']) + '\n'
            'Metal: ' + str(resources[0]['metal']) + '\n'
            'Oil: ' + str(resources[0]['oil']) + '\n'
            'Wealth: ' + str(resources[0]['wealth']) + '\n'
            'Knowledge: ' + str(resources[0]['knowledge']) + '\n'
            '======Buildings====== \n'
            'Granary Level: ' + str(resources[0]['granary']['level']) + '\n'
            'Water Mill Level: ' + str(resources[0]['waterMill']['level']) + '\n'
            'Quarry Level: ' + str(resources[0]['quarry']['level']) + '\n'
            'Oil Rig Level: ' + str(resources[0]['oilRig']['level']) + '\n'
            'Market Level: ' + str(resources[0]['market']['level']) + '\n'
            'University Level: ' + str(resources[0]['university']['level']) + '\n'
            'Market Level: ' + str(resources[0]['market']['level']) + '\n'
        )
    if message.content.startswith('/rankings'):
        nations = utils.getRankings()
        nationListString = ''
        rank = 1
        for nation in nations:
            rank = str(rank)
            nationListString = nationListString + '======\nRank #' + rank +'\nOwner: ' + nation['username'] + '\nNation: ' + nation['name'] + '\nPopulation: ' + str(nation['population']) + '\n======'
            rank = int(rank)
            rank +=1
        await message.channel.send(nationListString)
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
        spaceList = ['Citizen', 'Shock Troopers', 'Starfighter', 'Battlecruiser', 'Death Star']

        twitchList = ['Citizen', 'Pogchamps', 'MonkaS', 'KekW', 'KKhona']
        animeList = ['Citizen', 'Collossal Titan', 'Avatar', 'Pokemon', 'Harem']
        modernList = ['Citizen', 'Infantry', 'Tank', 'Fighter', 'Bomber', 'ICBM']
        spaceList = ['Citizen', 'Shock Troopers', 'Starfighter', 'Battlecruiser', 'Death Star']

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
        if len(msgContent) != 3:
            await message.channel.send('Incorrect parameters. Format: /attack [player]')
        elif utils.playerHasShield():
            await message.channel.send('You cannot attack this player, they have a shield.')
        elif utils.playerExists():
            await message.channel.send('This player does not exist')
        else: #Battle Sequence
            utils.attackSequence(message.player.id, message.player.id2)
        
    elif message.content.startswith('/Chongahelp'): #Don't know how to make commands not conflict with other bots
        await message.channel.send(
            '========RULES========\n'
            'Create your own nation and attack other players.\n' 
            'Manage resources (Food, Timber, Metal, Oil, Wealth, Knowledge) to grow stronger.\n'
            'Citizens mine all resources at a certain rate.\n' 
            'You only get one nation for all servers.\n' 
            '========Commands========\n' 
            '/createNation [name] [ability] - Create a nation\n' 
            '/stats - View what your resources are\n' 
            '/rankings - View the rankings of everyone who plays\n' 
            '/buy [units] [number] - Buys n number of units\n'
            '/attack [player] - Attack a player\n'
            '/help [player] - List of commands and rules\n'
        )
        
client.run(TOKEN)



