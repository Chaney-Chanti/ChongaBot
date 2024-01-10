class CreateNation:
    def __init__(self, userID, server_id, username, name, epoch):
        self._id = userID
        self.server_origin_id = server_id
        self.username = username

        self.name = name
        self.age = 'ancient'
        self.battle_rating = 0    
        self.shield = 0
        self.last_explore = 0
        self.last_event = 0 
        self.num_wins = 0
        self.num_losses = 0
        self.wonder = ''
        self.motto = ''
        self.alliance = ''
        self.owned_wonders = []
        self.owned_heroes = []
        self.researched_list = [] 
        self.owned_abiltiies = [] #not used but may be needed later

        self.granary = 0
        self.lumbermill = 0
        self.quarry = 0
        self.oilrig = 0            
        self.market = 0
        self.university = 0

        self.keep = 0
        self.castle = 0
        self.fortress = 0
        self.army_base = 0
        self.planetary_fortress = 0
