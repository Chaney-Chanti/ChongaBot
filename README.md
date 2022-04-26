# ChongaBot
Built with Nextcord and MongoDB

This is a fun project I decided to pursue in order to build my python skills. 

*IMPORTANT: The game is in beta, and I have only implemented the basic 
functionality of the game to be playable. The game is prone to bugs, but
I think I covered the important ones. Things to expect would be issues
with balancing unit rolls, progression, and inconvenience such as info displays
and usability.   

# Rules
### Description
Build a nation, gather resources to grow stronger, and defeat your enemies.

### How to play
Gather resources {Food, Timber, Metal, Wealth, Oil, and Knowledge}. 
Buy Units to attack other players (Units change based on age)
Building buildings to increase rate of production of resources
Climb the leaderboard by attcking players to gain battle rating.

* Details
    Ages: Medieval (starting), Enlightment, Modern, Space
    Costs (in knowledge):
    'Enlightment': 50000,
    'Modern': 200000,
    'Space': 1000000,
    Rate of Production of Resources:
    Medieval: +100
    Enlightment: +200
    Modern: +300
    Space: +400 

Units: 
    ===============Medieval===============: 
    'lancer': { 'lowerBound': 1, 'upperBound': 5},
    'archer': { 'lowerBound': 1, 'upperBound': 15},
    'calvalry': { 'lowerBound': 1, 'upperBound': 30},
    'trebuchet': {'lowerBound': 1, 'upperBound': 50},
                    Costs:  
    'lancer': { 'food': 50, 'timber': 50, },
    'archer': { 'food': 100, 'timber': 100, },
    'calvalry': { 'food': 200, 'timber': 200, },
    'trebuchet': { 'food': 300, 'timber': 300, },
    'minutemen': { 'food': 100, 'metal': 100, },
    ===============Enlightment===============: 
    'minutemen': { 'lowerBound': 1, 'upperBound': 50},
    'general': { 'lowerBound': 1, 'upperBound': 60},
    'cannon': { 'lowerBound': 1, 'upperBound': 80},
                    Costs:
    'general': { 'food': 200, 'metal': 200, 'wealth': 100},
    'cannon': { 'food': 200, 'timber': 100, 'metal': 200, 'wealth': 100},
    'infantry': { 'food': 300, 'metal': 300, 'wealth': 300},
    ===============Modern===============: 
    'infantry': { 'lowerBound': 1, 'upperBound': 100},
    'tank': { 'lowerBound': 1, 'upperBound': 1000},
    'fighter': { 'lowerBound': 1, 'upperBound': 10000},
    'bomber': { 'lowerBound': 1, 'upperBound': 30000},
    'icbm': { 'lowerBound': 1, 'upperBound': 100000},
                    Costs:
    'infantry': { 'food': 300, 'metal': 300, 'wealth': 300},
    'tank': { 'metal': 1000, 'oil': 1000, 'wealth': 1000},
    'fighter': { 'metal': 2000, 'oil': 2000, 'wealth': 2000},
    'bomber': { 'metal': 3000, 'oil': 3000, 'wealth': 3000},
    'icbm': { 'metal': 10000, 'oil': 10000, 'wealth': 10000},
     ===============Space===============: 
    'shocktrooper': { 'lowerBound': 1, 'upperBound': 10000},
    'lasercannon': { 'lowerBound': 1, 'upperBound': 100000},
    'starfighter': { 'lowerBound': 1, 'upperBound': 500000},
    'battlecruiser': { 'lowerBound': 1, 'upperBound': 700000}, 
    'deathstar': { 'lowerBound': 1, 'upperBound': 10000000},
                    osts:
    'shocktrooper': { 'metal': 2000, 'oil': 500, 'wealth': 2000},
    'lasercannon': { 'metal': 15000, 'oil': 15000, 'wealth': 15000},
    'starfighter': { 'metal': 25000, 'oil': 20000, 'wealth': 20000},
    'battlecruiser': { 'metal': 30000, 'oil': 30000, 'wealth': 30000},
    'deathstar': { 'metal': 100000, 'oil': 100000, 'wealth': 100000},

Buildings:
    'granary': { 'timber': 1000, 'metal': 1000, },
    'lumbermill': { 'timber': 3000, 'metal': 3000, },
    'quarry': { 'timber': 3000, 'metal': 3000, },
    'oilrig': { 'metal': 5000, 'wealth': 5000, },
    'market': { 'food': 1000, 'timber': 1000, 'wealth': 1000,},
    'university': { 'timber': 1500, 'metal': 1500, 'wealth': 1500,},

Attacking:
    Units inherit a dice roll that ranges from 1-N (this information can be found above).
    the game will take your army, and perform dice rolls, killing off units, until a player's
    army reaches 0. The winning player plunders 20% of the victims resources, plus an additional 3x
    of the plunder provided by the game. However, attacking a player and losing will result in the 
    perpetrator being counter plundered as an added risk.  

Going To The Next Age:
    After going to the next age you will have access to new units. In addition,
    new buildings have an increase rate of production Medieval[+100], Enlightment[+200],
    Modern[+300], Space[+400]. This rate of production also affects prebuilt buildings.

## Setup
To get set up, run the following in your cloned directory (Windows).
You must also have python installed and git.

pip install nextcord   
pip install pymongo  
pip install "pymongo[srv]"  
pip install python-dotenv  
pip install PurgoMalum  

## Credits
Chaney Chantipaporn  
Sarah Kwon  
Jeffrey Hwang  
Michael Tran  


## For Collaborators
In order to develop, you must ask me for the MongoDB connection string and Discord token

note to developers:
    1. camelCase variables and functions
    2. commit messages should start with [Update:, Fix:, Add:, Refactor:] and then the message

Before you start work:
1. git stash
2. git pull
3. git stash pop