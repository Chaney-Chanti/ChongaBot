class CreateNation:
    def __init__(self, userID, server_id, username, name, epoch):
        self._id = userID
        self.server_origin_id = server_id
        self.username = username

        self.name = name
        self.age = 'stone'
        self.battle_rating = 0    
        self.shield = 0
        self.last_explore = 0
        self.last_event = 0 
        self.wonder = ''
        self.owned_wonders = [] #can roll for wonders for bonuses
        self.motto = '' #used as a message for when you attack people
        self.alliance = '' #not used but may be needed later
        self.ability = 'none' #not used but may be needed later
        self.owned_abiltiies = [] #not used but may be needed later
        self.match_history = { #not used but may be needed later
            'attacker_username': '',
            'summary': '',
        }
        self.granary = 0
        self.lumbermill = 0
        self.quarry = 0
        self.oilrig = 0            
        self.market = 0
        self.university = 0