###
### SELF-ROLES MODULE
###


# Import Discord Modules
import typing
import discord
from discord.ext import commands
from json import loads, dumps
from time import sleep

# Load Additional Modules
import os
from json import loads, dumps
from configparser import ConfigParser

class RoleSelector(discord.ui.Select):

    def __init__(self, cog, guild):
        
        super().__init__(placeholder="Select Your Subscribed Role",
                       options=[discord.SelectOption(label=str(role.name)[:25], description=str(role.id), value=str(role.id), emoji=role.icon)
                                for role in guild.roles[:25]])

        self.cog = cog
        self.guild = guild

    async def callback(self, interaction: discord.Interaction):

        # Delete View
        message = interaction.message
        roleID = self.values[0]
        await message.delete()

        guildConfig = self.cog.bot.get_config(self.guild)

        guildRoles = guildConfig.get("self-roles", "roles")
        
        roles = loads(guildRoles)
        roles[int(roleID)] = ""
        guildConfig.set("self-roles", "roles", dumps(roles))
        guildDirectory = str("guilds/" + str(self.guild.id))
        with open(guildDirectory + "/config.rcf", "w") as confFile:
            guildConfig.write(confFile)
            confFile.close()
        role = self.guild.get_role(int(roleID))
        await self.cog.bot.guild_debug(self.guild, ":book: Successfully added " + role.name + " to subscribed roles.")

class RoleSelectorView(discord.ui.View):

    def __init__(self, cog, guild):
        super().__init__(timeout=None)

        self.add_item(RoleSelector(cog, guild))

class RoleChannelSelector(discord.ui.Select):

    def __init__(self, cog, guild):
        
        super().__init__(placeholder="Select Your Roles Channel",
                       options=[discord.SelectOption(label=str(channel.name), description=str(channel.id), value=str(channel.id), emoji='🎫')
                                for channel in guild.text_channels])

        self.cog = cog
        self.guild = guild

    async def callback(self, interaction: discord.Interaction):

        await self.cog._set_role_channel(self.guild, interaction, self.values[0])
        await self.cog._guild_setup(self.guild)

        # Delete View
        message = interaction.message
        await message.edit(view=None)
        

class RoleChannelSelectorView(discord.ui.View):

    def __init__(self, cog, guild):
        super().__init__(timeout=None)

        self.add_item(RoleChannelSelector(cog, guild))

        
class SelfRoles(commands.Cog):

    def __init__(self, bot):

        # Define Variables
        self.bot = bot
        self.prefix = "?"
        self.guildRoles = {}

    @commands.Cog.listener()
    async def on_ready(self):

        # Process All Guilds
        for guild in self.bot.guilds:

            if self.bot._has_feature(guild, "self-roles"):

                # Load Configuration
                guildConfig = self.bot.get_config(guild)

                # Default Setup
                saveRequired = False
                if not guildConfig.has_section("self-roles"):
                    guildConfig.add_section("self-roles")
                    saveRequired = True
                if not guildConfig.has_option("self-roles", "roles"):
                    guildConfig.set("self-roles", "roles", dumps({}))
                    saveRequired = True

                # Save If Required
                if saveRequired:
                    guildDirectory = str("guilds/" + str(guild.id))
                    with open(guildDirectory + "/config.rcf", "w") as confFile:
                        guildConfig.write(confFile)
                        confFile.close()

                await self._guild_setup(guild)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):

        guild = self.bot.get_guild(reaction.guild_id)
        config = self.bot.get_config(guild)

        if config.has_option("self-roles", "roles"):
            roles = loads(config.get("self-roles", "roles"))
        else:
            roles = {}

        if config.has_option("self-roles", "manager"):
            manager = int(config.get("self-roles", "manager"))
            if reaction.message_id == manager:
                for role in roles:
                    emoji = roles[role]
                    if emoji == reaction.emoji.name:
                        member = guild.get_member(reaction.user_id)
                        activeRole = guild.get_role(int(role))
                        await member.add_roles(activeRole)                        
                        break
                        
                
    async def _set_role_channel(self, guild, interaction, channelID):

       # Define Variables
       channel = await guild.fetch_channel(channelID)

       await interaction.response.send_message("Setting roles channel to " + channel.mention)

       # Load Configuration
       config = self.bot.get_config(guild)

       # Set Ticket Channel
       config.set("self-roles", "channel", str(channel.id))

       # Save Config
       await self.bot._save_config(guild)

    async def _guild_setup(self, guild):

        # Load Configuration
        guildConfig = self.bot.get_config(guild)
        saveRequired = False

        # Check if Channel Exists
        if not guildConfig.has_option("self-roles", "channel"):
            view = RoleChannelSelectorView(self, guild)
            await self.bot.guild_debug(guild, ":book: Please specify a roles channel.", view=view)

        # Check if Manager Exists
        if guildConfig.has_option("self-roles", "manager"):

            managerID = guildConfig.get("self-roles", "manager")
            channelID = guildConfig.get("self-roles", "channel")

            channel = await guild.fetch_channel(int(channelID))
            message = await channel.fetch_message(int(managerID))

            emojis = loads(guildConfig.get("self-roles", "roles"))
            for emoji in emojis:
                emojiStr = emojis[emoji]
                emojiIcon = self.bot.get_emoji(int(emojiStr))
                await message.add_reaction(emojiIcon)
                
                        
    @commands.command()
    async def add_subscribe_role(self, ctx):
        if ctx.message.author.guild_permissions.administrator:

            # Define Variables
            guild = ctx.message.author.guild

            # Send Ticket Channel View
            view = RoleSelectorView(self, guild)
            await self.bot.guild_debug(guild, ":book: Please a role you want users to subscribe to:", view=view)
        else:
            self.bot._permission_denied(ctx)

    @commands.command()
    async def set_role_channel(self, ctx):
        if ctx.message.author.guild_permissions.administrator:

            # Define Variables
            guild = ctx.message.author.guild

            # Send Ticket Channel View
            view = RoleChannelSelectorView(self, guild)
            await self.bot.guild_debug(guild, ":book: Please sepcify a role channel.", view=view)
        else:
            self.bot._permission_denied(ctx)        
        

async def setup(bot):

    # Add Self Roles Cog to Bot
    cog = SelfRoles(bot)
    bot.recordedCogs["self-roles"] = cog
    await bot.add_cog(cog)
