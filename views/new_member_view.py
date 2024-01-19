import nextcord
from nextcord.ext import commands
from nextcord.ui import Button, View

bot = commands.Bot(command_prefix="!")

#controller should send data to view
#if member is accepted: msg them back, add them to alliance
#else msg them back
class AllianceAcceptanceButton(nextcord.ui.Button):
    def __init__(self, label, custom_id, callback, creator_id, view):
        self.callback_func = callback
        self.exploration_view = view
        self.creator_id = creator_id
        super().__init__(custom_id=custom_id, label=label, style=1)

    async def callback(self, interaction: nextcord.Interaction):
        for child in self.view.children:
            child.disabled = True
        await interaction.edit(view=self.view)
        await self.callback_func(interaction)

class AllianceAcceptanceView(View):
    def __init__(self, accept_label, deny_label, member_to_join_id, alliance_owner_id, 
                 sovereigns, accept_callback, deny_callback):
        super().__init__()
        self.accept_callback = accept_callback
        self.deny_callback = deny_callback
        self.alliance_owner_id = alliance_owner_id
        self.member_id = member_to_join_id
        accept_id = 'accept_button'
        deny_id = 'deny_button'
        accept_button = AllianceAcceptanceButton(accept_label, accept_id, self.accept_callback, self.member_id, self)
        deny_button = AllianceAcceptanceButton(deny_label, deny_id, self.deny_callback, self.member_id, self)
        self.add_item(accept_button)
        self.add_item(deny_button)

    async def on_timeout(self):
        # This method is called when the view times out (e.g., user doesn't click any button)
        pass

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        # This method can be used to add additional checks before processing interactions
        return True