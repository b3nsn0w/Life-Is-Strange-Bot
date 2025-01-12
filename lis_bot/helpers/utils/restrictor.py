from __future__ import annotations

# Builtin
from typing import Union

# Pip
from discord import TextChannel, VoiceChannel
from discord.ext import bridge


# Restrictor class to switch between different embeds
class Restrictor:
    # Initialise variables
    def __init__(self, commandGroups: dict[str, list[str]]) -> None:
        self.commandGroups = commandGroups
        self.IDs = None
        self.bot = None

    # Function to get the allowed channels for a command
    def getAllowed(
        self, ctx: Union[bridge.BridgeApplicationContext, bridge.BridgeExtContext],
    ) -> Union[list[int], None]:
        for key, value in self.commandGroups.items():
            if str(ctx.command) in value:
                allowedChannels = self.IDs[str(ctx.guild.id)][key]
                if allowedChannels[0] != -1:
                    return allowedChannels
        return None

    # Function to set the bot variable
    async def setBot(self, bot: bridge.Bot) -> None:
        self.bot = bot
        self.IDs = await self.getIDs()

    # Function to get IDs from the database
    async def getIDs(self) -> dict[str, dict[str, list[int]]]:
        # Import utils to avoid a circular import
        from lis_bot.helpers.utils.utils import database

        tempDict = {}
        for guild in self.bot.guilds:
            result = await database.fetch(
                "SELECT guildID, lifeIsStrangeID, triviaID, fanficID, imageID, radioTextID, radioVoiceID, botBidnessID FROM settings WHERE guildID = ?",
                (guild.id,),
            )
            result = result[0]
            tempDict[str(guild.id)] = {
                "life is strange": [
                    int(channelID) for channelID in result[1].split(",")
                ],
                "trivia": [int(channelID) for channelID in result[2].split(",")],
                "fanfic": [int(channelID) for channelID in result[3].split(",")],
                "image": [int(channelID) for channelID in result[4].split(",")],
                "radio text": [int(channelID) for channelID in result[5].split(",")],
                "radio voice": [int(channelID) for channelID in result[6].split(",")],
                "bot bidness": [int(channelID) for channelID in result[7].split(",")],
            }
        return tempDict

    # Function to check if a command is allowed in a specific channel
    async def commandCheck(
        self, ctx: Union[bridge.BridgeApplicationContext, bridge.BridgeExtContext],
    ) -> bool:
        allowedChannel = self.getAllowed(ctx)
        if allowedChannel is not None:
            return ctx.channel.id in allowedChannel
        return True

    # Function to grab the allowed channels
    async def grabAllowed(
        self, ctx: Union[bridge.BridgeApplicationContext, bridge.BridgeExtContext],
    ) -> str:
        allowedChannel = self.getAllowed(ctx)
        textChannelAllowed: list[Union[TextChannel, VoiceChannel]] = [
            self.bot.get_channel(channel) for channel in allowedChannel
        ]
        guildAllowed = ", ".join([channel.mention for channel in textChannelAllowed])
        return f"This command is only allowed in {guildAllowed}"
