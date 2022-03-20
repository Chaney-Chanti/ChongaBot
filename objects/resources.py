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

        self.foodRate = 50
        self.timberRate = 50
        self.metalRate = 50
        self.oilRate = 50
        self.wealthRate = 50
        self.knowledgeRate = 50