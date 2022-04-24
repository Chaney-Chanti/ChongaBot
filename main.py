from attr import has
from dotenv import load_dotenv
import nextcord
import os
import utils
import json
import pymongo
import objects.nation, objects.resources, objects.army
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
    print('Currently in ' + str(len(client.guilds)) + ' servers');

@client.event
async def on_message(message):
    prefix = 'c!'
    if message.author == client.user:
        return
    #Text processing
    message.content = message.content.lower()
    msgContent = message.content.split(' ')
    userID = message.author.id
    serverID = message.guild.id
    username = str(message.author)
    print('DEBUG:', msgContent)

    if message.content.startswith(prefix +'createnation'): 
        if len(msgContent) != 2:
            await message.channel.send('Incorrect parameters. Format: ' + prefix + 'createnation [name]')
        if len(msgContent[1]) > 20:
            await message.channel.send('Nation Name is too long!')
        else:
            name = msgContent[1]
            userNation = objects.nation.createNation(userID, serverID, username, name, time.time())
            userResources = objects.resources.createResources(userID, username, name, time.time())
            userArmy = objects.army.createArmy(userID, username, name)
            if not utils.checkCreation(userID, name): 
                db.Nations.insert_one(userNation.__dict__)
                db.Resources.insert_one(userResources.__dict__)
                db.Army.insert_one(userArmy.__dict__)
                await message.channel.send('Nation Created! Type ' + prefix + 'stats to show info about your nation!')
            else:
                await message.channel.send('You either already have a nation or profanity was found in the creation...')
    elif message.content.startswith(prefix + 'stats'):
        if len(msgContent) == 2:
            if utils.playerExists(message.mentions[0].id):
                user = message.mentions[0].id
            else:
                await message.channel.send('This player does not exist')
        elif len(msgContent) == 1:
            user = message.author.id
        else:
             await message.channel.send('Incorrect parameters. Format: ' + prefix + 'stats or ' + prefix + 'stats [user]')
        data = utils.getUserStats(user)
        await message.channel.send( #Figure out a way to make this horizontal than like a column (paging)
            '```=======' + str(data['name']) + '=======\n'
            'Owner: ' + str(data['username']) + '\n' 
            'Age: ' + str(data['age']) + '\n'
            'Ability: ' + str(data['ability']) + '\n'
            'BattleRating: ' + str(data['battleRating']) + '\n'
            'Shield (When this person can be attacked): ' + str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['shield']+ 86400))) + '\n'
            '======Resources======\n'
            'Food: ' + str(data['resources']['food']) + '\n'
            'Timber: ' + str(data['resources']['timber']) + '\n'
            'Metal: ' + str(data['resources']['metal']) + '\n'
            'Oil: ' + str(data['resources']['oil']) + '\n'
            'Wealth: ' + str(data['resources']['wealth']) + '\n'
            'Knowledge: ' + str(data['resources']['knowledge']) + '\n'
            '======Buildings====== \n'
            'Granaries: ' + str(data['granary']['numBuildings']) + '\n'
            'Lumbermills: ' + str(data['lumbermill']['numBuildings']) + '\n'
            'Quarries: ' + str(data['quarry']['numBuildings']) + '\n'
            'Oil Rigs: ' + str(data['oilrig']['numBuildings']) + '\n'
            'Markets: ' + str(data['market']['numBuildings']) + '\n'
            'Universities: ' + str(data['university']['numBuildings']) + '\n```'
        )
    elif message.content.startswith(prefix + 'leaderboard'):
        nations = utils.getRankings()
        rankingString = ''
        rank = 1
        for nation in nations:
            rank = str(rank)
            rankingString = rankingString + '======\nRank #' + rank +'\nOwner: ' + nation['username'] + '\nNation: ' + nation['name'] + '\nBattle Rating: ' + str(nation['battleRating']) + '\n======'
            rank = int(rank)
            rank +=1
        await message.channel.send('```' + rankingString + '```')

    elif message.content.startswith(prefix + 'claim'):
        currentTime = time.time()
        data = utils.getUserStats(userID)
        timePassed = int(currentTime - data['resources']['lastClaim'])
        timePassed = int(timePassed // 3600) # get total number of hours since last claim
        if timePassed >= 48:
            timePassed = 48
        if (timePassed > 0):
            food = data['resources']['foodrate'] * timePassed + data['resources']['food']
            timber = data['resources']['timberrate'] * timePassed + data['resources']['timber']
            metal = data['resources']['metalrate'] * timePassed + data['resources']['metal']
            wealth = data['resources']['wealthrate'] * timePassed + data['resources']['wealth']
            oil = data['resources']['oilrate'] * timePassed + data['resources']['oil']
            knowledge = data['resources']['knowledgerate'] * timePassed + data['resources']['knowledge']

            db.Resources.update_one({'userID': userID}, {'$set': {'lastClaim': currentTime, 'food': food, 'timber': timber, 'metal': metal, 'wealth': wealth, 'oil': oil, 'knowledge': knowledge}})
            await message.channel.send(
                '```Resources Claimed:\n'
                'Food: ' + str(data['resources']['foodrate'] * timePassed) + '\n'
                'Timber: ' + str(data['resources']['timberrate'] * timePassed) + '\n'
                'Metal: ' + str(data['resources']['metalrate'] * timePassed) + '\n'
                'Wealth: ' + str(data['resources']['wealthrate'] * timePassed) + '\n'
                'Oil: ' + str(data['resources']['oilrate'] * timePassed) + '\n'
                'Knowledge: ' + str(data['resources']['knowledgerate'] * timePassed) + '\n```'
            )
        else:
            await message.channel.send('You have already claimed within the hour. Please wait another hour.')

    elif message.content.startswith(prefix + 'army'):
        if len(msgContent) == 2:
            if utils.playerExists(message.mentions[0].id):
                user = message.mentions[0].id
            else:
                await message.channel.send('This player does not exist')
        elif len(msgContent) == 1:
            user = message.author.id
        else:
            await message.channel.send('Incorrect parameters. Format: ' + prefix + 'army or ' + prefix + 'army [user]')
        armyData = utils.getUserArmy(userID)
        units = utils.getUnits()
        hasArmy = False
        for unit in armyData:
            if unit in units and armyData[unit] > 0 :
                hasArmy = True
                break
        if hasArmy == False:
            await message.channel.send('Sadge, you have no army...')
        else:
            armyStr = ''
            for unit in armyData:
                if unit != 'userID' and unit != 'username' and unit != 'name' and armyData[unit] != 0:
                    armyStr += unit + ': ' + str(armyData[unit]) + '\n'
            await message.channel.send(armyStr)

    elif message.content.startswith(prefix + 'shop'):
        if len(msgContent) > 3:
            await message.channel.send('Incorrect parameters. Format: ' + prefix + 'shop [unit] [number]')
        elif len(msgContent) == 1 and 'shop' in msgContent[0]:
            age = utils.getAge(userID)
            unitCosts = utils.getUnitsCosts()
            unitRolls = utils.getUnitDiceRolls()

            if age == 'Medieval':
                await message.channel.send(
                    '```===Units You Can Buy=== \n'
                    'Lancers - cost: ' + str(unitCosts['lancer']['food']) + ' food, ' + str(unitCosts['lancer']['timber']) 
                    + ' timber | Roll: ' + str(unitRolls['lancer']['lowerBound']) + '-' + str(unitRolls['lancer']['upperBound']) + '\n'
                    'Archers - cost: ' + str(unitCosts['archer']['food']) + ' food, ' + str(unitCosts['archer']['timber']) 
                    + ' timber | Roll: ' + str(unitRolls['archer']['lowerBound']) + '-' + str(unitRolls['archer']['upperBound']) + '\n'
                    'Calvalry - cost: ' + str(unitCosts['calvalry']['food']) + ' food, ' + str(unitCosts['calvalry']['timber']) 
                    + ' timber | Roll: ' + str(unitRolls['calvalry']['lowerBound']) + '-' + str(unitRolls['calvalry']['upperBound']) + '\n'
                    'Trebuchets - cost: ' + str(unitCosts['trebuchet']['food']) + ' food, ' + str(unitCosts['trebuchet']['timber']) 
                    + ' timber | Roll: ' + str(unitRolls['trebuchet']['lowerBound']) + '-' + str(unitRolls['trebuchet']['upperBound']) + '\n```'
                )
            if age == 'Enlightment':
                 await message.channel.send(
                      '```===Units You Can Buy=== \n'
                    'Minutemen - cost: ' + str(unitCosts['minutemen']['food']) + ' food, ' + str(unitCosts['minutemen']['metal']) 
                    + ' metal | Roll: ' + str(unitRolls['minutemen']['lowerBound']) + '-' + str(unitRolls['minutemen']['upperBound']) + '\n'
                    'Generals - cost: ' + str(unitCosts['general']['food']) + ' food, ' + str(unitCosts['general']['metal']) 
                    + ' metal, ' + str(unitCosts['general']['wealth']) + 'wealth | Roll: ' + str(unitRolls['general']['lowerBound']) + '-' + str(unitRolls['general']['upperBound']) + '\n'
                    'Trebuchet - cost: ' + str(unitCosts['trebuchet']['food']) + ' food, ' + str(unitCosts['trebuchet']['timber']) 
                    + ' timber | Roll: ' + str(unitRolls['trebuchet']['lowerBound']) + '-' + str(unitRolls['trebuchet']['upperBound']) + '\n```'
                )
            if age == 'Modern':
                 await message.channel.send(
                    '```===Units You Can Buy=== \n'
                    'infantry - cost: 50 food, 50 timber |  Roll 3-5\n'
                    'tank- cost: 50 food, 50 timber | Roll: 5-10\n'
                    'fighter - cost: 50 food, 50 timber |  Roll 3-5\n'
                    'bomber - cost: 50 food, 50 timber |  Roll 3-5\n'
                    'icbm - cost: 50 food, 50 timber |  Roll 3-5\n```'
                )
            if age == 'Space':
                 await message.channel.send(
                    '```===Units You Can Buy=== \n'
                    'shocktrooper - cost: 50 food, 50 timber |  Roll 3-5\n'
                    'starfighter - cost: 50 food, 50 timber | Roll: 5-10\n'
                    'lasercannon - cost: 50 food, 50 timber |  Roll 3-5\n'
                    'battlecruiser - cost: 50 food, 50 timber |  Roll 3-5\n'
                    'deathstar - cost: 50 food, 50 timber |  Roll 3-5\n```'
                )
        elif not msgContent[2].isnumeric():
            await message.channel.send('You must specify a number of units to buy')
        else:
            unit = msgContent[1].lower()
            numUnits = msgContent[2]

            medievalList = ['citizen', 'lancer', 'archer', 'calvalry', 'trebuchet']
            enlightmentList = ['citizen', 'minutemen', 'general', 'cannon']
            modernList = ['citizen', 'infantry', 'tank', 'fighter', 'bomber', 'icbm']
            spaceList = ['citizen', 'shocktrooper', 'lasercannon', 'starfighter', 'battlecruiser', 'deathstar']

            age = utils.getAge(userID)

            if age == 'Medieval':
                unitList = medievalList
            elif age == 'Enlightment':
                unitList = enlightmentList
            elif age == 'Modern':
                unitList = modernList
            elif age == 'Space':
                unitList = spaceList
            else:
                unitList = [''] 
            
            resourceCost = utils.validateExecuteBuy(userID, unit, numUnits)
            if str(unit) not in unitList:
                await message.channel.send('This unit does not exist in the game or you do not have access to this unit.')
            else:
                if not resourceCost[0]:
                    await message.channel.send('You must construct additional pylons (not enough resources)')
                utils.updateResources(userID, resourceCost[1])
                utils.updateUnits(userID, unit, numUnits)
                await message.channel.send('Successfully bought ' + numUnits + ' ' + unit + 's')
    elif message.content.startswith(prefix + 'build'):
        buildings = ['granary', 'lumbermill', 'quarry', 'oilrig', 'market', 'university']
        if len(msgContent) == 1:
            buildingCosts = utils.getBuildingsCosts()
            await message.channel.send(
                '```=====Buildings=====\n'
                'Granary - cost: ' + str(buildingCosts['granary']['timber']) + ' timber, ' + str(buildingCosts['granary']['metal']) + ' metal\n'
                'Lumbermill - cost: ' + str(buildingCosts['lumbermill']['timber']) + ' timber, ' + str(buildingCosts['lumbermill']['metal']) + ' metal\n'
                'Quarry - cost: ' + str(buildingCosts['quarry']['timber']) + ' timber, ' + str(buildingCosts['quarry']['metal']) + ' metal\n'
                'Oil Rig - cost: ' + str(buildingCosts['oilrig']['metal']) + ' metal, ' + str(buildingCosts['oilrig']['wealth']) + ' wealth\n'
                'Market - cost: ' + str(buildingCosts['market']['food']) + ' food, ' + str(buildingCosts['market']['timber']) + ' timber, ' + str(buildingCosts['market']['wealth']) + ' wealth \n'
                'University - cost: ' + str(buildingCosts['university']['timber']) + ' timber, ' + str(buildingCosts['university']['metal']) + ' metal, ' + str(buildingCosts['university']['wealth']) + ' wealth \n```'
            )
        elif len(msgContent) == 2 and msgContent[1] in buildings:
            if utils.buyBuilding(userID, msgContent[1].lower()):
                await message.channel.send('Successfully built ' + msgContent[1])
            else:
                await message.channel.send('Bruh Moment... (not enough resources)')
        else:
            await message.channel.send('This building does not exist.')
    elif message.content.startswith(prefix + 'ages'):
        ageCosts = utils.getAgeCosts()
        await message.channel.send(
            '```Ages (Costs in Knowledge):\n ' + str(ageCosts) + '```'
        )
    elif message.content.startswith(prefix + 'nextage'):
        result = utils.upgradeAge(userID)
        print(result)
        if result[0]:
            await message.channel.send('Successfully advanced to the ' + result[1] + ' age!')
        else:
            await message.channel.send('You got no M\'s in ur bank account (not enough resources) or you\'re just maxed out.')

    elif message.content.startswith(prefix + 'attack'):
        if len(msgContent) == 1:
            players = utils.getVictims(userID)    
            await message.channel.send(
                '```Here Is A List of Players You Can Attack:\n' +
                str(players) + '```'
            )
        elif len(msgContent) > 2:
            await message.channel.send('Incorrect parameters. Format: ' + prefix + 'attack [player]')
        
        if len(message.mentions) > 0:
            defenderID = message.mentions[0].id
            if message.author.id == defenderID:
                await message.channel.send('You cannot attack yourself!')
        elif '#' in msgContent[1]:
            defenderID = msgContent[1]
            if message.author == message.content[1]:
                await message.channel.send('You cannot attack yourself!')

        if not utils.playerExists(defenderID):
            await message.channel.send('This player does not exist')
        elif not utils.checkBattleRatingRange(userID, defenderID):
            await message.channel.send('Player rating too either to high or below you(+-300)')
        elif utils.hasShield(defenderID, time.time()):
            await message.channel.send('This player has a shield, you can\'t attack them.')
        elif True:
            armyData = utils.getUserArmy(userID)
            units = utils.getUnits()
            hasArmy = False
            for unit in armyData:
                if unit in units and armyData[unit] > 0 :
                    hasArmy = True
                    break
            if hasArmy == False:
                await message.channel.send('Stop the cap you have no army...')
            else:
                print('lol')
                attackerID = userID
                if len(message.mentions[0].id):
                    defenderID = message.mentions[0].id 
                else:
                    defenderID = msgContent[1]
                data = utils.attackSequence(attackerID, defenderID)
                await message.channel.send(
                    '=====BATTLE SUMMARY=====\n' +
                    data['winner'] + ' DEFEATED ' + data['loser'] + '\n' +
                    data['winner'] + ' Battle Rating: ' + data['winnerBattleRating'] + ' (+25)\n' +
                    data['winner'] + ' Plundered ' + str(data['tribute']) + '\n' +
                    data['loser'] + ' Battle Rating: ' + data['loserBattleRating'] + ' (-25)\n' +
                    'Attacker Casualties: ' + data['attackerCasualties'] + '\n' +
                    'Defender Casualties: ' + data['defenderCasualties'] + '\n'
                )
    elif message.content.startswith(prefix + 'help'):
        await message.channel.send(
            '```========RULES========\n'
            'Create your own nation and attack other players.\n' 
            'Manage resources (Food, Timber, Metal, Oil, Wealth, Knowledge) to grow stronger.\n'
            'Citizens mine all resources at a certain rate.\n' 
            'Build/Upgrade buildings to increase resource rate.\n' 
            'Buy units and attack other players for resources and battle rating.\n' 
            'You only get one nation for all servers.\n' 
            '========Commands========\n' +
            prefix + 'createnation [name] - Create a nation\n' +
            prefix + 'stats - Info on your nation\n' +
            prefix + 'leaderboard - View the rankings of everyone who plays\n' + 
            prefix + 'claim - Collect resources (every hour)\n' +
            prefix + 'ages - Info on ages\n' +
            prefix + 'nextage - Go to the next age!\n' +
            prefix + 'shop - Info on units you can purchase\n' + 
            prefix + 'shop [units] [number] - Buys n number of units\n' + 
            prefix + 'build - Info on buildings you can build\n' + 
            prefix + 'build [building] - Build this building\n' +
            prefix + 'attack [player] - Attack a player (wins +25, losses -25)\n' + 
            prefix + 'help [player] - List of commands and rules\n```'
        )
        
client.run(TOKEN)
