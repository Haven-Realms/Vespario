# Import nextcord Modules
import nextcord
from nextcord.ext import commands
from nextcord.utils import oauth_url
from nextcord import Spotify

# Load Additional Modules
from configparser import ConfigParser
from json import loads, dumps

# Core Module Class #
class Core(commands.Cog):

    def __init__(self, bot):

        # Define Variables
        self.bot = bot
        self.prefix = "?"

    async def cog_check(self, ctx):
        prefix = getattr(ctx.cog, "prefix", None)
        if prefix is not None:
            return ctx.prefix == prefix
        else:
            return True

    @commands.command()
    async def reload_config(self, ctx):
        if ctx.message.author.guild_permissions.administrator:
            guildID = str(ctx.message.guild.id)
            await self.bot._reload_config(ctx.message.guild)
            await ctx.send("All done! Your nextcord server's configuration has now been reloaded.")
            await self.bot._guild_feature_setup(ctx.message.guild)
        else:
            await self.bot._permission_denied(ctx)

    @commands.command()
    async def enable_feature(self, ctx, feature: str = None):
        if ctx.message.author.guild_permissions.administrator:
            # Define Variables
            guild = ctx.message.guild

            # Check if Feature Specified
            if feature == None:
                await ctx.send("Please specify a feature name.")
                return

            # Check if Enabled
            if feature in self.bot.recordedCogs:
                await ctx.send("Attempting to enable " + feature + " module...")

                # Enable Module
                await self.bot._enable_feature(guild, feature)
            else:
                await ctx.send("That is not a valid feature name. These are valid options: " + json.dumps(self.recordedCogs.keys()))
        else:
            self.bot._permission_denied(ctx)

    @commands.command()
    async def set_bot_channel(self, ctx):
        if ctx.message.author.guild_permissions.administrator:

            # Update Guild Configuration
            config = self.bot.get_config(ctx.message.guild)
            config.set("base", "bot_channel", str(ctx.message.channel.id))
            
            await ctx.send("This channel is now the main bot command channel. Any commands in other channels will not work unless specified.")

            # Save Configuration
            await self.bot._save_config(ctx.message.guild)
        else:
            self.bot._permission_denied(ctx)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        if after.pending == False:
            guild = after.guild
            config = self.bot.get_config(guild)
            if config.has_option("base", "default_roles"):
                roles = loads(config.get("base", "default_roles"))
                for roleID in roles:
                    role = guild.get_role(roleID)
                    if role not in after.roles:
                        await after.add_roles(role)

    @commands.command()
    async def add_default_role(self, ctx, role: nextcord.Role = None):
        if ctx.message.author.guild_permissions.administrator:

            # Check if Role Specified
            if role == None:
                await ctx.send("Please mention a role to add to the list of default roles.")
                return

            # Update Guild Configuration
            config = self.bot.get_config(ctx.message.guild)
            if config.has_option("base", "default_roles"):
                roles = loads(config.get("base", "default_roles"))
            else:
                roles = []
            roles.append(role.id)
            config.set("base", "default_roles", dumps(roles))
            
            await ctx.send(role.name + " has been added to the list of default roles.")

            # Save Configuration
            await self.bot._save_config(ctx.message.guild)
        else:
            self.bot._permission_denied(ctx)

    def get_bot_channel(self, guild):

        # Get Configuration
        config = self.bot.get_config(guild)

        # Check for Bot Channel
        if config.has_option("base", "bot_channel"):
            id = config.get("base", "bot_channel")
            channel = guild.get(int(id))
            return channel
        return None
    
async def setup(bot):

    # Add Core Cog to Bot
    cog = Core(bot)
    bot.recordedCogs["core"] = cog
    await bot.add_cog(cog)
