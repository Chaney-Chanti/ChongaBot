class CreateResources:
    def __init__(self, userID, username, name, epoch):
        self._id = userID
        self.username = username
        self.name = name

        self.last_claim = epoch

        self.food = 100
        self.timber = 100
        self.metal = 100
        self.wealth = 100
        self.oil = 100
        self.knowledge = 100

        self.food_rate = 100
        self.timber_rate = 100
        self.metal_rate = 100
        self.oil_rate = 100
        self.wealth_rate = 100
        self.knowledge_rate = 100