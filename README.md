# MafiaBot
A bot that plays the card game *Mafia* (also known as *Werewolf*) on Discord.

### [Invite the bot to your server](https://discordapp.com/oauth2/authorize?scope=bot&client_id=690010035086164041)

## Commands to play Mafia
The default prefix the bot uses in a server is `!`, this can be changed using the settings command.

* **!mafia** - starts a new game of Mafia
* **!destroy** - kills a current running game of Mafia
* **!why** - find out what the bot is currently waiting for
* **!who** - find out who's in the current game

The bot will prompt with other commands during the game:

* **!join** - join a game (before it's started)
* **!start** - start the game (once enough players are in)
* **!leave** - leave the current game (can be done at any point in the game)
* **!choose *number*** - used by some of the roles to choose the player they wish to action
* **!accuse *@user*** - used by villagers to accuse others of being in the Mafia
* **!skip** - used by villagers to stay quiet

## Administering the bot in your server
### Control Commands
These can initially only be run by the server owner or members with the `Administrator` or `Manage Server` permissions granted. You can give other members or roles the ability to control the bot using the settings command.

* **!here** - to mark the channel(s) MafiaBot can use to start games in
* **!use #channel** - works like `!here`, but can be run from outside the channel you want games in
* **!remove** - stops MafiaBot from running in the current channel
* **!settings** - see the raw saved settings
* **!settings prefix *prefix*** - changes the prefix to `prefix`
* **!settings adduser *@user*** - allows the user `user` to adminster the bot
* **!settings removeuser *@user*** - removes user from list
* **!settings addrole *@role*** - allows any user with the role `role` to adminster the bot
* **!settings removerole *@role*** - removes role from list

If you want the bot to leave your server at any point, just kick it.

### Required Permissions
In order to run correctly the bot needs the following permissions set for it, or it won't run:

* **Manage Channel** - on the channel category the bot is in, this is so it can add/remove the extra channels used to communicate with the Mafia during the game
* **Read Messages** - in the channels being used to run the game, and any other channels you wish to be able to send control commands from
* **Send Messages** - as above
* **Embed Links** - on the channel category the bot is in, used to send messages with rich embeds

## Running the bot yourself
You can run the bot yourself by cloning this repo, renaming `credentials.example.py` to `credentials.py` and adding a bot token and your user ID, then running `main.py`.

There are a few additional commands bot owners can run, the default prefix is `%%`:

* **%%stats** - gives some info on how many servers and active games the bot is currently running
* **%%leave** - removes the bot from the server the command is run on
* **%%logset** - mark the current channel as the place to output any internal Python exceptions
* **%%exception** - forces an exception (to test the above)
* **%%permissions** - for debug, tells you which of the required permissions are missing from the current channel (can be called by a server manager)
* **%%settings** - see the raw saved settings
* **%%settings prefix *prefix*** - changes the bot control prefix to `prefix`
* **%%settings adduser *@user*** - adds `user` to the list of people allowed to manage the bot
* **%%settings removeuser *@user*** - removes `user` from the list

<!--* **%%log *n*** - returns the last `n` lines of the bot log (up to the maximum Discord message length)-->
