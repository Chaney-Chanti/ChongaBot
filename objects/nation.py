class createNation:
    def __init__(self, userID, serverID, username, name, ability):
        self.userID = userID
        self.serverOriginID = serverID
        self.username = username

        self.name = name
        self.ability = ability

        self.numCitizens = 1
        self.population = 1

        self.granary = { 
            'level': 1,
            'built': False
        }
        self.waterMill = {
            'level': 1,
            'built': False
        }   
        self.quarry = {
            'level': 1,
            'built': False
        }   
        self.oilRig = {
            'level': 1,
            'built': False
        }   
        self.market = {
            'level': 1,
            'built': False
        }   
        self.university = {
            'level': 1,
            'built': False
        } 
        self.shield = {
            'on': False,
            'timer': 0
        }
    


 
        

                
            

        