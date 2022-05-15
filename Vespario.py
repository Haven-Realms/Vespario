import os

# Detect if Discord.py Installed
try:
    import nextcord
except ModuleNotFoundError:
    os.system("python -m pip install -U nextcord")
    import nextcord

# Import Discord Cogs Providers
from nextcord.ext import commands
from nextcord.utils import oauth_url

# Import Other Modules
from configparser import ConfigParser

    
class Vespario(commands.Bot):

    def __init__(self):
    
        # Vespario Base Properties
        self.prefixes = {}
        self.token = "ODIyMzEzNjM0NDc0MjI5NzYw.YFQdQA.loxBdNquWZqFOX4yvI7DS9P6IAc"
        self.enabled = False
        self.id = "822313634474229760"
        
        # Super Class Override
        super().__init__(command_prefix=commands.when_mentioned_or(self.get_prefix), case_insensitive=True, intents=nextcord.Intents.all())

        # Remove Lib Help
        self.remove_command("help")

        # Setup All Modules
        self.modules = [
            "lib.Core",
            "lib.Moderation",
            "lib.Tickets",
            "lib.Announcements",
            "lib.SelfRoles"
        ]
        self.recordedCogs = {}
        
        # Attempt to Load Modules
        for module in self.modules:
            try:
                self.load_extension(module)
                print(f"Loaded Module: ({module}) Successfully")
            except Exception as e:
                print(f'[{type(e).__name__}] {e}')

        # Run & Connect Token
        self.run(self.token)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            pass
        elif isinstance(error, nextcord.errors.NotFound):
            print("ERROR: FOUND")
            print(type(ctx))
            print(ctx.author)
            print(error)
        else:
            print(error)

    async def on_member_join(self, member):

        await member.guild.system_channel.send("Welcome " + member.mention + " to our community! Please be sure to accept the rules in order to verify and gain full access to our community.")

    async def get_prefix(self, message):
        guild = message.guild

        cogPrefixes = []
        for cog in self.cogs.values():
            if hasattr(cog, "prefix"):
                cogPrefixes.append(cog.prefix)

        try:
            prefix = self.prefixes[guild]
            default_prefix, custom_prefix = '!', prefix
            cogPrefixes.append(default_prefix)
            cogPrefixes.append(custom_prefix)
        except KeyError:
            pass
        return cogPrefixes
        
    async def _setup(self):
    
        # Create Guilds Directory if Not Exists
        if not os.path.exists("guilds"):
            os.mkdir("guilds")

        # Process Guild Setup
        self.guildConfs = {}
        for guild in self.guilds:
            self._setup_guild(guild)

        # Update Presence
        await self._update_presence()

    def _setup_guild(self, guild):

        # Setup Properties
        guildDirectory = str("guilds/" + str(guild.id))

        # Setup Guild Base Directory & Files
        if not os.path.exists(guildDirectory):
            os.mkdir(guildDirectory)
        if not os.path.exists(guildDirectory + "/config.rcf"):
            newGuildConfigFile = open(guildDirectory + "/config.rcf", "w")
            newGuildConfigFile.close()

        # Setup Guild Base Configuration
        guildConfig = ConfigParser()
        guildConfig.read(guildDirectory + "/config.rcf")

        # Check for Updating After Check
        saveRequired = False

        # Check for Default Base Configuration Values
        if not guildConfig.has_section("base"):
            guildConfig.add_section("base")
            saveRequired = True
            
        if not guildConfig.has_option("base", "id"):
            guildConfig.set("base", "id", str(guild.id))
            saveRequired = True
        if not guildConfig.has_option("base", "prefix"):
            guildConfig.set("base", "prefix", "!")
            saveRequired = True

        # Check for Features Configuration Values
        if not guildConfig.has_section("features"):
            guildConfig.add_section("features")

        if not guildConfig.has_option("features", "tickets"):
            guildConfig.set("features", "tickets", "False")
            saveRequired = True
        if not guildConfig.has_option("features", "announcements"):
            guildConfig.set("features", "announcements", "False")
            saveRequired = True
        if not guildConfig.has_option("features", "drops"):
            guildConfig.set("features", "drops", "False")
            saveRequired = True
        if not guildConfig.has_option("features", "giveaways"):
            guildConfig.set("features", "giveaways", "False")
            saveRequired = True
        if not guildConfig.has_option("features", "moderation"):
            guildConfig.set("features", "moderation", "True")
            saveRequired = True
        if not guildConfig.has_option("features", "self-roles"):
            guildConfig.set("features", "self-roles", "False")
            saveRequired = True

        # Check if Save & Update Config
        if saveRequired:
            with open(guildDirectory + "/config.rcf", "w") as confFile:
                guildConfig.write(confFile)
                confFile.close()

        # Setup Guild Prefix
        prefix = guildConfig.get("base", "prefix")
        self.prefixes[guild] = prefix

        # Append Configuration Object
        setattr(self, str(guild.id) + "CONFIG", guildConfig)

    def _has_feature(self, guild, feature):

        # Get Guild Configuration
        config = self.get_config(guild)

        # Check if Feature Enabled
        enabled = False
        if config.has_option("features", feature):
            if config.get("features", feature) == "True":
                enabled = True
            
        return enabled

    async def _enable_feature(self, guild, feature):

        # Get Guild Configuration
        config = self.get_config(guild)

        # Enable Feature
        config.set("features", feature, "True")

        # Attempt to Identify Cog
        if feature in self.recordedCogs:
            cog = self.recordedCogs[feature]

            # Attempt to Run Cog Guild Setup
            print("running cog setup")
            await cog._guild_setup(guild)

            # Save Guild Configuration
            await self._save_config(guild)
        

    async def _disable_feature(self, guild, feature):

        # Get Guild Configuration
        config = self.get_config(guild)

        # Disable Feature
        config.set("features", feature, "False")

    async def _reload_config(self, guild):

        # Grab Current Configuration
        try:
            guildConfig = self.guildConfs[guild]
        except KeyError:
            guildConfig = ConfigParser()
        guildConfig.read("guilds/" + str(guild.id) + "/config.rcf")

        # Update Configuration to Master
        self.guildConfs[guild] = guildConfig

    async def _save_config(self, guild):

        # Grab Current Configuration
        guildConfig = getattr(self, str(guild.id) + "CONFIG")

        # Save Configuration to File
        with open("guilds/" + str(guild.id) + "/config.rcf", "w") as configFile:
            guildConfig.write(configFile)

    def config_has_section(self, guild, section):
        return self.guildConfs[guild].has_section(section)
    def config_has_option(self, guild, section, option):
        return self.guildConfs[guild].has_option(section, option)
    def config_set(self, guild, section, option, value):
        return self.guildConfs[guild].set(section, option, value)
    def config_get(self, guild, section, option):
        return self.guildConfs[guild].set(section, option)

    def get_config(self, guild):

        # Grab Current Configuration
        guildConfig = getattr(self, str(guild.id) + "CONFIG")

        return guildConfig

    def update_config(self, guild, config):

        pass

    def get_bot_channel(self, guild):

        # Get Configuration
        config = self.get_config(guild)

        # Check for Bot Channel
        if config.has_option("base", "bot_channel"):
            id = config.get("base", "bot_channel")
            channel = guild.get_channel(int(id))
            return channel
        return None

    async def guild_debug(self, guild, message, **kwargs):

        channel = self.get_bot_channel(guild)
        if channel != None:
            await channel.send(message, **kwargs)

    async def on_ready(self):

        # Bot Status
        self.enabled = True

        # Setup Bot
        await self._setup()

        # Update Servers of Status
        for guild in self.guilds:
            await self.guild_debug(guild, ":green_circle: Vespario is now online.")

        print("Vespario Bot Version 1.2")
        print("Now Active & Running on " + str(len(self.guilds)) + " Discord Servers")
        print("--------------------------\n")
        print("Invite Vespario to Your Server Here:")
        print(oauth_url(self.id))
        
    async def _update_presence(self):
        
        # Calculate Guilds Count
        count = str(len(self.guilds)-1)
        
        # Update Presence Status
        await self.change_presence(activity = nextcord.Activity(type=nextcord.ActivityType.watching, name=" over " + count + " other servers."))

    async def _permission_denied(self, ctx):
        await ctx.send("Sorry, but you do not have permission to perform that command. If this is an error please try consulting and administrator.")

if __name__ == "__main__":
    bot = Vespario()
