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

        self.foodrate = 100
        self.timberrate = 100
        self.metalrate = 100
        self.oilrate = 100
        self.wealthrate = 100
        self.knowledgerate = 100