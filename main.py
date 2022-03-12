from dotenv import load_dotenv
import nextcord
import os
import utils
import json
import pymongo
import objects.nation as nation

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
    print(msgContent)
    if message.content.startswith('/createNation'):
        """
        Create a nation
            arg1 = name of nation
            arg2 = nation ability

            Must check if user already has nation or if nation name is taken
            Then Display something to user ot know their command worked
        """
        author = str(message.author)
        name = msgContent[1]
        ability = msgContent[2]
        userNation = nation.createNation(author, name, ability)
        if not utils.checkDuplicateCreation(message.author, name):
            db.Nations.insert_one(userNation.__dict__)
    elif message.content.startswith('/resources'):
        """Display your nations total resources """
        resources = utils.getAuthorResources(message.author.id)
        resources = json.loads(resources)
        await message.channel.send(
            'Nation: ' + str(resources[0]['name']) + '\n'
            'Food:  ' + str(resources[0]['food']) + '\n'
            'Timber:' + str(resources[0]['timber']) + '\n'
            'Metal: ' + str(resources[0]['metal']) + '\n'
            'Oil: ' + str(resources[0]['oil']) + '\n'
            'Wealth: ' + str(resources[0]['wealth']) + '\n'
            'Knowledge: ' + str(resources[0]['knowledge']) + '\n'        
        )

    elif message.content.startswith('/nations'):
        """Display a list of all nations on a server """
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
    elif message.content.startswith('/buy'):
        """"Buys the unit for the author and then adds it to mongodb"""
        pass
    elif message.content.startswith('/attack'):
        """Attack another player and go through the attack procedure"""
        pass
    elif message.content.startswith('/help'):
        """Provide a list of commands"""
        pass
    
client.run(TOKEN)