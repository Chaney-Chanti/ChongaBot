class createNation:
    def __init__(self, userID, serverID, username, name, epoch):
        self._id = userID
        self.serverOriginID = serverID
        self.username = username

        self.name = name
        self.ability = 'none'
        self.age = 'Medieval'
        self.battleRating = 0    
        self.shield = epoch              

        self.numCitizens = 0

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
    


 
        

                
            

        