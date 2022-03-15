class createNation:
    def __init__(self, userID, serverID, username, name, ability):
        self.userID = userID
        self.serverOriginID = serverID
        self.username = username

        self.name = name
        self.ability = ability
        self.age = 'Medieval'

        self.numCitizens = 1
        self.population = 1

        self.food = 100
        self.timber = 100
        self.metal = 100
        self.wealth = 100
        self.oil = 100
        self.knowledge = 100

        self.foodRate = 50
        self.timberRate = 50
        self.metalRate = 50
        self.oilRate = 50
        self.wealthRate = 50
        self.knowledgeRate = 50

        self.granary = { 
            'level': 0,
            'built': False,
            'rateMultiplier': 0
        }
        self.waterMill = {
            'level': 0,
            'built': False
        }   
        self.quarry = {
            'level': 0,
            'built': False
        }   
        self.oilRig = {
            'level': 0,
            'built': False
        }   
        self.market = {
            'level': 0,
            'built': False
        }   
        self.university = {
            'level': 0,
            'built': False
        } 
        self.shield = {
            'on': False,
            'timer': 0
        }
    


 
        

                
            

        