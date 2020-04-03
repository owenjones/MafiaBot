#!/usr/bin/python3
from credentials import discordToken
from mafia import Mafia

m = Mafia()
m.run(discordToken)
