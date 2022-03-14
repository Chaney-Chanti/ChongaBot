from dotenv import load_dotenv
from time import time, sleep
import nextcord
import os
import utils
import json
import pymongo
import objects.nation, objects.resources

load_dotenv()
CONNECTIONPASSWORD = os.environ.get('MONGODBCONNECTION')
TOKEN = os.environ.get('DISCORDTOKEN')

mongoClient = pymongo.MongoClient(CONNECTIONPASSWORD)
db = mongoClient.ChongaBot
client = nextcord.Client()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    # while True:
    #     sleep(60 - time() % 60)
    #     utils.addResources()

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    msgContent = message.content.split(' ')
    print(msgContent)

    if message.content.startswith('/createNation'): 
        """
        Create a nation
            arg1 = name of nation
            arg2 = nation ability

            * Must check if user already has nation or if nation name is taken
            * Then Display something to user ot know their command worked
            * Filter swear words from nations creation
        """
        if len(msgContent) != 3:
             await message.channel.send('Incorrect parameters. Format: /createNation [name] [ability]')
        name = msgContent[1]
        ability = msgContent[2]
        userID = message.author.id
        serverID = message.guild.id
        username = str(message.author)
        userNation = objects.nation.createNation(userID, serverID, username, name, ability)
        userResources = objects.resources.createResources(userID, username, name, ability)
        if not utils.checkCreation(userID, name):
            db.Nations.insert_one(userNation.__dict__)
            db.Resources.insert_one(userResources.__dict__)
            await message.channel.send('Nation Created! Type /resources to show info about your nation!')
        else:
            await message.channel.send('You either already have a nation, or profanity was found in the creation...')
    if message.content.startswith('/resources'): #maybe instead do /stats and all encompass resources with units and shield/no shield etc
        """Display your nations total resources """
        resources = utils.getAuthorResources(message.author.id)
        resources = json.loads(resources)
        print(resources)
        await message.channel.send(
            'Nation: ' + str(resources[0]['name']) + '\n'
            'Food:  ' + str(resources[0]['food']) + '\n'
            'Timber:' + str(resources[0]['timber']) + '\n'
            'Metal: ' + str(resources[0]['metal']) + '\n'
            'Oil: ' + str(resources[0]['oil']) + '\n'
            'Wealth: ' + str(resources[0]['wealth']) + '\n'
            'Knowledge: ' + str(resources[0]['knowledge']) + '\n'        
        )
    if message.content.startswith('/rankings'):
        """Display a list of all nations across all servers in the order of population """
        nations = utils.getNationList(message.guild.id)
        nations = json.loads(nations)
        cache = {}
        for nation in nations:
           cache[nation['name']] = str(nation['population'])
        await message.channel.send(cache)
    elif message.content.startswith('/army'):
        """
        Display a list of a users nation 
        Do I need to make a self.unit for every unit in my class?
        Make an army subclass with each unit?
        """
        pass
    elif message.content.startswith('/buy'): 
        """"Buys the unit for the author and then adds it to mongodb"""
        if len(msgContent) != 3:
            await message.channel.send('Incorrect parameters. Format: /buy [unit] [number]')
    elif message.content.startswith('/attack'):
        """Attack another player and go through the attack procedure"""
        if len(msgContent) != 3:
            await message.channel.send('Incorrect parameters. Format: /attack [player]')
        if utils.playerHasShield():
            pass
    elif message.content.startswith('/Chongahelp'): #Don't know how to make commands not conflict with other bots
        """Provide a list of commands and how to play"""
        await message.channel.send(
            '========RULES========\n'
            'Create your own nation and attack other players.\n' 
            'Manage an resoures (Food, Timber, Metal, Oil, Wealth, Knowledge) to grow stronger.\n'
            'Citizens mine all reasources as a certain rate.\n' 
            'You only get one nation for all servers.\n' 
            '========Commands========\n' 
            '/createNation [name] [ability] - Create a nation\n' 
            '/resources - View what your resources are\n' 
            '/rankings - View the rankings of everyone who plays\n' 
            '/population - View what units you have\n'
            '/buy [units] [number] - Buys n number of units\n'
            '/attack [player] - Attack a player\n'
            '/help [player] - List of commands and rules\n'
        )
        
client.run(TOKEN)



