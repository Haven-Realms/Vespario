import discord
import os
from discord.ext import commands, tasks
from datetime import datetime
from configparser import ConfigParser
from discord import Embed

from json import loads, dumps

class AnnouncementChannelSelector(discord.ui.Select):

    def __init__(self, cog, guild, base):
        
        super().__init__(placeholder="Select Your Announcement Channel",
                       options=[discord.SelectOption(label=str(channel.name)[:25], description=str(channel.id), value=str(channel.id), emoji='🎫')
                                for channel in guild.text_channels[:25]])

        self.cog = cog
        self.guild = guild
        self.base = base

    async def callback(self, interaction: discord.Interaction):

        await self.cog._set_announcement_channel(self.guild, interaction, self.base, self.values[0])
        await self.cog._guild_setup(self.guild)

        # Delete View
        message = interaction.message
        await message.edit(view=None)
        

class AnnouncementChannelSelectorView(discord.ui.View):

    def __init__(self, cog, guild, base):
        super().__init__(timeout=None)

        self.add_item(AnnouncementChannelSelector(cog, guild, base))

class Announcements(commands.Cog):

    def __init__(self, bot):

        # Define Variables
        self.bot = bot
        self.prefix = "!"
        self.announcementConfs = {}

    @commands.Cog.listener()
    async def on_ready(self):
        # Setup All Guilds with Announcements
        for guild in self.bot.guilds:
            if self.bot._has_feature(guild, "announcements"):
                await self._guild_setup(guild)

    async def _guild_setup(self, guild):

        # Setup Default User Configuration
        guildAnnouncementsFile = "guilds/" + str(guild.id) + "/announcements.rcf"

        # Create If Not Exists
        if not os.path.exists(guildAnnouncementsFile):
            newFile = open(guildAnnouncementsFile, "w")
            newFile.close()

        # Load Configuration
        guildConfig = self.bot.get_config(guild)

        config = ConfigParser()
        config.read(guildAnnouncementsFile)
        setattr(self, str(guild.id) + "CONFIG", config)

        # Debug Output
        await self.bot.guild_debug(guild, ":postal_horn: Initializing Announcements system...")

        saveRequired = False
        if not guildConfig.has_section("announcements"):
            guildConfig.add_section("announcements")
            saveRequired = True
    

        # Check if Contains Channel Yet
        if not guildConfig.has_option("announcements", "channel"):
            view = AnnouncementChannelSelectorView(self, guild, "announcement")
            await self.bot.guild_debug(guild, ":postal_horn: Please specify an announcements channel.", view=view)

        # Check if Save Required
        if saveRequired:
            self.bot.update_config(guild, config)
            await self.bot._save_config(guild)

        # Debug Finish
        await self.bot.guild_debug(guild, ":postal_horn: Announcements now successfully enabled.")

    async def cog_check(self, ctx):
        prefix = getattr(ctx.cog, "prefix", None)
        if prefix is not None:
            return ctx.prefix == prefix
        else:
            return True

    @commands.command()
    async def set_announcement_channel(self, ctx):
        if ctx.message.author.guild_permissions.administrator:

            # Define Variables
            guild = ctx.message.author.guild

            # Send Ticket Channel View
            view = TicketSelectorView(self, guild, "announcement")
            await self.bot.guild_debug(guild, ":postal_horn: Please sepcify an announcements channel.", view=view)
        else:
            self.bot._permission_denied(ctx)     

    async def _set_announcement_channel(self, guild, interaction, base, channelID):

       # Define Variables
       channel = await guild.fetch_channel(channelID)

       if base == "announcement": 
           await interaction.response.send_message("Setting announcement channel to " + channel.mention)
       else:
           await interaction.response.send_message("Setting announcement channel for " + base + " to " + channel.mention)

       # Load Configuration
       config = self.bot.get_config(guild)

       # Set Ticket Channel
       if base == "announcement":
           config.set("announcements", "channel", str(channelID))
       else:
           config.set("tickets", base + "_channel", str(channelID))
       # Check if Channel has Parent Category
       if channel.category != None and base == "ticket":
           config.set("announcements", "category", str(channel.category_id))

       # Save Config
       await self.bot._save_config(guild)

    async def _post_announcement(self, guild, announcement, announcementConf, announcementChannel):
        
        # Define Variables
        announcementTitle = announcementConf.get(announcement, "title")
        announcementDescription = announcementConf.get(announcement, "description")
        announcementDatetime = datetime.utcnow()
        if announcementConf.has_option(announcement, "url"):
            announcementURL = announcementConf.get(announcement, "url")
        
        # Setup Embed
        if "announcementURL" in locals():
            announcementEmbed = Embed(color=0x00bcff, title=str(announcementTitle), description=str(announcementDescription), url=announcementURL)
        else:
            announcementEmbed = Embed(color=0x00bcff, title=str(announcementTitle), description=str(announcementDescription))
        if announcementConf.has_option(announcement, "author"):
            author = guild.get_member(int(announcementConf.get(announcement, "author")))
            icon_url = author.display_avatar
        if "icon_url" in locals():
            announcementEmbed.set_footer(text="Published By " + author.display_name + " | " + announcementDatetime.strftime("%Y-%m-%d %H:%M"), icon_url=icon_url)
        else:
            announcementEmbed.set_footer(text=announcementDatetime.strftime("%Y-%m-%d %H:%M"))
            
        if announcementConf.has_option(announcement, "thumbnail"):
            announcementEmbed.set_thumbnail(url=str(announcementConf.get(announcement, "thumbnail")))
            
        print(f"Posting announcement {announcement}")
        await announcementChannel.send("|| @everyone ||", embed=announcementEmbed)
        announcementConf.set(announcement, "posted", "True")
        self._save_config(guild.id)

    @commands.command()
    async def announce(self, ctx, *, command = None):
        guild = ctx.message.author.guild
        guildConf = self.bot.get_config(guild)
        announcementConf = getattr(self, str(guild.id) + "CONFIG")
        arguments = str(command).split(" ")
        if arguments[0] in announcementConf:
            await ctx.message.delete()
            if ctx.message.author.guild_permissions.administrator:
                announcement = arguments[0]
                announcementChannel = self.bot.get_channel(int(guildConf.get("announcements", "channel")))
                await self._post_announcement(guild, announcement, announcementConf, announcementChannel)

async def setup(bot):

    # Add Announcements Cog to Bot
    cog = Announcements(bot)
    bot.recordedCogs["announcements"] = cog
    await bot.add_cog(cog)
