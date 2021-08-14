# Builtin
from datetime import datetime
from datetime import timedelta
from pathlib import Path
import json
# Pip
from discord.ext import commands
from AO3.utils import HTTPError
from discord import Embed
from discord import Colour
# Custom
from .Restrictor import Restrictor


# Function to create allowedIDs
def initIDs():
    return json.loads(open(idPath, "r").read())


# Function to write changes to channelIDs.json
def idWriter(newDict):
    open(idPath, "w").write(json.dumps(newDict, indent=4))


# Function to write messages to error.txt
def errorWrite(error):
    open(errorPath, "a").write(f"{datetime.now()}, {error}\n")


# Function to determine the time since last game activity
def gameActivity(lastActivity):
    return datetime.now() > (lastActivity + timedelta(seconds=gameActivityTimeout))


# Function to split a list with a set amount of items in each
def listSplit(arr, perListSize, listAmount):
    result = []
    for i in range(listAmount):
        result.append(arr[i * perListSize:i * perListSize + perListSize])
    return result


# Function to create an embed displaying the command error
async def commandDebugEmbed(ctx, error, message):
    if error:
        await ctx.channel.send(embed=Embed(title="Command Error", description=message, colour=Colour.from_rgb(0, 0, 0)))
    else:
        await ctx.channel.send(embed=Embed(title="Command Info", description=message, colour=Colour.from_rgb(0, 0, 0)))


# Handle errors
async def errorHandler(ctx, error):
    if isinstance(error, commands.CheckFailure):
        result = await restrictor.grabAllowed(ctx)
        await commandDebugEmbed(ctx, True, result)
    elif isinstance(error, commands.MissingPermissions):
        await commandDebugEmbed(ctx, True, "You do not have sufficient permission to run this command")
    elif isinstance(error, commands.NotOwner):
        await commandDebugEmbed(ctx, True, "You are not owner")
    elif isinstance(error, commands.CommandOnCooldown):
        await commandDebugEmbed(ctx, True, f"Command is on cooldown, try again in {round(error.retry_after, 2)} seconds")
    elif isinstance(error.original, HTTPError):
        await commandDebugEmbed(ctx, True, error.original)
    errorWrite(error)


# Script variables
extensions = ["Cogs.Life Is Strange", "Cogs.Fanfic", "Cogs.General", "Cogs.Miscellaneous", "Cogs.Admin"]
gameActivityTimeout = 300

# Path variables
rootDirectory = Path(__file__).parent.parent.parent
idPath = rootDirectory.joinpath("Resources").joinpath("Files").joinpath("channelIDs.json")
errorPath = rootDirectory.joinpath("DebugFiles").joinpath("error.txt")

# Restrictor class initialisation
IDs = initIDs()
commandGroups = {
    "life is strange": ["choices", "memory", "chatbot"],
    "trivia": ["trivia", "triviaLeaderboard", "triviaScore"],
    "fanfic": ["quote", "nextQuote", "searchQuote", "outline", "works"],
    "general": ["question", "connect4", "tictactoe", "hangman"],
    "bot bidness": ["stop", "channel", "botRefresh", "channelRefresh", "about"]
}
restrictor = Restrictor(IDs, commandGroups)

# Cooldown variables
superShort = 5
extraShort = 10
short = 20
medium = 45
long = 60
extraLong = 120
superLong = 300
