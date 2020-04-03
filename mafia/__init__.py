from gamebot import GameBot
from gamebot.decorators import guard

from mafia.game import (Game, commands)

class Mafia(GameBot) :

    name = "MafiaBot"
    activity = "Mafia"
    contact = "owen@owenjones.net"
    persist = "mafiabot.pickle"

    handlers = {
        "mafia"   : "mafia",
        "destroy" : "destroy"
    }

    mafiaChannels = {}

    @guard.onlyActiveChannel
    async def mafia(self, message, args) :
        if not message.channel.id in self.active :
            self.active[message.channel.id] = {
                "guild" : message.guild.id,
                "game"  : Game(self, message)
            }

            await self.active[message.channel.id]["game"].launch(message)

        else :
            await self.active[message.channel.id]["game"].on_message(message)

    @guard.onlyActiveChannel
    async def destroy(self, message, args) :
        if message.channel.id in self.active :
            await self.active[message.channel.id]["game"].destroy()
            del self.active[message.channel.id]["game"]
            del self.active[message.channel.id]
            await message.channel.send("The game was destroyed!")
