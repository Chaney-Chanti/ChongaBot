class createNation:
    def __init__(self, author, guild, name, ability):
        self.author = author
        self.guild = guild
        self.name = name
        self.ability = ability
        self.population = 1
        self.food = 100
        self.timber = 100
        self.metal = 100
        self.wealth = 100
        self.oil = 100
        self.knowledge = 100
        self.numCitizens = 1

        class buildUniversity:
            def __init__(self):
                self.level = 1
                self.built = False
        class buildWaterMill:
            def __init__(self):
                self.level = 1
                self.built = False
        class buildQuarry:
            def __init__(self):
                self.level = 1
                self.built = False
        class buildOilRig:
            def __init__(self):
                self.level = 1
                self.built = False
        class buildMarket:
            def __init__(self):
                self.level = 1
                self.built = False
        class hasShield:
            def __init__(self):
                self.shield = False
                self.timer = 0

                
            

        