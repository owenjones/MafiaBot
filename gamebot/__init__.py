from datetime import datetime
import os.path
import pickle
import discord
import logging
from credentials import ownerID
from gamebot.decorators import guard
from gamebot.helpers import (hasPrefix, userInActiveGame, isDM, parseMessage, Colours)
from mafia.game import (Game, commands)

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class GameBot(discord.Client) :

    enabled = True
    settings = {}

    globalHandlers = {
        # Bot Owner
        "help"     : "cBotHelp",
        "stats"    : "cBotStats",
        "log"      : "cBotLog",
        "leave"    : "cBotLeave",
        "stop"     : "cBotStop",
        "reload"   : "cBotReload",
        "settings" : "cBotSettings"
    }

    guildHandlers = {
        # Global
        "help"  : "cGuildHelp",

        # Guild Owner / Manage Server / Guild Specific User/Role
        "settings"   : "cGuildSettings",
        "enable"     : "cGuildEnable",
        "disable"    : "cGuildDisable",
        "here"       : "cGuildHere",
        "use"        : "cGuildHere",
        "remove"     : "cGuildLeave"
    }

    active = {}

    def __init__(self) :
        super().__init__()
        if os.path.isfile(self.persist) :
            with open(self.persist, 'rb') as f :
                self.settings = pickle.load(f)

        else :
            # first run
            self.settings["bot"] = {
                "prefix" : "%%",
                "owner"  : ownerID,
                "manage" : []
            }

    async def close(self) :
        for game in self.active :
            await self.active[game]["game"].destroy()

        self.saveSettings()
        await super().close()

    def generateSettings(self, gID) :

        self.settings[gID] = {
            "prefix"            : "!",
            "manageUsers"       : [ ],
            "manageRoles"       : [ ],
            "activeChannels"    : [ ],
            "winCommand"        : None,
            "disabled"          : False
        }

    def saveSettings(self) :
        with open(self.persist, 'wb') as f :
            pickle.dump(self.settings, f, pickle.HIGHEST_PROTOCOL)

    async def updatePresenceCount(self) :
        activity = discord.Game(
            "{} in {} server{}".format(
                self.activity,
                len(self.guilds),
                "s" if len(self.guilds) > 1 else ""
            )
        )

        await self.change_presence(status=discord.Status.online, activity=activity)

    async def sendGuildIntro(self, guild) :
        self.generateSettings(guild.id)

        try :
            await guild.owner.send('Thanks for inviting {0} into {1.name}! The default prefix this bot uses to listen for instructions in your Guild is `!`, to change this prefix message `!settings prefix <prefix>` from within your Guild.'.format(self.name, guild))

        except discord.errors.Forbidden :
            pass

    async def on_ready(self) :
        for guild in self.guilds :
            if guild.id not in self.settings :
                await self.sendGuildIntro(guild)

        await self.updatePresenceCount()

        logger.info('{} launched, active on {} guilds'.format(self.name, len(self.guilds)))

    async def on_guild_join(self, guild) :
        logger.info("Joined guild {}".format(guild.name))
        await self.sendGuildIntro(guild)
        await self.updatePresenceCount()

    async def on_guild_remove(self, guild) :
        logger.info("Left guild {}".format(guild.name))

        if guild.id in self.settings :
            del self.settings[guild.id]

        await self.updatePresenceCount()

    async def on_message(self, message) :
        globalPrefix = self.settings["bot"]["prefix"]
        activeGame = userInActiveGame(message.author.id, self.active)

        if message.guild and message.guild.id in self.settings :
            # message send within a guild (so in a channel)
            guildPrefix = self.settings[message.guild.id]["prefix"]

        elif (isDM(message) and activeGame) :
            # message sent in DM by somebody in an active game - FUTURE: handle guild commands in DMs too
            guildPrefix = self.settings[self.active[activeGame]["guild"]]["prefix"]

        else :
            guildPrefix = False

        if guildPrefix and hasPrefix(message, guildPrefix) :
            guildMatched = await self.handleCommand(message, guildPrefix, self.guildHandlers)
            gameMatched = await self.handleCommand(message, guildPrefix, self.handlers)

            if not (guildMatched or gameMatched) :
                sentInDMWithActiveGame = activeGame and isDM(message)
                recognisedGuild = message.guild and message.guild.id in self.settings
                sentInActiveChannel = recognisedGuild and message.channel.id in self.settings[message.guild.id]["activeChannels"]
                sentInMafiaChannel = message.channel.id in self.mafiaChannels

                if sentInDMWithActiveGame or (recognisedGuild and (sentInActiveChannel or sentInMafiaChannel)) :
                    if sentInDMWithActiveGame :
                        id = activeGame
                    elif sentInMafiaChannel :
                        id = self.mafiaChannels[message.channel.id] # map mafia channel to game
                    else :
                        id = message.channel.id

                    if id in self.active :
                        await self.active[id]["game"].on_message(message)

        if hasPrefix(message, globalPrefix) :
            await self.handleCommand(message, globalPrefix, self.globalHandlers)

    async def handleCommand(self, message, prefix, handlers) :
        command, args = parseMessage(message, prefix)

        if command in handlers and handlers[command] :
            handle = getattr(self, handlers[command])
            await handle(message, args)
            return True

        else :
            return False

    async def leaveGuild(self, guild) :
        await guild.leave()
        del self.settings[guild.id]

    @guard.botManager
    async def cBotHelp(self, message, args) :
        pass # TODO

    @guard.botManager
    async def cBotStats(self, message, args) :
        embed = discord.Embed(
            title="{}".format(self.name),
            description="Currently running on {0} Guild{1} ({2}), with {3} active game{4}".format(
                len(self.guilds),
                "s" if len(self.guilds) != 1 else "",
                ", ".join([g.name for g in self.guilds]),
                len(self.active),
                "s" if len(self.active) != 1 else "",
            ),
            colour=Colours.LUMINOUS_VIVID_PINK
        )
        await message.channel.send(embed=embed) # TODO

    @guard.botManager
    async def cBotLog(self, message, args) :
        pass

    @guard.botManager
    @guard.onlyChannel
    async def cBotLeave(self, message, args) :
        await message.channel.send("Leaving {}".format(message.guild.name))
        await self.leaveGuild(message.guild)

    @guard.botManager
    async def cBotStop(self, message, args) :
        await self.close()

    @guard.botManager
    async def cBotReload(self, message, args) :
        # TODO
        # await self.disconnect()
        # self.saveSettings()
        # await self.connect()
        pass

    @guard.botManager
    async def cBotSettings(self, message, args) :
        if len(args) > 1 :
            option = args[1]

            if option == "prefix" and len(args) > 2 :
                self.settings["bot"]["prefix"] = args[2]
                await message.channel.send("Prefix changed to {}".format(args[2]))

            elif option == "adduser" and len(message.mentions) > 0 :
                self.settings["bot"]["manage"].append(message.mentions[0].id)

            elif option == "removeuser" and len(message.mentions) > 0 and message.mentions[0].id in self.settings["bot"]["manageUsers"]:
                self.settings["bot"]["manage"].remove(message.mentions[0].id)

        await message.channel.send(self.settings)

    # Guild Commands
    async def cGuildHelp(self, message, args) :
        pass

    @guard.guildManager
    async def cGuildSettings(self, message, args) :
        if len(args) > 1 :
            option = args[1]

            if option == "prefix" and len(args) > 2 :
                self.settings[message.guild.id]["prefix"] = args[2]
                await message.channel.send("Prefix changed to {}".format(args[2]))

            elif option == "adduser" and len(message.mentions) > 0 :
                self.settings[message.guild.id]["manageUsers"].append(message.mentions[0].id)

            elif option == "removeuser" and len(message.mentions) > 0 and message.mentions[0].id in self.settings[message.guild.id]["manageUsers"]:
                self.settings[message.guild.id]["manageUsers"].remove(message.mentions[0].id)

            elif option == "addrole" and len(message.role_mentions) > 0 :
                self.settings[message.guild.id]["manageRoles"].append(message.role_mentions[0].id)

            elif option == "removerole" and len(message.role_mentions) > 0 and message.role_mentions[0].id in self.settings[message.guild.id]["manageRoles"]:
                self.settings[message.guild.id]["manageRoles"].remove(message.role_mentions[0].id)

        await message.channel.send(self.settings[message.guild.id])

    @guard.guildManager
    def cGuildEnable(self, message, args) :
        self.settings[message.guild.id]["disabled"] = False

    @guard.guildManager
    def cGuildDisable(self, message, args) :
        self.settings[message.guild.id]["disabled"] = True

    @guard.guildManager
    async def cGuildHere(self, message, args) :
        if(args[0] == "use") :
            channel = message.channel_mentions[0]
        else :
            channel = message.channel

        if channel :
            if channel.id in self.settings[message.guild.id]["activeChannels"] :
                await message.channel.send("MafiaBot is already active in {0.mention}".format(channel))
            else :
                self.settings[message.guild.id]["activeChannels"].append(channel.id)
                await message.channel.send("MafiaBot now active in {0.mention} - please check I have `manage_channels` permissions for this channel category or I won't be able to work :cry:".format(channel))

    @guard.guildManager
    async def cGuildLeave(self, message, args) :
        if message.channel.id in self.settings[message.guild.id]["activeChannels"] :
            self.settings[message.guild.id]["activeChannels"].remove(message.channel.id)
            await message.channel.send("No longer active in {0.mention}".format(message.channel))
