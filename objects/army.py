from utils import get_list_of_all_units

class CreateArmy:
    def __init__(self, userID, username, name):
        self._id = userID
        self.username = username
        self.name = name
        for unit in get_list_of_all_units():
            setattr(self, unit, 0)

        self.slinger = 10

   
 
        
