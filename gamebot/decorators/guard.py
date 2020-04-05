import discord

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
        owner = message.author == message.guild.owner
        mAdmin = message.author.guild_permissions.administrator
        mManage = message.author.guild_permissions.manage_guild
        mUser = message.author.id in bot.settings[message.guild.id]["manageUsers"]
        mRole = len([ r for r in message.author.roles if r.id in bot.settings[message.guild.id]["manageRoles"] ]) > 0

        if owner or mAdmin or mManage or mUser or mRole :
            await command(bot, message, args)

    return guard

def onlyDM(command) :
    async def guard(bot, message, args) :
        if message.channel == discord.DMChannel :
            await command(bot, message, args)

    return guard

def onlyChannel(command) :
    async def guard(bot, message, args) :
        if message.channel == discord.TextChannel :
            await command(bot, message, args)

    return guard

def onlyActiveChannel(command) :
    async def guard(bot, message, args) :
        if message.channel.id in bot.settings[message.guild.id]["activeChannels"] :
            await command(bot, message, args)

    return guard
