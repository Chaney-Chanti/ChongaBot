import nextcord
import utils
import json
import pymongo
import objects.nation as nation

mongoClient = pymongo.MongoClient("mongodb+srv://Chonga:chaneychonga@chongabot.fukpc.mongodb.net/ChongaBot?retryWrites=true&w=majority")
db = mongoClient.ChongaBot

client = nextcord.Client()
TOKEN = 'OTUxMzkxNDIwMzE1NDY3Nzc2.YimyTg.Ya3orsZQmb3CQyyihy79BQlXYAw'

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
        """
        name = msgContent[1]
        ability = msgContent[2]
        print(db.Nation.find({}, {'name': name}).limit(1).explain())
        userNation = nation.createNation(name, ability)
        # db.Nations.insert_one(userNation.__dict__)
    if message.content.startswith('/resources'):
        """Display your nations total resources """
        pass
    if message.content.startswith('/nations'):
        """Display a list of all nations on a server """
        pass
    if message.content.startswith('/buy'):
        pass
    if message.content.startswith('/attack'):
        pass
    if message.content.startswith('/help'):
        """Provide a list of commands"""
        pass


client.run(TOKEN)