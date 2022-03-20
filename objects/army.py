class createArmy:
    def __init__(self, userID, username, name):
        self.userID = userID
        self.username = username
        self.name = name

        self.army = {
            'spearmen': 0,
            'archers': 0,
            'calvalry': 0,
            'trebuchets': 0,
            'minutemen': 0,
            'cannons': 0,
            'infantry': 0,
            'tanks': 0,
            'fighters': 0,
            'bombers': 0,
            'ICBM': 0,
            'laser cannons': 0,
            'battle cruisers': 0,
            'death stars': 0
        }
        
