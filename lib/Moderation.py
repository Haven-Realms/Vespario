###
### MODERATION MODULE
###


# Import Discord Modules
import discord
from discord.ext import commands
from discord.utils import oauth_url
from discord import Spotify

# Load Additional Modules
import os
from configparser import ConfigParser
from json import loads, dumps


# Moderation Module Class #
class Moderation(commands.Cog):

    def __init__(self, bot):

        # Define Variables
        self.bot = bot
        self.prefix = ">"
        self.configs = {}

    async def cog_check(self, ctx):
        prefix = getattr(ctx.cog, "prefix", None)
        if prefix is not None:
            return ctx.prefix == self.prefix
        else:
            return True

    @commands.Cog.listener()
    async def on_ready(self):
        # Setup All Guilds With Moderation
        for guild in self.bot.guilds:
            if self.bot._has_feature(guild, "moderation"):
                await self._guild_setup(guild)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            pass

    @commands.command()
    async def enable(self, ctx):
        if ctx.message.author.guild_permissions.administrator:

            # Define Variables
            guild = ctx.message.author.guild

            # Enable Moderation
            await ctx.send("Enabling Moderation Feature...")
            await self.bot._enable_feature(guild, "moderation")
            await ctx.send("All done! Your discord now has the moderation feature enabled. Please use \"" + self.prefix + "\" for all commands.")
        else:
            self.bot._permission_denied(ctx)

    @commands.command()
    async def allow_score_points(self, ctx, member: discord.Member = None):
        if ctx.message.author.guild_permissions.administrator:
            if member == None:
                member = ctx.author
            
            # Load Configuration
            config = self.configs[member.guild]

            # Allow Member to Score Points
            config.set(str(member.id), "score_points", "True")

            # Update to Master
            self.configs[member.guild] = config

            # Notify Member
            await ctx.send("<@" + str(member.id) + "> can now score points on other users.")
        else:
            await self.bot._permission_denied(ctx)

    @commands.command()
    async def score(self, ctx, member: discord.Member = None, score = "0"):

        if member == None:
            member = ctx.author

        # Check Permission
        if self._can_score_points(ctx.message.author.guild, ctx.message.author):
            # Define Variables
            id = str(member.id)
            guild = member.guild
            score = int(score)

            # Load Configuration
            config = self.configs[guild]

            # Update Player Score
            if score != 0:
                currentScore = int(config.get(id, "score"))
                newScore = currentScore + score
                config.set(id, "score", str(newScore))

            # Update to Master
            self.configs[guild] = config

            if score > 0:
                await ctx.send("<@" + str(member.id) + "> has been awarded " + str(score) + " points.")
            elif score < 0:
                await ctx.send("<@" + str(member.id) + "> has been deducted by " + str(score) + " points. Please be careful.")
            else:
                await ctx.send("Please specify an amount to score.")
        else:
            await self.bot._permission_denied(ctx)

    def _can_score_points(self, guild, member):

        # Load Configuration
        config = self.configs[guild]

        # Check if Player Can Score Points
        allowed = False
        if config.get(str(member.id), "score_points") == "True":
            allowed = True
        return allowed

    async def _guild_setup(self, guild):

        # Setup Default User Configuration
        guildUserFile = "guilds/" + str(guild.id) + "/users.rcf"

        # Create If Not Exists
        if not os.path.exists(guildUserFile):
            newFile = open(guildUserFile, "w")
            newFile.close()

        # Load Configuration
        config = ConfigParser()
        config.read(guildUserFile)

        # Debug Output
        await self.bot.guild_debug(guild, ":judge: Processing " + str(len(guild.members)-1) + " Total Users.")
        
        # Process All User Data
        saveRequired = False
        for member in guild.members:
            if member.id != self.bot.id:
                if not config.has_section(str(member.id)):
                    config.add_section(str(member.id))
                    saveRequired = True
                if not config.has_option(str(member.id), "moderator"):
                    config.set(str(member.id), "moderator", "False")
                    saveRequired = True
                if not config.has_option(str(member.id), "score_points"):
                    config.set(str(member.id), "score_points", "False")
                    saveRequired = True
                if not config.has_option(str(member.id), "score"):
                    config.set(str(member.id), "score", "0")
                    saveRequired = True

        # Check if Save Required
        if saveRequired:
            with open(guildUserFile, "w") as configFile:
                config.write(configFile)

        # Add to Master
        self.configs[guild] = config

        # Debug Finish
        await self.bot.guild_debug(guild, ":judge: Moderation Successfully Enabled.")

async def setup(bot):

    # Add Moderation Cog to Bot
    cog = Moderation(bot)
    bot.recordedCogs["moderation"] = cog
    await bot.add_cog(cog)
