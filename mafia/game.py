import math
import random
from enum import Enum
from collections import Counter
import asyncio

import discord

from gamebot.helpers import parseMessage, userInActiveGame, isDM, Colours

commands = ["join", "leave", "start", "choose", "purge", "why", "who"]


class State(Enum):
    START = 1
    ROUNDSLEEP = 2
    ROUNDPURGE = 3
    END = 4


class Win(Enum):
    VILLAGERS = 1
    MAFIA = 2


class Game:

    lock = None
    bot = None
    guild = None
    channel = None

    minPlayers = 5
    maxPlayers = 15

    # Game Object Methods
    def __init__(self, bot, message):
        self.lock = asyncio.Lock()
        self.bot = bot
        self.guild = message.guild
        self.channel = message.channel

        self.settings = self.bot.settings[self.guild.id]
        self.prefix = self.settings["prefix"]

        random.seed()

        self.setInitialState()

    def setInitialState(self):
        self.mafiaChannel = None
        self.players = []
        self.villagers = []
        self.mafia = []
        self.doctor = None
        self.detective = None
        self.round = 1
        self.mafiaChoose = {}
        self.roundKill = None
        self.roundKillSkip = None
        self.roundSave = None
        self.lastRoundSave = None
        self.roundDetect = None
        self.roundPurge = {}
        self.state = State.START

    async def destroy(self):
        await self.removeMafiaChannel()

    async def launch(self, message):
        await message.channel.send(
            embed=discord.Embed(
                title="Mafia :dagger:",
                description="Welcome to the village of Upper Lowerstoft, it's normally quite a peaceful place but recently something *a bit sinister* has been happening when everyone's tucked up in bed...\n\nTo join the game message `{0}join`, then `{0}start` when there are at least {1} players. To leave the game at any point message `{0}leave`.".format(
                    self.prefix, self.minPlayers
                ),
                colour=Colours.DARK_RED,
            )
        )

    async def on_message(self, message):
        async with self.lock:
            # TODO: split this into separate functions!
            command, args = parseMessage(message, self.prefix)

            if (
                command == "join"
                and message.channel == self.channel
                and self.state == State.START
            ):
                if self.hasUser(message.author.id):
                    await message.channel.send("You're already in the game!")
                elif userInActiveGame(message.author.id, self.bot.active):
                    await message.channel.send("You're already in a game elsewhere!")
                else:
                    try:
                        embed = discord.Embed(
                            description="Welcome to Upper Lowerstoft, we hope you have a peaceful visit.\n\nDuring the game I will send you messages here, if you need to leave at any point message `{}leave` in the game channel.".format(
                                self.prefix
                            ),
                            colour=Colours.DARK_BLUE,
                        )
                        await message.author.send(embed=embed)

                        self.players.append(message.author)
                        if len(self.players) < self.minPlayers:
                            l = "{} players of {} needed".format(
                                len(self.players), self.minPlayers
                            )
                        else:
                            l = "{} players of maximum {}".format(
                                len(self.players), self.maxPlayers
                            )
                        await message.channel.send(
                            "{} joined the game ({})".format(message.author.mention, l)
                        )

                    except discord.errors.Forbidden:
                        await self.channel.send(
                            "{0.mention} you have your DMs turned off - the game doesn't work if I can't send you messages :cry:".format(
                                message.author
                            )
                        )

            elif command == "leave" and message.channel == self.channel:
                if message.author in self.players:
                    await self.channel.send(
                        "{} left the game".format(message.author.mention)
                    )

                    if self.state in [State.ROUNDSLEEP, State.ROUNDPURGE]:
                        await self.kill(message.author)
                        win = self.checkWinConditions()

                        if win:
                            self.endGame(win)

                    else:
                        self.players.remove(message.author)

            elif (
                command == "start"
                and message.channel == self.channel
                and self.state == State.START
            ):
                if message.author in self.players and message.channel == self.channel:
                    if len(self.players) < self.minPlayers:
                        await self.channel.send(
                            "There aren't enough players ({} of {} needed)".format(
                                len(self.players), self.minPlayers
                            )
                        )

                    else:
                        await self.startGame()

            elif command == "choose" and self.state == State.ROUNDSLEEP:

                def IDFromArg(args):
                    if len(args) > 1:
                        try:
                            return int(args[1])
                        except ValueError:
                            return False

                if (
                    message.author in self.mafia
                    and message.channel == self.mafiaChannel
                ):
                    id = IDFromArg(args)

                    if not message.author.id in self.mafiaChoose and id:
                        if (id < 1) or (id > len(self.players)):
                            await message.channel.send(
                                "{} - that isn't a valid choice".format(
                                    message.author.mention
                                )
                            )
                        else:
                            self.mafiaChoose[message.author.id] = id
                            await message.channel.send(
                                "{} - choice submitted".format(message.author.mention)
                            )

                            if len(self.mafiaChoose) == len(self.mafia):
                                chosen, count = Counter(
                                    self.mafiaChoose.values()
                                ).most_common(1)[0]
                                if count >= (math.floor(len(self.mafia) / 2) + 1):
                                    self.roundKill = self.players[chosen - 1]
                                    await message.channel.send(
                                        "{} has been marked for death".format(
                                            self.roundKill.display_name
                                        )
                                    )
                                else:
                                    await message.channel.send(
                                        "You couldn't come to an agreement, nobody will be killed this round"
                                    )
                                    self.roundKillSkip = True

                elif message.author == self.doctor and isDM(message):
                    id = IDFromArg(args)

                    if id and ((id > 0) and (id <= len(self.players))):
                        save = self.players[id - 1]
                        if save != self.lastRoundSave:
                            self.roundSave = save
                            await message.channel.send(
                                "Choice submitted - {} will be saved".format(
                                    self.roundSave.display_name
                                )
                            )

                        else:
                            await message.channel.send(
                                "You can't save the person two nights running!"
                            )
                    else:
                        await message.channel.send("That isn't a valid choice!")

                elif message.author == self.detective and isDM(message):
                    id = IDFromArg(args)

                    if id and ((id > 0) and (id <= len(self.players))):
                        self.roundDetect = self.players[id - 1]
                        await message.channel.send(
                            "Choice submitted - {} will be investigated".format(
                                self.roundDetect.display_name
                            )
                        )
                    else:
                        await message.channel.send("That isn't a valid choice!")

                await self.testRoundContinue()

            elif (
                command == "accuse"
                and message.channel == self.channel
                and self.state == State.ROUNDPURGE
            ):
                if message.author in self.players:
                    if message.mentions and (len(message.mentions) == 1):
                        if message.mentions[0] in self.players:
                            self.roundPurge[message.author.id] = message.mentions[0]
                            left = len(self.players) - len(self.roundPurge)
                            await message.channel.send(
                                "{0.mention} accused {1.display_name} - {2} left to decide".format(
                                    message.author, message.mentions[0], left
                                )
                            )

                            if len(self.roundPurge) == len(self.players):
                                await self.purge()

                        else:
                            await self.channel.send(
                                "{0.mention} isn't in the game!".format(
                                    message.mentions[0]
                                )
                            )
                    else:
                        await self.channel.send(
                            "{0.mention} that wasn't a valid choice".format(
                                message.author
                            )
                        )

            elif (
                command == "skip"
                and message.channel == self.channel
                and self.state == State.ROUNDPURGE
            ):
                if message.author in self.players:
                    self.roundPurge[message.author.id] = False
                    left = len(self.players) - len(self.roundPurge)
                    await message.channel.send(
                        "{} skipped - {} left to decide".format(
                            message.author.mention, left
                        )
                    )

                    if len(self.roundPurge) == len(self.players):
                        await self.purge()

            elif command == "restart" and self.state == State.END:
                self.setInitialState()
                await self.launch(message)

            elif command == "why" and message.channel == self.channel:
                if self.state == State.START:
                    if len(self.players) < self.minPlayers:
                        await self.channel.send(
                            embed=discord.Embed(
                                description="I'm waiting for more players to join, use `{0}join` if you want to play".format(
                                    self.prefix
                                ),
                                colour=Colours.BLUE,
                            )
                        )

                    else:
                        await self.channel.send(
                            embed=discord.Embed(
                                description="I'm waiting for someone to start the game, use `{0}start` when you're ready to begin".format(
                                    self.prefix
                                ),
                                colour=Colours.BLUE,
                            )
                        )

                elif self.state == State.ROUNDSLEEP:
                    waiting = []

                    if not (self.roundKill or self.roundKillSkip):
                        waiting.append("the Mafia")

                    if self.doctor and not self.roundSave:
                        waiting.append("the doctor")

                    if self.detective and not self.roundDetect:
                        waiting.append("the detective")

                    await self.channel.send(
                        embed=discord.Embed(
                            description="I'm waiting for the following to make their choices: {}".format(
                                ", ".join(waiting)
                            ),
                            colour=Colours.BLUE,
                        )
                    )

                elif self.state == State.ROUNDPURGE:
                    remaining = len(self.players) - len(self.roundPurge)
                    players = ", ".join(
                        [
                            "{0.mention}".format(p)
                            for p in self.players
                            if p.id not in self.roundPurge
                        ]
                    )
                    plural = "players" if remaining > 1 else "player"

                    await self.channel.send(
                        embed=discord.Embed(
                            description="I'm waiting for the village to discuss - {0} {1} left to make a decision ({2})".format(
                                remaining, plural, players
                            ),
                            colour=Colours.BLUE,
                        )
                    )

                elif self.state == State.END:
                    await self.channel.send(
                        embed=discord.Embed(
                            description="The game has ended, use `{0}restart` for a new game".format(
                                self.prefix
                            ),
                            colour=Colours.BLUE,
                        )
                    )

            elif command == "who" and self.state in [
                State.START,
                State.ROUNDSLEEP,
                State.ROUNDPURGE,
            ]:
                if len(self.players) > 0:
                    are = "are" if len(self.players) > 1 else "is"
                    players = " ".join(["{0.mention}".format(m) for m in self.players])
                    await self.channel.send(
                        embed=discord.Embed(
                            description="{} {} in the game".format(players, are),
                            color=Colours.DARK_BLUE,
                        )
                    )

                else:
                    await self.channel.send(
                        embed=discord.Embed(
                            description="Nobody is in the game yet",
                            color=Colours.DARK_BLUE,
                        )
                    )

    # Game Helpers
    def checkWinConditions(self):
        if len(self.mafia) >= len(self.villagers):
            return Win.MAFIA
        elif len(self.mafia) == 0:
            return Win.VILLAGERS
        else:
            return False

    def hasUser(self, uID):
        count = len([u for u in self.players if u.id == uID])
        return count > 0

    def allocateRoles(self):
        nMafia = (
            1 if len(self.players) <= 5 else (math.floor(len(self.players) / 5) + 1)
        )

        random.shuffle(self.players)

        self.mafia = self.players[0:nMafia]
        self.villagers = self.players[nMafia:]

        self.doctor = self.villagers[0]
        self.detective = self.villagers[1] if len(self.players) > 5 else None

        random.shuffle(self.players)

    async def makeMafiaChannel(self):
        if not self.mafiaChannel:
            mafiaPermissions = discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            )

            overwrites = {
                self.guild.default_role: discord.PermissionOverwrite(
                    read_messages=False
                ),
                self.guild.me: discord.PermissionOverwrite(
                    manage_channels=True,
                    manage_permissions=True,
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                ),
            }

            for m in self.mafia:
                overwrites[m] = mafiaPermissions

            try:
                self.mafiaChannel = await self.channel.category.create_text_channel(
                    "the-mafia", overwrites=overwrites
                )
                self.bot.mafiaChannels[self.mafiaChannel.id] = self.channel.id
                return True

            except discord.errors.Forbidden:
                await self.channel.send(
                    ":exploding_head: I can't continue because I don't have permission to create text channels in this channel category - did you remove the permission?"
                )
                await self.endGame()
                return False

    async def removeMafiaChannel(self):
        if self.mafiaChannel:
            del self.bot.mafiaChannels[self.mafiaChannel.id]
            await self.mafiaChannel.delete()
            self.mafiaChannel = None

    async def removeFromMafia(self, player):
        self.mafia.remove(player)
        permissions = discord.PermissionOverwrite(
            read_messages=False, send_messages=False
        )
        await self.mafiaChannel.set_permissions(player, overwrite=permissions)

    def makePlayerListEmbed(self):
        return discord.Embed(
            description="\n".join(
                [
                    "{0} - {1}".format((n + 1), v.display_name)
                    for n, v in enumerate(self.players)
                ]
            ),
            colour=Colours.PURPLE,
        )

    async def kill(self, player, purge=False):
        method = "purged" if purge else "killed"

        if player in self.mafia:
            role = "in the **mafia**"
            await self.removeFromMafia(player)

        elif player == self.doctor:
            role = "the **doctor**"
            self.doctor = None
            self.villagers.remove(player)

        elif player == self.detective:
            role = "the **detective**"
            self.detective = None
            self.villagers.remove(player)

        elif player in self.villagers:
            role = "a **villager**"
            self.villagers.remove(player)

        else:
            return

        embed = discord.Embed(
            title="{} has been {}!".format(player.display_name, method),
            description="They were {}".format(role),
            colour=Colours.DARK_RED,
        )
        await self.channel.send(embed=embed)

        self.players.remove(player)

        await self.testRoundContinue()

    # Game Flow
    async def startGame(self):
        self.allocateRoles()
        created = await self.makeMafiaChannel()

        if created:
            await self.sendIntros()
            await self.startRound()

    async def continueGame(self):
        self.lastRoundSave = self.roundSave
        self.mafiaChoose = {}
        self.roundKill = None
        self.roundKillSkip = None
        self.roundSave = None
        self.roundDetect = None
        self.roundPurge = {}

        self.round += 1
        await self.startRound()

    async def endGame(self, win=False):
        self.state = State.END

        if win == Win.VILLAGERS:
            winners = " ".join(["{0.mention}".format(m) for m in self.villagers])
            embed = discord.Embed(
                description="The villagers ({}) have won!\n\nMessage `{}restart` to play again".format(
                    winners, self.prefix
                ),
                colour=Colours.DARK_GREEN,
            )

        elif win == Win.MAFIA:
            winners = " ".join(["{0.mention}".format(m) for m in self.mafia])
            embed = discord.Embed(
                description="The Mafia ({}) have won!\n\nMessage `{}restart` to play again".format(
                    winners, self.prefix
                ),
                colour=Colours.DARK_RED,
            )

        else:
            embed = discord.Embed(
                description="The game has had to end for some reason :cry:\n\nMessage `{}restart` to start a new game".format(
                    self.prefix
                ),
                colour=Colours.BLUE,
            )

        await self.removeMafiaChannel()
        await self.channel.send(embed=embed)

        if self.settings["winCommand"]:
            await self.channel.send(
                "{} {}".format(self.settings["winCommand"], winners)
            )

    # Round Flow
    async def startRound(self):
        embed = discord.Embed(
            title="Round {}".format(self.round),
            description="As the sun sets, the villagers head to bed for an uneasy nights sleep",  # make list of these to work through as a story
            colour=Colours.PURPLE,
        )
        await self.channel.send(embed=embed)
        self.state = State.ROUNDSLEEP
        await self.sendPrompts()

    async def sendIntros(self):
        mafia = "".join(["{0.mention} ".format(m) for m in self.mafia])
        await self.mafiaChannel.send(
            "{} - you are the mafia, each night you get to mark one villager for death!".format(
                mafia
            )
        )

        for v in self.villagers:
            if v in self.mafia:
                await v.send(
                    "You're in the mafia, each night you get to mark one villager for death! Look for `#the-mafia` channel to make your choice."
                )
            elif v == self.doctor:
                await v.send(
                    "You're the doctor, each night you get to pick one villager to save - you can't save the same person two nights in a row"
                )

            elif v == self.detective:
                await v.send(
                    "You're the detective, each night you get to pick one villager to investigate and find out if they're in the mafia"
                )

            else:
                await v.send(
                    "You're a villager, keep your wits about you there are mafia on the loose!"
                )

    async def sendPrompts(self):
        mafiaPrompt = "Each reply with `{0}choose number` (e.g. `{0}choose 1`) to choose the player you wish to mark for death - you need to come to an agreement as a group, if there's no clear choice then nobody will be marked, so you may want to discuss your choice first!".format(
            self.prefix
        )
        doctorPrompt = "Reply with `{0}choose number` (e.g. `{0}choose 1`) to choose the player you wish to save".format(
            self.prefix
        )
        detectivePrompt = "Reply with `{0}choose number` (e.g. `{0}choose 1`) to choose the player you wish to investigate".format(
            self.prefix
        )

        embed = self.makePlayerListEmbed()
        await self.mafiaChannel.send(mafiaPrompt, embed=embed)

        if self.doctor:
            await self.doctor.send(doctorPrompt, embed=embed)

        if self.detective:
            await self.detective.send(detectivePrompt, embed=embed)

    async def testRoundContinue(self):
        if (
            (self.state == State.ROUNDSLEEP)
            and (self.roundKill or self.roundKillSkip)
            and (not self.doctor or self.roundSave)
            and (not self.detective or self.roundDetect)
        ):
            await self.summariseRound()

    async def summariseRound(self):
        summary = discord.Embed(
            title="Wakey wakey",
            description="As the village wakes, it's inhabitants cautiously step outside to find out what happened during the night...",
            colour=Colours.PURPLE,
        )

        if self.roundKillSkip:
            summary.add_field(
                name=":person_shrugging:",
                value="The Mafia didn't choose anybody to kill this time around",
                inline=False,
            )
            kill = False

        elif self.roundKill:
            summary.add_field(
                name=":dagger:",
                value="The Mafia chose to kill {}".format(self.roundKill.mention),
                inline=False,
            )

            if self.roundSave == self.roundKill:
                summary.add_field(
                    name=":syringe:",
                    value="The doctor managed to save them in time!",
                    inline=False,
                )
                kill = False

            elif self.doctor:
                summary.add_field(
                    name=":skull_crossbones:",
                    value="The doctor was unable to save them",
                    inline=False,
                )
                kill = True

            else:
                # the doctor has been killed
                kill = True

        if self.detective and self.roundDetect:
            if self.roundDetect in self.mafia:
                summary.add_field(
                    name=":detective:",
                    value="The detective found a member of the mafia",
                    inline=False,
                )
                await self.detective.send(
                    embed=discord.Embed(
                        description="Correct - {} is in the mafia!".format(
                            self.roundDetect.display_name
                        ),
                        colour=Colours.DARK_RED,
                    )
                )
            else:
                summary.add_field(
                    name=":detective:",
                    value="The detective didn't find a member of the mafia",
                    inline=False,
                )
                await self.detective.send(
                    embed=discord.Embed(
                        description="Incorrect - {} is not in the mafia!".format(
                            self.roundDetect.display_name
                        ),
                        colour=Colours.DARK_GREEN,
                    )
                )

        await self.channel.send(embed=summary)

        if kill:
            await self.kill(self.roundKill)
            win = self.checkWinConditions()

            if win:
                await self.endGame(win)

        if self.state != State.END:
            await self.moveToPurge()

    async def moveToPurge(self):
        self.state = State.ROUNDPURGE

        if self.roundKillSkip:
            text = "Although the Mafia didn't strike last night, the villagers are still on edge and a village meeting is called..."

        elif self.roundKill == self.roundSave:
            text = "Tensions are running high after last nights attempted murder, the villagers gather to discuss..."

        else:
            text = "Horrified at last nights murder, the villagers gather to discuss..."

        left = " ".join(["{0.mention}".format(m) for m in self.players])

        embed = discord.Embed(
            description="{0}\n\nIf you're suspicious of a player mention them using `{2}accuse` to accuse them of being in the Mafia, or use `{2}skip` to stay quiet. At least half the village must accuse someone for them to be purged.\n\n{1} are still in the game".format(
                text, left, self.prefix
            ),
            colour=Colours.DARK_ORANGE,
        )

        await self.channel.send(embed=embed)

    async def purge(self):
        chosen, count = Counter(self.roundPurge.values()).most_common(1)[0]
        if chosen != False and count >= (math.ceil(len(self.players) / 2)):
            await self.channel.send(
                embed=discord.Embed(
                    description="The village has agreed that {} should be purged".format(
                        chosen.display_name
                    ),
                    colour=Colours.DARK_RED,
                )
            )

            await self.kill(chosen, True)
            win = self.checkWinConditions()

            if win:
                await self.endGame(win)

            else:
                await self.continueGame()
        else:
            await self.channel.send(
                embed=discord.Embed(
                    description="The village couldn't come to an agreement, nobody is purged today",
                    colour=Colours.DARK_GREEN,
                )
            )

            await self.continueGame()
