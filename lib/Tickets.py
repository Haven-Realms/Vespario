###
### TICKETS MODULE
###


# Import Discord Modules
import typing
import discord
from discord.ext import commands

# Load Additional Modules
import os
from json import loads, dumps
from configparser import ConfigParser

# Tickets Dropdown Class #
class TicketSelector(discord.ui.Select):

    def __init__(self, cog, guild, base):
        
        super().__init__(placeholder="Select Your Ticket Channel",
                       options=[discord.SelectOption(label=str(channel.name)[:25], description=str(channel.id), value=str(channel.id), emoji='🎫')
                                for channel in guild.text_channels[:25]])

        self.cog = cog
        self.guild = guild
        self.base = base

    async def callback(self, interaction: discord.Interaction):

        await self.cog._set_ticket_channel(self.guild, interaction, self.base, self.values[0])
        await self.cog._guild_setup(self.guild)

        # Delete View
        message = interaction.message
        await message.edit(view=None)
        

class TicketSelectorView(discord.ui.View):

    def __init__(self, cog, guild, base, *args, **kwargs):
        super().__init__(timeout=None, *args, **kwargs)

    @discord.ui.select(placeholder="Select Your Ticket Channel",
                       options=[discord.SelectOption(label=str(channel.name)[:25], description=str(channel.id), value=str(channel.id), emoji='🎫')
                                for channel in guild.text_channels[:25]])

    async def callback(self, interaction: discord.Interaction):

        await self.cog._set_ticket_channel(self.guild, interaction, self.base, self.values[0])
        await self.cog._guild_setup(self.guild)

        # Delete View
        message = interaction.message
        await message.edit(view=None)

class TicketRoleSelector(discord.ui.Select):

    def __init__(self, cog, guild, base):
        
        super().__init__(placeholder="Select Your Role",
                       options=[discord.SelectOption(label=str(role.name)[:25], description=str(role.id), value=str(role.id), emoji='🎫')
                                for role in guild.roles[:25]])

        self.cog = cog
        self.guild = guild
        self.base = base

    async def callback(self, interaction: discord.Interaction):

        await self.cog._add_ticket_role(self.guild, interaction, self.base, self.values[0])
        await self.cog._guild_setup(self.guild)

        # Delete View
        message = interaction.message
        await message.edit(view=None)
        

class TicketRoleSelectorView(discord.ui.View):

    def __init__(self, cog, guild, base):
        super().__init__(timeout=None)

        self.add_item(TicketRoleSelector(cog, guild, base))

class SingleTicketManager(discord.ui.Button["Cancel"]):

    def __init__(self, cog, guild, type, channel, member):

        super().__init__(style=discord.ButtonStyle.red, label="Close Ticket", emoji=None)

        # Define Variables
        self.cog = cog
        self.guild = guild
        self.ticketType = type
        self.channel = channel
        self.member = member

    async def callback(self, interaction: discord.Interaction):

        # Close Ticket
        await self.cog._delete_ticket(self.guild, self.channel, self.member, self.ticketType)

class SingleTicketManagerView(discord.ui.View):

    def __init__(self, cog, guild, type, channel, member):
        super().__init__(timeout=None)

        self.add_item(SingleTicketManager(cog, guild, type, channel, member))

class TicketOptionSelector(discord.ui.Select):

    def __init__(self, cog, guild, type, channel, member, options, questionTypes):
        super().__init__(placeholder="Select Your " + cog.names[type] + " Option",
                         options=[discord.SelectOption(label=option["name"], description=option["description"], value=option["name"], emoji=option["emoji"])
                                 for option in options])

        self.cog = cog
        self.guild = guild
        self.ticketType = type
        self.channel = channel
        self.member = member
        self.ticketOptions = options.pop()
        self.questionTypes = questionTypes

    async def callback(self, interaction: discord.Interaction):

        # Check if Cancel
        if self.values[0] == "Cancel":
            await self.cog._delete_ticket(self.guild, self.channel, self.member, self.ticketType)
            return
        else:
            self.subType = self.values[0]
            view = SingleTicketManagerView(self.cog, self.guild, self.ticketType, self.channel, self.member)
            await interaction.message.edit(view=view)

        # Check for Question Type Callback
        if self.ticketType in self.questionTypes:

            # Process Response Ticket
            await self.cog._process_response_ticket(self.guild, self.channel, self.ticketType, self.member, self.questionTypes, 0)
            

