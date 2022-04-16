class createNation:
    def __init__(self, userID, serverID, username, name, epoch):
        self._id = userID
        self.serverOriginID = serverID
        self.username = username

        self.name = name
        self.ability = 'none'
        self.age = 'Medieval'
        self.battleRating = 0    
        self.lastRoll = 0
        self.ownedAbiltiies = []
        self.matchHistory = {
            'attacker': '',
            'summary': '',
        }

        self.granary = { 
            'numBuildings': 0,
            'built': False,
        }
        self.lumbermill = {
            'numBuildings': 0,
            'built': False
        }   
        self.quarry = {
            'numBuildings': 0,
            'built': False
        }   
        self.oilrig = {
            'numBuildings': 0,
            'built': False
        }   
        self.market = {
            'numBuildings': 0,
            'built': False
        }   
        self.university = {
            'numBuildings': 0,
            'built': False
        } 
        self.shield = {
            'isOn': False,
            'epoch': epoch
        }