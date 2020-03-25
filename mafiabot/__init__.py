import discord
import logging

from mafiabot.roles import mafia

# DEBUG
from pprint import pprint

"""
Perm storage:
* list of Guilds
* active channels bot has been setup in, options for these

Events:
* ready
* join Guild
* leave Guild
* receive message
"""

class MafiaBot(discord.Client) :

    guilds = []

    async def on_ready(self) :
        print('Connected as {}, active on {} guilds.'.format(self.user, len(self.guilds)))

    async def on_guild_join(self, guild) :
        pass

    async def on_guild_leave(self, guild) :
        pass

    async def on_message(self, message) :
        pass