class TicketOptionSelectorView(discord.ui.View):

    def __init__(self, cog, guild, type, channel, member, options, questionTypes):

        super().__init__(timeout=None)

        self.add_item(TicketOptionSelector(cog, guild, type, channel, member, options, questionTypes))

class SubmitResponse(discord.ui.Button["Submit"]):

    def __init__(self, cog, guild, ticketType, member, iteration, iterTotal):
        super().__init__(style=discord.ButtonStyle.green, label="Next Step " + iteration + "/" + iterTotal if iteration < iterTotal else "Finish " + ticketType.replace("_", " ").capitalize(), emoji=cog.emojis[ticketType])

        # Define Variables
        self.cog = cog
        self.guild = guild
        self.ticketType = ticketType
        self.member = member

    async def callback(self, interaction: discord.Interaction):

        # Define Variables
        message = interaction.message
        channel = message.channel

        # Load Configuration
        config = self.cog.bot.get_config(self.guild)
        tickets = getattr(self.cog, str(self.guild.id) + "CONFIG")

        # Define Variables
        name = str(self.member.display_name) + "-" + self.cog.names[self.ticketType].lower().replace(" ", "-")
        ticketID = name + "-" + str(self.member.id)

        # Load Response
        responseID = int(tickets.get(ticketID, "iterationMessageID"))
        managerID = int(tickets.get(ticketID, "manager"))
        response = await channel.fetch_message(responseID)
        manager = await channel.fetch_message(managerID)

        # Remove IterationID
        tickets.remove_option(ticketID, "iterationMessageID")

        # Update Responses
        if ticketID in self.cog.questionResponses:
            responses = self.cog.questionResponses[ticketID]
        else:
            responses = {}
        iteration = int(tickets.get(ticketID, "iteration"))
        responses[iteration] = response.content
        self.cog.questionResponses[ticketID] = responses

        setattr(self.cog, str(self.guild.id) + "CONFIG", tickets)

        # Remove View & Message
        await response.delete()
        await manager.delete()
        await message.delete()

        # Update Responses
        tickets.set(ticketID, "responses", dumps(responses))

        # Process Next Ticket
        questionTypes = self.cog.default_questions
        for option in config["tickets"]:
            if option.endswith("_questions"):
                questions = loads(config.get("tickets", option))
                questionTypes[option.replace("_questions", "")] = questions
        await self.cog._process_response_ticket(self.guild, channel, self.ticketType, self.member, questionTypes, iteration + 1)
    
class SubmitResponseView(discord.ui.View):

    def __init__(self, cog, guild, ticketType, member, iteration, iterTotal):
        super().__init__(timeout=None)

        # Add Submit Button
        submit = SubmitResponse(cog, guild, ticketType, member, iteration, iterTotal)
        self.add_item(submit)

class TicketManager(discord.ui.View):

    def __init__(self, cog, guild):
        super().__init__(timeout=None)

        # Define Variables
        self.guild = guild

        for type in cog.types:
            if cog._has_ticket_type(guild, type):
                button = TicketButton(cog, guild, type)
                self.add_item(button)

class TicketButton(discord.ui.Button["Ticket"]):

    def __init__(self, cog, guild, ticketType):

        super().__init__(style=discord.ButtonStyle.green, label=cog.names[ticketType], emoji=cog.emojis[ticketType])

        # Define Variables
        self.guild = guild
        self.cog = cog
        self.ticketType = ticketType

    async def callback(self, interaction: discord.Interaction):

        await self.cog._create_ticket_channel(self.guild, self.ticketType, interaction.user)


