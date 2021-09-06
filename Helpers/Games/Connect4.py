# Builtin
from datetime import datetime
from typing import List, Union
# Pip
import numpy
from discord import Embed, Colour, Reaction
from discord.ext.commands import Context, Bot


# Connect4 class to play connect 4 in a discord channel
class Connect4:
    # Initialise variables
    def __init__(self, ctx: Context, bot: Bot, color: Colour) -> None:
        self.ctx = ctx
        self.bot = bot
        self.colour = color
        self.gameID = 2
        self.player1 = self.ctx.author
        self.nextPlayer = self.player1
        self.lastActivity = datetime.now()
        self.grid = [[0 for i in range(7)] for j in range(6)]
        self.gameEmojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "🛑"]
        self.iconEmojis = ["\U0001F535", "\U0001F7E1", "\U0001F534"]
        self.isPlaying = True
        self.changeMade = False
        self.player2 = None
        self.gameMessage = None
        self.currentIndex = None
        self.result = None

    # Function to return the game name
    def __repr__(self) -> str:
        return "Connect 4"

    # Function to manage moves made by the player
    def moveManager(self, reaction: str) -> None:
        if reaction == self.gameEmojis[0]:
            self.addMove(0)
        elif reaction == self.gameEmojis[1]:
            self.addMove(1)
        elif reaction == self.gameEmojis[2]:
            self.addMove(2)
        elif reaction == self.gameEmojis[3]:
            self.addMove(3)
        elif reaction == self.gameEmojis[4]:
            self.addMove(4)
        elif reaction == self.gameEmojis[5]:
            self.addMove(5)
        elif reaction == self.gameEmojis[6]:
            self.addMove(6)
        elif reaction == self.gameEmojis[7]:
            self.isPlaying = False
            self.switchPlayer()
            self.result = ("Win", self.nextPlayer)

    # Function to update the 2D array with new moves
    def addMove(self, columnNumber: int) -> None:
        availableRows: List[int] = [i for i in range(len(self.grid)) if self.grid[i][columnNumber] == 0]
        if len(availableRows) != 0:
            self.currentIndex = [availableRows[-1], columnNumber]
            if self.nextPlayer == self.player1:
                self.grid[self.currentIndex[0]][self.currentIndex[1]] = 1
            else:
                self.grid[self.currentIndex[0]][self.currentIndex[1]] = 2
            self.changeMade = True

    # Function to test for a draw
    def drawCheck(self) -> None:
        temp: List[int] = [item for row in self.grid for item in row]
        if all(item != 0 for item in temp):
            self.isPlaying = False
            self.result = ("Draw", self.nextPlayer)

    # Function to check for wins
    def winChecker(self) -> None:
        # Function to check for consecutive numbers
        def consecutiveCheck(row: Union[List[int], numpy.ndarray]) -> bool:
            totalConsecutive = 0
            if self.nextPlayer == self.player1:
                valueToCheck = 1
            else:
                valueToCheck = 2
            for value in row:
                if value == valueToCheck:
                    totalConsecutive += 1
                else:
                    totalConsecutive = 0
                if totalConsecutive >= 4:
                    return True
            return False
        # Function to check for vertical wins
        def verticalCheck() -> bool:
            verticalRow: List[int] = [row[self.currentIndex[1]] for row in self.grid]
            return consecutiveCheck(verticalRow)
        # Function to check for horizontal wins
        def horizontalCheck() -> bool:
            horizontalRow: List[int] = self.grid[self.currentIndex[0]]
            return consecutiveCheck(horizontalRow)
        # Function to check for diagonal wins
        def diagonalCheck() -> bool:
            result = []
            diagonals = self.getDiagonals()
            for direction in diagonals:
                for row in direction:
                    result.append(consecutiveCheck(row))
            return any(result)
        if verticalCheck() or horizontalCheck() or diagonalCheck():
            self.isPlaying = False
            self.result = ("Win", self.nextPlayer)

    # Function to get the diagonals
    def getDiagonals(self) -> List[List[numpy.ndarray]]:
        def getPositive(npArray):
            return [npArray[::-1, :].diagonal(i) for i in range(-npArray.shape[0]+1, npArray.shape[1])]
        def getNegative(npArray):
            return [npArray.diagonal(i) for i in range(npArray.shape[1]-1, -npArray.shape[0], -1)]
        npArray = numpy.array(self.grid)
        return [getPositive(npArray), getNegative(npArray)]

    # Function to determine who goes next
    def switchPlayer(self) -> None:
        if self.nextPlayer == self.player1:
            self.nextPlayer = self.player2
        else:
            self.nextPlayer = self.player1

    # Function to process a reaction from the gameManager
    def processReaction(self, reaction: Reaction) -> None:
        self.lastActivity = datetime.now()
        self.moveManager(str(reaction))
        if self.isPlaying:
            if self.changeMade:
                self.changeMade = False
                self.drawCheck()
                self.winChecker()
                self.switchPlayer()

    # Function to update the board
    async def embedUpdate(self) -> None:
        board = ""
        for row in self.grid:
            for item in row:
                if item == 0:
                    board += self.iconEmojis[0]
                elif item == 1:
                    board += self.iconEmojis[1]
                elif item == 2:
                    board += self.iconEmojis[2]
            board += "\n"
        gameEmbed = Embed(description=board, colour=self.colour)
        if self.isPlaying:
            gameEmbed.title = f"Connect 4 - {self.nextPlayer}'s Turn"
        else:
            if self.result[0] == "Win":
                gameEmbed.title = f"Game Over! {self.result[1]} Won"
            elif self.result[0] == "Draw":
                gameEmbed.title = f"Game Over! It's A Draw"
            else:
                gameEmbed.title = f"Game Over!"
        await self.gameMessage.edit(embed=gameEmbed)
