import nextcord
from nextcord.ext import commands
from nextcord.ui import Button, View

bot = commands.Bot(command_prefix="!")

class ExplorationButton(nextcord.ui.Button):
    def __init__(self, label, custom_id, exploration_event, callback, creator_id, view):
        self.exploration_event = exploration_event
        self.callback_func = callback
        self.exploration_view = view
        self.creator_id = creator_id
        super().__init__(custom_id=custom_id, label=label, style=1)


    async def callback(self, interaction: nextcord.Interaction):
        if interaction.user.id == self.creator_id:
            print('user.id is == to id')
            for child in self.view.children:
                child.disabled = True
            await interaction.edit(view=self.view)
            await self.callback_func(self.exploration_event, interaction)
        else:
            print('User did not create these buttons')

class ExplorationView(View):
    def __init__(self, creator_id, exploration_options, callback):
        super().__init__()
        self.exploration_options = exploration_options
        self.callback = callback
        self.clicked_button = None  # Add the clicked_button attribute
        self.creator_id = creator_id
        for i in range(len(exploration_options)):
            label = exploration_options[i]['label']
            custom_id = f'button{i}'
            button = ExplorationButton(label, custom_id, exploration_options[i], self.callback, self.creator_id , self)
            self.add_item(button)

    async def on_timeout(self):
        # This method is called when the view times out (e.g., user doesn't click any button)
        pass

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        # This method can be used to add additional checks before processing interactions
        return True




