# Builtin
from datetime import datetime, timedelta
import os
import random
import asyncio
import json
import requests
# Pip
from discord.errors import NotFound
from discord.ext import commands
from discord import Embed
from discord import Colour
from discord import File
import apsw
# Custom
from Utils.Paginator import Paginator
from Utils import Utils
import Config

# Path variables
rootDirectory = os.path.join(os.path.dirname(__file__), os.pardir)
triviaPath = os.path.join(rootDirectory, "Resources", "trivia.json")
choicesPath = os.path.join(rootDirectory, "Resources", "choices.json")
triviaScoresPath = os.path.join(rootDirectory, "Resources", "lisBot.db")
historyEventsPath = os.path.join(rootDirectory, "Resources", "historyEvents.json")
memoryPath = os.path.join(rootDirectory, "Screenshots")


# Cog to manage life is strange commands
class lifeIsStrange(commands.Cog, name="Life Is Strange"):
    # Initialise the client
    def __init__(self, client):
        self.client = client
        self.colour = Colour.purple()
        self.cursor = apsw.Connection(triviaScoresPath).cursor()
        self.triviaReactions = {"🇦": 1, "🇧": 2, "🇨": 3, "🇩": 4}
        self.nextTrivia = 0
        self.pastInputs = []
        self.pastResponses = []
        self.triviaQuestions = None
        self.choicesTable = None
        self.memoryImages = None
        self.historyEventsTable = None
        self.lifeIsStrangeInit()

    # Function to initialise life is strange variables
    def lifeIsStrangeInit(self):
        # Create trivia questions array
        self.triviaQuestions = json.loads(open(triviaPath, "r").read())
        random.shuffle(self.triviaQuestions)

        # Setup the choices table
        self.choicesTable = json.loads(open(choicesPath, "r").read())

        # Setup memory images array
        self.memoryImages = os.listdir(memoryPath)

        # Setup history events table
        self.historyEventsTable = json.loads(open(historyEventsPath, "r").read())

    # Function to create trivia questions
    def triviaMaker(self):
        if self.nextTrivia == len(self.triviaQuestions):
            # All questions done
            random.shuffle(self.triviaQuestions)
            self.nextTrivia = 0
        randomTrivia = self.triviaQuestions[self.nextTrivia]
        self.nextTrivia += 1
        triviaEmbed = Embed(colour=self.colour)
        triviaEmbed.title = randomTrivia["question"]
        triviaEmbed.description = f"""A. {randomTrivia["option 1"]}\nB. {randomTrivia["option 2"]}\nC. {randomTrivia["option 3"]}\nD. {randomTrivia["option 4"]}"""
        triviaEmbed.set_footer(text=f"{len(self.triviaQuestions)} questions")
        return triviaEmbed, int(randomTrivia["correct option"])

    # Function to create final trivia embed
    def finalTrivia(self, triviaEmbed, correctOption, guess):
        description = triviaEmbed.description.split("\n")
        newDescription = ""
        for count, option in enumerate(description):
            if count+1 == correctOption:
                temp = option + " ✅"
            else:
                temp = option + " ❌"
            if guess != None:
                try:
                    if self.triviaReactions[str(guess[0])] == count+1:
                        temp += f" ⬅ {str(guess[1])} guessed"
                except KeyError:
                    # Unknown emoji
                    pass
            newDescription += temp + "\n"
        finalObj = Embed(colour=self.colour)
        finalObj.title = triviaEmbed.title
        finalObj.description = newDescription
        finalObj.set_footer(text=f"{len(self.triviaQuestions)} questions")
        return finalObj

    # Function to update a user's trivia score
    def updateTriviaScores(self, ctx, correctOption, guess):
        try:
            orgUser = list(self.cursor.execute(f"SELECT * FROM triviaScores WHERE guildID == {ctx.guild.id} and userID == {ctx.author.id}"))[0]
        except IndexError:
            # User not in database
            orgUser = (ctx.guild.id, ctx.author.id, 0, 0, 0, 0)
            self.cursor.execute(f"INSERT INTO triviaScores values{orgUser}")
        orgUser = list(orgUser)
        if guess is None:
            # No answer
            orgUser[2] -= 2
            orgUser[4] += 2
        else:
            try:
                guessUser = list(self.cursor.execute(f"SELECT * FROM triviaScores WHERE guildID == {ctx.guild.id} and userID == {guess[1].id}"))[0]
            except IndexError:
                # User not in database
                guessUser = (ctx.guild.id, guess[1].id, 0, 0, 0, 0)
                self.cursor.execute(f"INSERT INTO triviaScores values{guessUser}")
            guessUser = list(guessUser)
            originalAuthor = ctx.author.id
            guessAuthor = guess[1].id
            try:
                if self.triviaReactions[str(guess[0])] == correctOption:
                    # Question correct
                    if originalAuthor == guessAuthor:
                        # No steal
                        orgUser[2] += 2
                        orgUser[3] += 2
                    else:
                        # Steal
                        orgUser[2] += 1
                        orgUser[3] += 1
                        guessUser[2] += 1
                        guessUser[3] += 1
                else:
                    # Question incorrect
                    if originalAuthor == guessAuthor:
                        # No steal
                        orgUser[2] -= 2
                        orgUser[4] += 2
                    else:
                        # Steal
                        orgUser[2] -= 1
                        orgUser[4] += 1
                        guessUser[2] -= 1
                        guessUser[4] += 1
            except KeyError:
                # Unknown emoji
                if originalAuthor == guessAuthor:
                    # No steal
                    orgUser[2] -= 2
                    orgUser[4] += 2
                else:
                    # Steal
                    orgUser[2] -= 1
                    orgUser[4] += 1
                    guessUser[2] -= 1
                    guessUser[4] += 1
            self.cursor.execute(f"UPDATE triviaScores SET score = {guessUser[2]}, pointsGained = {guessUser[3]}, pointsLost = {guessUser[4]} WHERE guildID == {ctx.guild.id} AND userID == {guessAuthor}")
        self.cursor.execute(f"UPDATE triviaScores SET score = {orgUser[2]}, pointsGained = {orgUser[3]}, pointsLost = {orgUser[4]} WHERE guildID == {ctx.guild.id} AND userID == {ctx.author.id}")
        # Update ranks
        self.updateRanks(ctx.guild.id)

    # Function to update the ranks for a specific guild
    def updateRanks(self, guildID):
        sortedGuildUsers = self.rankSort(list(self.cursor.execute(f"SELECT * FROM triviaScores WHERE guildID == {guildID}")))
        sortedRanks = [(row[0], row[1], row[2], row[3], row[4], count+1) for count, row in enumerate(sortedGuildUsers)]
        for rank in sortedRanks:
            self.cursor.execute(f"UPDATE triviaScores SET rank = {rank[5]} WHERE guildID == {rank[0]} AND userID == {rank[1]}")

    # Function to sort a list of trivia scores based on the ranks
    def rankSort(self, arr):
        return sorted(arr, key=lambda x: x[2], reverse=True)

    # Function to create a choice embed page
    def choicePageMaker(self, count, episode):
        episodeEmbed = Embed(title=f"Episode {count} Choices", colour=self.colour)
        majorString = "".join([choice["text"] for choice in episode if choice["major"] == "Yes"])
        minorString = "".join([choice["text"] for choice in episode if choice["major"] == "No"])
        episodeEmbed.add_field(name="Major Choices", value=majorString)
        episodeEmbed.add_field(name="Minor Choices", value=minorString)
        return episodeEmbed

    # Function to calculate how many seconds to wait
    def secondsUntilMidnight(self, currentTime):
        currentTimedelta = timedelta(hours=currentTime.hour, minutes=currentTime.minute, seconds=currentTime.second, microseconds=currentTime.microsecond)
        midnightTime = timedelta(hours=23, minutes=59)
        return (midnightTime-currentTimedelta).total_seconds() + 60

    # Get the suffix for a specific day
    def getSuffix(self, day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            return "th"
        else:
            return ["st", "nd", "rd"][day % 10 - 1]

    # Get a worded date format for a specific day
    def getWordedDate(self, dt):
        return dt.strftime("{DAY} of %B %Y").replace("{DAY}", str(dt.day) + self.getSuffix(dt.day))

    # Make a request to the huggingface model
    def chatbotQuery(self, message):
        payload = {
            "inputs": {
                "past_user_inputs": self.pastInputs,
                "generated_responses": self.pastResponses,
                "text": message
            }, "parameters": {
                "max_length": 200,
                "temperature": 0.5,
                "top_k": 100,
                "top_p": 0.7
            }}
        return requests.post("https://api-inference.huggingface.co/models/Aspect11/DialoGPT-Medium-LiSBot",
                             headers={"Authorization": f"Bearer {Config.huggingfaceToken}"},
                             json=payload).json()

    # Sends a message detailing a LiS event which happened on the same day
    async def historyEvents(self):
        # Get tomorrow's date so once midnight hits, the correct date can be checked
        tomorrowDate = datetime.now() + timedelta(days=1)
        await asyncio.sleep(self.secondsUntilMidnight(tomorrowDate))
        currentEvent = [event for event in self.historyEventsTable if tomorrowDate.strftime("%d/%m") in event[1]]
        if len(currentEvent) == 1:
            wordedDate = self.getWordedDate(datetime.strptime(currentEvent[0][1], "%d/%m/%Y"))
            for value in Utils.restrictor.IDs["life is strange"].values():
                try:
                    # If the amount of allowed channels for a specific guild is larger than 1, then the first channel is used
                    await self.client.get_channel(value[0]).send(f"Today on the {wordedDate}, this happened:\n\n{currentEvent[0][0]}")
                except AttributeError:
                    # This is just for testing purposes
                    # Normally this will never run since the bot will be in every guild in IDs
                    # And if it isn't then the bot automatically removes those guilds from channelIDs.json
                    continue

    # Function which runs once the bot is setup and running
    @commands.Cog.listener()
    async def on_ready(self):
        # Run the history function to display a LiS history event
        await self.historyEvents()

    # trivia command with a cooldown of 1 use every 60 seconds per guild
    @commands.command(help=f"Displays a trivia question which can be answered via the emojis. It will timeout in 15 seconds. It has a cooldown of {Utils.long} seconds", description="Scoring:\n\nNo answer = 2 points lost.\nUnrecognised emoji and answered by the original command sender = 2 points lost.\nUnrecognised emoji and answer stolen = 1 point lost for each person.\nCorrect answer and answered by the original command sender = 2 points gained.\nCorrect answer and answer stolen = 1 point gained for each person.\nIncorrect answer and answered by the original command sender = 2 points lost.\nIncorrect answer and answer stolen = 1 point lost for each person.", usage="trivia", brief="Trivia")
    @commands.cooldown(1, Utils.long, commands.BucketType.guild)
    async def trivia(self, ctx):
        def answerCheck(reaction, user):
            return user.id != self.client.user.id
        # Grab random trivia
        triviaObj, correctOption = self.triviaMaker()
        triviaMessage = await ctx.channel.send(embed=triviaObj)
        # Add relations
        for reaction in self.triviaReactions.keys():
            await triviaMessage.add_reaction(reaction)
        # Wait for the user's reaction and make sure the bot's reactions aren't counted
        reaction = None
        while True:
            try:
                reaction = await self.client.wait_for("reaction_add", timeout=15, check=answerCheck)
                # Edit the embed with the results
                resultEmbed = self.finalTrivia(triviaObj, correctOption, reaction)
                await triviaMessage.edit(embed=resultEmbed)
            except asyncio.TimeoutError:
                # Noone reacted
                resultEmbed = self.finalTrivia(triviaObj, correctOption, None)
                await triviaMessage.edit(embed=resultEmbed)
            break
        # Update trivia scores
        self.updateTriviaScores(ctx, correctOption, reaction)
        await triviaMessage.clear_reactions()

    # triviaScore command with a cooldown of 1 use every 20 seconds per guild
    @commands.command(aliases=["ts"], help=f"Displays a user's trivia score. It has a cooldown of {Utils.short} seconds", usage="triviaScore|ts", brief="Trivia")
    @commands.cooldown(1, Utils.short, commands.BucketType.guild)
    async def triviaScore(self, ctx, target=None):
        targetID = ctx.author.id
        if target is not None:
            try:
                # Check if mentioned user is in the current guild
                tempTarget = int(target.replace("<@!", "").replace(">", ""))
                guild = await self.client.fetch_guild(ctx.guild.id)
                guildMember = await guild.fetch_member(tempTarget)
                targetID = tempTarget
            except ValueError or NotFound:
                # Argument is invalid or mentioned user not in current guild
                pass
        user = list(self.cursor.execute(f"SELECT * FROM triviaScores WHERE guildID == {ctx.guild.id} AND userID == {targetID}"))
        userObj = await self.client.fetch_user(targetID)
        if len(user) == 0:
            # User not in database
            await ctx.channel.send(f"{userObj.mention} hasn't answered any questions. Run {ctx.prefix}trivia to answer some")
        else:
            # User in database
            totalUserCount = len(list(self.cursor.execute(f"SELECT * FROM triviaScores WHERE guildID == {ctx.guild.id}")))
            triviaScoreEmbed = Embed(title=f"{userObj.name}'s Trivia Score", colour=self.colour)
            triviaScoreEmbed.description = f"Rank: **{user[0][5]}/{totalUserCount}**\nScore: **{user[0][2]}**\nPoints Gained: **{user[0][3]}**\nPoints Lost: **{user[0][4]}**"
            triviaScoreEmbed.set_thumbnail(url=userObj.avatar_url)
            await ctx.channel.send(embed=triviaScoreEmbed)

    # triviaLeaderboard command with a cooldown of 1 use every 45 seconds per guild
    @commands.command(aliases=["tl"], help=f"Displays the server's trivia scores leaderboard. It has a cooldown of {Utils.medium} seconds", usage="triviaLeaderboard|tl", brief="Trivia")
    @commands.cooldown(1, Utils.medium, commands.BucketType.guild)
    async def triviaLeaderboard(self, ctx):
        guildUsers = self.rankSort(list(self.cursor.execute(f"SELECT * FROM triviaScores WHERE guildID == {ctx.guild.id}")))
        triviaLeaderboardEmbed = Embed(title=f"{ctx.guild.name}'s Trivia Leaderboard", colour=self.colour)
        leaderboardDescription = ""
        for user in guildUsers[:10]:
            userName = await self.client.fetch_user(user[1])
            leaderboardDescription += f"{user[5]}. {userName}. (Score: **{user[2]}** | Points Gained: **{user[3]}** | Points Lost: **{user[4]}**)\n"
        if leaderboardDescription == "":
            leaderboardDescription = f"No users added. Run {ctx.prefix}trivia to add some"
        triviaLeaderboardEmbed.description = leaderboardDescription
        scoreList = [item[2] for item in guildUsers]
        triviaLeaderboardEmbed.set_footer(text=f"Top 10 Average Score: {round(sum(scoreList[:10])/len(scoreList[:10]))} | Average Score: {round(sum(scoreList)/len(scoreList))} | Total User Count: {len(guildUsers)}")
        await ctx.channel.send(embed=triviaLeaderboardEmbed)

    # choices command with a cooldown of 1 use every 60 seconds per guild
    @commands.command(help=f"Displays the different choices in the game and their responses. It has a cooldown of {Utils.long} seconds", description="\nArguments:\nEpisode Number - Either 1, 2, 3, 4 or 5. This argument is optional as not including it will display all choices", usage="choices (episode number)", brief="Life Is Strange")
    @commands.cooldown(1, Utils.long, commands.BucketType.guild)
    async def choices(self, ctx, *epNumber):
        if len(epNumber) == 0:
            # Display all choices with a paginator
            pages = []
            for count, episode in enumerate(self.choicesTable):
                pages.append(self.choicePageMaker(count+1, episode))
            # Create paginator
            paginator = Paginator(ctx, self.client)
            paginator.addPages(pages)
            await paginator.start()
        elif len(epNumber) == 1:
            # Only display specific episode number
            episodeNum = epNumber[0]
            # Run checks to make sure argument is correct
            if episodeNum.isdigit():
                episodeNum = int(episodeNum)
                if episodeNum >= 1 and episodeNum <= 5:
                    # Create embed page
                    await ctx.channel.send(embed=self.choicePageMaker(episodeNum, self.choicesTable[episodeNum-1]))
                else:
                    await ctx.channel.send("Not a valid episode number")
            else:
                await ctx.channel.send("Episode number is not a number")
        else:
            # Too many arguments
            await ctx.channel.send("Too many arguments")

    # memory command with a cooldown of 1 use every 20 seconds per guild
    @commands.command(help=f"Displays a random Life is Strange image. It has a cooldown of {Utils.short} seconds", usage="memory", brief="Life Is Strange")
    @commands.cooldown(1, Utils.short, commands.BucketType.guild)
    async def memory(self, ctx):
        randomImagePath = os.path.join(memoryPath, self.memoryImages[random.randint(0, len(self.memoryImages)-1)])
        await ctx.channel.send(file=File(randomImagePath))

    # # chatbot command with a cooldown of 1 use every 5 seconds per guild
    # @commands.command(help=f"Interacts with the LiS AI chatbot. It has a cooldown of {Utils.superShort} seconds", description="\nArguments:\nMessage - The message to send to the AI chatbot", usage="chatbot (message)", brief="Life Is Strange")
    # @commands.cooldown(1, Utils.superShort, commands.BucketType.guild)
    # async def chatbot(self, ctx, *args):
    #     async with ctx.channel.typing():
    #         req = self.chatbotQuery(" ".join(args))
    #         try:
    #             rounded = round(req["estimated_time"], 2)
    #             messageToSend = f"AI is starting up, try again in {round(rounded)} seconds"
    #         except KeyError:
    #             messageToSend = req["generated_text"]
    #             self.pastInputs.append(req["conversation"]["past_user_inputs"].pop(-1))
    #             self.pastResponses.append(req["conversation"]["generated_responses"].pop(-1))
    #     await ctx.channel.send(messageToSend)

    # Function to run channelCheck for Life Is Strange
    async def cog_check(self, ctx):
        return await Utils.restrictor.commandCheck(ctx)

    # Catch any cog errors
    async def cog_command_error(self, ctx, error):
        await Utils.errorHandler(ctx, error)


# Function which initialises the life is strange cog
def setup(client):
    client.add_cog(lifeIsStrange(client))
