import discord
from gamebot.helpers import canManageGuild

def botOwner(command) :
    async def guard(bot, message, args) :
        if message.author.id == bot.settings["bot"]["owner"] :
            await command(bot, message, args)

    return guard

def botManager(command) :
    async def guard(bot, message, args) :
        if message.author.id == bot.settings["bot"]["owner"] or message.author.id in bot.settings["bot"]["manage"] :
            await command(bot, message, args)

    return guard

def guildOwner(command) :
    async def guard(bot, message, args) :
        if message.author == message.guild.owner :
            await command(bot, message, args)

    return guard

def guildManager(command) :
    async def guard(bot, message, args) :
        mUser = message.author.id in bot.settings[message.guild.id]["manageUsers"]
        mRole = len([ r for r in message.author.roles if r.id in bot.settings[message.guild.id]["manageRoles"] ]) > 0

        if canManageGuild(message.author, message.guild) or mUser or mRole :
            await command(bot, message, args)

    return guard

def onlyDM(command) :
    async def guard(bot, message, args) :
        if type(message.channel) == discord.DMChannel :
            await command(bot, message, args)

    return guard

def onlyChannel(command) :
    async def guard(bot, message, args) :
        if type(message.channel) == discord.TextChannel :
            await command(bot, message, args)

    return guard

def onlyActiveChannel(command) :
    async def guard(bot, message, args) :
        if message.channel.id in bot.settings[message.guild.id]["activeChannels"] :
            await command(bot, message, args)

    return guard
