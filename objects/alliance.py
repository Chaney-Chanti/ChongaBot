class Alliance:
    def __init__(self, name, creator_id, creator_username, creator_br, server_id, epoch):
        self.name = name
        self.creator_id = creator_id
        self.owner_username = creator_username
        self.time_created = epoch
        self.server_origin_id = server_id

        self.num_members = 1
        self.normal_members = [] 
        self.distinguished_members = []
        self.alliance_battle_rating = creator_br
        self.alliance_army = {}

    def add_member(self):
        pass
    def kick_member(self):
        pass
    def list_all_members(self):
        pass
    def promote_member(self):
        pass
    def send_resources(self): # cap at some amt
        pass
    def add_to_alliance_army(self): # for battling bosses
        pass
    def attack_boss(self):
        pass


    #be able to list members of your alliance and others