# Tickets Module Class #
class Tickets(commands.Cog):

    def __init__(self, bot):

        # Define Variables
        self.bot = bot
        self.prefix = "?"
        self.ticketTypes = {}
        self.types = {"support": True, "bug_report": False, "suggestion": False}
        self.names = {"support": "Support Ticket", "bug_report": "Bug Report", "suggestion": "Suggestion"}

        supportEmoji = str("\N{ENVELOPE}")
        bugEmoji = str("\N{LADY BEETLE}")
        suggestionEmoji = str("\N{ELECTRIC LIGHT BULB}")
        self.emojis = {"support": supportEmoji, "bug_report": bugEmoji, "suggestion": suggestionEmoji}
        
        self.descriptions = {
            "support": "If you need general support or help figuring things out or if you're having an issue.",
            "bug_report": "If you've found a problem and you wish to report it to us.",
            "suggestion": "If you've got an idea for us you can submit it here."
        }
        
        self.default_questions = {
            "bug_report": [
                ["Describe the issue to us?", "Please include a brief explanation about the issue you are experiencing."],
                ["Provide Details, Examples, Demonstrations, etc.", "Here you can go in length as to where you are and what you were doing to cause this bug, you can also submit links of videos/screenshots to help identify the bug."]
            ],
            "suggestion": [
                ["What\'s Your Idea?", "Please include a brief explanation of what your idea is!"],
                ["How Would It Work?", "Tell us how your idea would work and also fit within to our existing content if applicable."]
            ]
        }

        joystickEmoji = str("\N{JOYSTICK}")
        earthEmoji = str("\N{Earth Globe Asia-Australia}")
        self.default_options = {
            "support": [
                {
                    "name": "General Support",
                    "description": "If you're in need or general support or no other option applies.",
                    "emoji": supportEmoji,
                    "response": "Thanks for opening a support ticket, a member from our team will be with you as soon as possibly available, for now please tell us how we can help.",
                },
                {
                    "name": "In-Game Support",
                    "description": "Experienced a gameplay problem that resulted in a loss?",
                    "emoji": joystickEmoji,
                    "response": "Thanks for opening a ticket, we're sorry that this issue happened and will try to fix it for you as soon as possible. If there isn't one already we would also ask you open a new bug report to help track the issue."
                }
            ],
            "bug_report": [
                {
                    "name": "In-Game Bug",
                    "description": "The bug/problem is being experienced in-game.",
                    "emoji": "Thanks for opening a ticket, we're sorry that this issue happened and will try to fix it for you as soon as possible."
                },
                {
                    "name": "Website Bug",
                    "description": "The bug/problem is experienced when using our website.",
                    "emoji": "Thanks for opening a ticket, we're sorry that this issue happened and will try to fix it for you as soon as possible."
                }
            ],
            "suggestion": [
                {
                    "name": "In-Game Suggestion",
                    "description": "Got an idea for us to add to our game?",
                    "emoji": joystickEmoji
                },
                {
                    "name": "Website Suggestion",
                    "description": "Got an idea for our website?",
                    "emoji": earthEmoji
                },
                {
                    "name": "Other Suggestion",
                    "description": "If your suggestion doesn't fit into this category.",
                    "emoji": suggestionEmoji
                }
            ]
        }
        self.options = {}

        self.default_responses = {
            "support": "Thanks for opening a support ticket. Please use the dropbox below to select the type of support you need in order to continue, otherwise you can cancel and close the ticket.",
            "bug_report": "Thanks for opening a bug report and bringing this issue to our concern, we look forward to providing a smooth experience for all and squashing bugs ensures optimal usage. Please use the dropbox below to specify in which area your bug occured, otherwise you can cancel and close the report.",
            "suggestion": "Thanks for opening a new suggestion, we're always looking for new and exciting ideas to add and we're excited for what you have to share with us. Just use the dropdown below to select your type of suggestion, otherwise you can close and cancel this suggestion ticket."
        }
        self.responses = {}
        self.questionResponses = {}

    async def cog_check(self, ctx):
        prefix = getattr(ctx.cog, "prefix", None)
        if prefix is not None:
            return ctx.prefix == prefix
        else:
            return True

    @commands.Cog.listener()
    async def on_ready(self):
        # Setup All Guilds With Tickets
        for guild in self.bot.guilds:
            if self.bot._has_feature(guild, "tickets"):
                await self._guild_setup(guild)

    @commands.command()
    async def add_ticket_role(self, ctx, base = None):
        if base == None:
            await self.bot.guild_debug(guild, ":tickets: Please specify the ticket type you wish to add a role to.")
        if ctx.message.author.guild_permissions.administrator:

            # Define Variables
            guild = ctx.message.author.guild

            # Send Ticket Channel View
            view = TicketRoleSelectorView(self, guild, base)
            await self.bot.guild_debug(guild, ":tickets: Please sepcify a ticket channel.", view=view)
        else:
            self.bot._permission_denied(ctx)          

    async def _add_ticket_role(self, guild, interaction, base, roleID):

       # Define Variables
       role = guild.get_role(int(roleID))

       if role == None:
           print("Fuck")
           print(roleID)

       if base == "ticket": 
           await interaction.response.send_message("Setting ticket channel to " + role.mention)
       else:
           await interaction.response.send_message("Setting response channel for " + base + " to " + role.mention)

       # Load Configuration
       config = self.bot.get_config(guild)

       # Set Ticket Channel
       if base == "ticket":
           roles = loads(config.get("tickets", "roles"))
           roles.append(role)
           config.set("tickets", "roles", dumps(roles))
       else:
           roles = loads(config.get("tickets", base + "_roles"))
           roles.append(role.id)
           config.set("tickets", base + "_roles", dumps(roles))

       # Save Config
       await self.bot._save_config(guild)

    @commands.command()
    async def set_ticket_channel(self, ctx):
        if ctx.message.author.guild_permissions.administrator:

            # Define Variables
            guild = ctx.message.author.guild

            # Send Ticket Channel View
            view = TicketSelectorView(self, guild, "ticket")
            await self.bot.guild_debug(guild, ":tickets: Please sepcify a ticket channel.", view=view)
        else:
            self.bot._permission_denied(ctx)          

    async def _set_ticket_channel(self, guild, interaction, base, channelID):

       # Define Variables
       channel = await guild.fetch_channel(channelID)

       if base == "ticket": 
           await interaction.response.send_message("Setting ticket channel to " + channel.mention)
       else:
           await interaction.response.send_message("Setting response channel for " + base + " to " + channel.mention)

       # Load Configuration
       config = self.bot.get_config(guild)

       # Set Ticket Channel
       if base == "ticket":
           config.set("tickets", "channel", str(channelID))
       else:
           config.set("tickets", base + "_channel", str(channelID))
       # Check if Channel has Parent Category
       if channel.category != None and base == "ticket":
           config.set("tickets", "category", str(channel.category_id))

       # Save Config
       await self.bot._save_config(guild)

    async def _submit_response_ticket(self, guild, channel, type, member, questionTypes):

        # Load Configuration
        config = self.bot.get_config(guild)
        tickets = getattr(self, str(guild.id) + "CONFIG")

        # Define Variables
        name = str(member.display_name) + "-" + self.names[type].lower().replace(" ", "-")
        ticketID = name + "-" + str(member.id)

        # Load Submission Channel
        submitChannelID = int(config.get("tickets", type + "_channel"))
        submitChannel = await guild.fetch_channel(submitChannelID)

        # Setup Embed
        embed = discord.Embed(
            title="New " + type.replace("_", " ").capitalize() + " From " + member.display_name,
            colour=0x00bcff,
            description="We've just received a new " + type.replace("_", " ") + "."
        )

        # Process Responses
        responses = loads(tickets.get(ticketID, "responses"))
        questions = questionTypes[type]
        for responseID in responses:
            response = responses[responseID]
            responseID = int(responseID)
            question = questions[responseID][0]
            embed.add_field(name=question, value=response, inline=False)

        # Submit Suggestion
        await submitChannel.send(embed=embed)

        # Close Existing Ticket
        await self._delete_ticket(guild, channel, member, type)

    async def _process_response_ticket(self, guild, channel, type, member, questionTypes, iteration):

        # Load Configuration
        config = self.bot.get_config(guild)
        tickets = getattr(self, str(guild.id) + "CONFIG")

        # Define Variables
        name = str(member.display_name) + "-" + self.names[type].lower().replace(" ", "-")
        ticketID = name + "-" + str(member.id)

        # Setup Iteration Manager
        questions = questionTypes[type]
        try:
            question = questions[iteration]
            embed = discord.Embed(colour=0x00bcff, title=question[0], description=question[1])

            manager = await channel.send(embed=embed)

            # Update Configuration With Manager
            tickets.set(ticketID, "manager", str(manager.id))
            tickets.set(ticketID, "iteration", str(iteration))
            tickets.set(ticketID, "responses", "{}")

            return
        except IndexError:
            pass

        # End of Ticket
        await self._submit_response_ticket(guild, channel, type, member, questionTypes)
        
    @commands.Cog.listener()
    async def on_message(self, message):

        # Define Variables
        author = message.author
        channel = message.channel
        guild = channel.guild
        if author.id == self.bot.id:
            return
        if channel.id not in self.ticketTypes:
            return
        type = self.ticketTypes[channel.id]

        name = str(author.display_name) + "-" + self.names[type].lower().replace(" ", "-")
        ticketID = name + "-" + str(author.id)

        config = self.bot.get_config(guild)
        tickets = getattr(self, str(guild.id) + "CONFIG")

        # Callback
        if ticketID not in tickets:
            return

        # Too Early
        if type in self.default_questions:
            if not tickets.has_option(ticketID, "manager"):
                await message.delete()
                return

        # Check if Not Already Sent
        if not tickets.has_option(ticketID, "iterationMessageID"):

            tickets.set(ticketID, "iterationMessageID", str(message.id))

            # Define Iter Variables
            iteration = int(tickets.get(ticketID, "iteration")) + 1
            iterTotal = len(loads(config.get("tickets", type + "_questions")))

            setattr(self, str(guild.id) + "CONFIG", tickets)

            # Send Submission Check
            view = SubmitResponseView(self, guild, type, author, str(iteration), str(iterTotal))
            await channel.send("Are you sure you would like to submit this response? If you would like to add more or update your answer please edit your message.", view=view)

    async def _create_ticket_channel(self, guild: discord.Guild, type, member: discord.Member):

        # Load Configuration
        config = self.bot.get_config(guild)
        tickets = getattr(self, str(guild.id) + "CONFIG")
        
        saveRequired = False

        # Define Variables
        name = str(member.display_name) + "-" + self.names[type].lower().replace(" ", "-")

        # Check if Ticket Already Open
        ticketID = name + "-" + str(member.id)
        if tickets.has_section(ticketID):

            # Identify Ticket Channel
            try:
                
                channel = await guild.fetch_channel(int(tickets.get(ticketID, "channel")))

                # Notify Member of Existing Channel
                await channel.send(member.mention + " you already have this " + self.names[type].lower() + " open. Please close or finish this before opening a new one.")
                return
            except discord.errors.NotFound:

                # Channel Deleted So Reset Section
                tickets.remove_section(ticketID)
                tickets.add_section(ticketID)
        else:

            # Add New Ticket to Config
            tickets.add_section(ticketID)

        # Check if Category Exists
        category = None
        if config.has_option("tickets", "category"):
            try:
                category = await guild.fetch_channel(int(config.get("tickets", "category")))
            except NotFoundException:
                config.remove_option("tickets", "category")
                saveRequired = True

        # Create New Ticket Channel
        if category:
            channel = await guild.create_text_channel(name, category=category)
        else:
            channel = await guild.create_text_channel(name)
        tickets.set(ticketID, "channel", str(channel.id))
        self.ticketTypes[channel.id] = type

        # Permissions Setup
        await channel.set_permissions(guild.default_role, send_messages=False, read_messages=False)
        await channel.set_permissions(member, send_messages=True, read_messages=True)

        if config.has_option("tickets", str(type) + "_roles"):
            roleIDs = loads(config.get("tickets", str(type) + "_roles"))
            for roleID in roleIDs:
                role = guild.get_role(int(roleID))
                await channel.set_permissions(role, send_messages=True, read_messages=True)

                # Send Phantom Ping
                ping = await channel.send(role.mention)
                await ping.delete()

        embed = None
        if guild in self.responses:
            allResponses = self.responses[guild]
            if isinstance(allResponses, str):
                allResponses = loads(allResponses)
            if type in allResponses:
                description = allResponses[str(type)]
                embed = discord.Embed(
                    title=str(member.display_name) + "'s " + self.names[type],
                    colour=0x00bcff,
                    description=description
                )

        if embed == None:
            embed = discord.Embed(
                title=str(member.display_name) + "'s " + self.names[type],
                colour=0x00bcff,
                description="Please select an option from the dropbox below."
            )

        # Ticket Setup
        questionTypes = self.default_questions
        for option in config["tickets"]:
            if option.endswith("_questions"):
                questions = loads(config.get("tickets", option))
                questionTypes[option.replace("_questions", "")] = questions
        managerSent = False
        if guild in self.options:
            allOptions = self.options[guild]
            if type in allOptions:
                options = allOptions[type]
                if isinstance(options, str):
                    options = loads(options)

                cancelEmoji = str("\N{NO ENTRY SIGN}")
                cancel = {
                    "name": "Cancel",
                    "description": "This will close and cancel the ticket.",
                    "emoji": cancelEmoji
                    }
                options.append(cancel)

                selector = TicketOptionSelectorView(self, guild, type, channel, member, options, questionTypes)

                await channel.send(embed=embed, view=selector)
                managerSent = True

        if not managerSent:
            await channel.send(embed=embed)

        # Check if Save Required
        if saveRequired:
            self.bot.update_config(guild, config)
            await self.bot._save_config(guild)

    async def _delete_ticket(self, guild, channel, member, type):

        # Load Configuration
        tickets = getattr(self, str(guild.id) + "CONFIG")

        # Define Variables
        name = str(member.display_name) + "-" + self.names[type].lower().replace(" ", "-")
        ticketID = name + "-" + str(member.id)

        # Cleanup
        tickets.remove_section(ticketID)

        # Delete Channel
        await channel.delete()

    async def _guild_setup(self, guild):

        # Setup Default User Configuration
        guildTicketsFile = "guilds/" + str(guild.id) + "/tickets.rcf"

        # Create If Not Exists
        if not os.path.exists(guildTicketsFile):
            newFile = open(guildTicketsFile, "w")
            newFile.close()

        # Load Configuration
        guildConfig = self.bot.get_config(guild)
        
        config = ConfigParser()
        config.read(guildTicketsFile)
        setattr(self, str(guild.id) + "CONFIG", config)

        # Debug Output
        await self.bot.guild_debug(guild, ":tickets: Intializing tickets system...")

        # Process All Ticket Types
        saveRequired = False
        if not guildConfig.has_section("tickets"):
            guildConfig.add_section("tickets")
            saveRequired = True
        for ticketType in self.types:
            enabled = str(self.types[ticketType])
            
            if not guildConfig.has_option("tickets", ticketType):
                guildConfig.set("tickets", ticketType, enabled)
                saveRequired = True

            if not guildConfig.has_option("tickets", ticketType + "_roles"):
                guildConfig.set("tickets", ticketType + "_roles", dumps([]))
                saveRequired = True
                
            if ticketType in self.default_questions:
                if not guildConfig.has_option("tickets", ticketType + "_questions"):
                    questions = dumps(self.default_questions[ticketType])
                    guildConfig.set("tickets", ticketType + "_questions", questions)
                    saveRequired = True
            elif guildConfig.has_option("tickets", ticketType + "_questions"):
                guildConfig.remove_option("tickets", ticketType + "_questions")
                saveRequired = True
                
            if ticketType in self.default_options:
                if not guildConfig.has_option("tickets", ticketType + "_options"):
                    options = dumps(self.default_options[ticketType])
                    guildConfig.set("tickets", ticketType + "_options", options)
                    saveRequired = True
                else:
                    options = loads(guildConfig.get("tickets", ticketType + "_options"))
                if guild in self.options:
                    allOptions = self.options[guild]
                else:
                    allOptions = {}
                allOptions[ticketType] = options
                self.options[guild] = allOptions

        if not guildConfig.has_option("tickets", "responses"):
            responses = dumps(self.default_responses)
            guildConfig.set("tickets", "responses", responses)
            saveRequired = True
        else:
            responses = loads(guildConfig.get("tickets", "responses"))
        self.responses[guild] = responses

        # Check if Contains Channel Yet
        if not guildConfig.has_option("tickets", "channel"):
            view = TicketSelectorView(self, guild, "ticket")
            await self.bot.guild_debug(guild, ":tickets: Please sepcify a ticket channel.", view=view)
        else:
            print("PASSS")
            # Check if for Required Submission Channels
            supportedTypes = list(self.default_questions.keys())
            for option in guildConfig["tickets"]:
                if option.endswith("_questions"):
                    supportedTypes.append(option.replace("_questions", ""))
            for supportedType in supportedTypes:
                if not guildConfig.has_option("tickets", supportedType + "_channel"):
                    view = TicketSelectorView(self, guild, supportedType)
                    await self.bot.guild_debug(guild, ":tickets: Please specify a response channel for the ticket type: `" + supportedType + "`", view=view)
                    return
                else:
                    # Verify Channel Still Exists
                    channelID = guildConfig.get("tickets", supportedType + "_channel")
                    try:
                        await guild.fetch_channel(channelID)
                    except discord.errors.NotFound:
                        view = TicketSelectorView(self, guild, supportedType)
                        await self.bot.guild_debug(guild, ":tickets: Please specify a response channel for the ticket type: `" + supportedType + "`", view=view)
                        return
                    
            # Define Variables
            channel = await guild.fetch_channel(guildConfig.get("tickets", "channel"))

            # Setup Ticket Embed
            embed = discord.Embed(
                title="",
                colour=0x00bcff,
                description="Please select from the following options based on your needs."
            )

            for type in self.types:
                if self._has_ticket_type(guild, type):
                    embed.add_field(name=self.emojis[type] + " " + self.names[type], value=self.descriptions[type], inline=False)

            # Check for Existing Manager
            # Check if Manager Deployed
            if guildConfig.has_option("tickets", "manager"):

                # Check if Manager Not Deleted
                channel = await guild.fetch_channel(int(guildConfig.get("tickets", "channel")))
                try:
                    manager = await channel.fetch_message(int(guildConfig.get("tickets", "manager")))

                    await manager.edit(embed=embed, view=TicketManager(self, guild))
                except discord.errors.NotFound:
                    pass
                
            else:

                manager = await channel.send(embed=embed, view=TicketManager(self, guild))

                guildConfig.set("tickets", "manager", str(manager.id))
                saveRequired = True
        

        # Check if Required Saving
        if saveRequired:
            self.bot.update_config(guild, config)
            await self.bot._save_config(guild)

        # Debug Finish
        await self.bot.guild_debug(guild, ":tickets: Tickets system now successfully enabled.")

    def _has_ticket_type(self, guild, type):

        # Load Configuration
        config = self.bot.get_config(guild)

        if config.get("tickets", type) == "True":
            return True
        return False
    
async def setup(bot):

    # Add Ticket Cog to Bot
    cog = Tickets(bot)

    # Update Recorded Cogs
    bot.recordedCogs.update(dict(tickets=cog))
    
    await bot.add_cog(cog)

    
