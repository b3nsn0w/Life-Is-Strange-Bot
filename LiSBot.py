# Builtin
import logging
import os
# Pip
from discord.ext import commands
from discord import Game
from discord import Status
# Custom
from Utils import Utils
import Config

# Initialise discord variables
token = Config.token
client = commands.Bot(command_prefix="$", description="A LiS Discord Bot")

# Path variables
rootDirectory = os.path.join(os.path.dirname(__file__))
logPath = os.path.join(rootDirectory, "BotFiles", "lisBot.log")


# Run when discord bot has joined a guild
@client.event
async def on_guild_join(guild):
    tempDict = Utils.allowedIDs
    for key, value in tempDict.items():
        value[str(guild.id)] = [-1]
    Utils.idWriter(tempDict)


# Run when discord bot has left a guild
@client.event
async def on_guild_remove(guild):
    tempDict = Utils.allowedIDs
    for key, value in tempDict.items():
        del value[str(guild.id)]
    Utils.idWriter(tempDict)


# Run when discord bot has started
@client.event
async def on_ready():
    # Get channel ID for test channel
    channel = client.get_channel(817807544482922496)
    # Change the presence to show the help command
    await client.change_presence(status=Status.online, activity=Game(name=f"{client.command_prefix}help"))
    # Send message to user signalling that the bot is ready
    await channel.send("Running")


# Setup automatic logging for debugging
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename=logPath, encoding="utf-8", mode="a")
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s'))
logger.addHandler(handler)

# Load all extensions (filenames for the exterior cogs)
for extension in Utils.extensions:
    client.load_extension(extension)

# Start discord bot
client.run(token)