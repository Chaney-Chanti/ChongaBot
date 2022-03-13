from dotenv import load_dotenv
from hikari import Guild
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
        userNation = nation.createNation(message.author.id, message.guild.id, msgContent[1], msgContent[2])
        if not utils.checkDuplicateCreation(message.author.id, message.guild.id):
            db.Nations.insert_one(userNation.__dict__)
            
    if message.content.startswith('/resources'):
        """Display your nations total resources """
        message.author.id
        pass
    if message.content.startswith('/nations'):
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