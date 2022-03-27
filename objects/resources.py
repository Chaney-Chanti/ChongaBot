class createResources:
    def __init__(self, userID, username, name, epoch):
        self.userID = userID
        self.username = username
        self.name = name

        self.lastClaim = epoch

        self.food = 100
        self.timber = 100
        self.metal = 100
        self.wealth = 100
        self.oil = 100
        self.knowledge = 100

        self.foodrate = 50
        self.timberrate = 50
        self.metalrate = 50
        self.oilrate = 50
        self.wealthrate = 50
        self.knowledgerate = 50