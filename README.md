# ChongaBot
Built with Nextcord and MongoDB

# Rules
### Description
Build a nation, gather resources to grow stronger, and defeat your enemies.

### How to play
Gather resources {Food, Timber, Metal, Wealth, Oil, and Knowledge}. At the start, every resource
is mined at a rate of 100. Build buildings {Granary, Water Mill, Quarry, Market, Oil Rig, University}.
to increase the rate of resource production which will also be increased based on age {Medieval(starting)[+100], Enlightment[+200], Modern[+300], Space[+400]}.
Units strength is based on a dice roll cap where units can roll from 1-n where n is the cap of the unit dice roll.
Go to the next age to have access to stronger units and more efficient resource collection. 
Attack other players and steal 20% of their resource and gain a 3x (of what you stole) bonus loot.
Battle rating reveals the strength of an empire (+25 for a win -25 for a loss).
Attacked players gain a 24 hour shield to rebuild and cannot be attacked. You may only attack players within +/-300 BR of yourself.

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