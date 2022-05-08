import discord
from discord.ext import commands
import RaidedGW2.app as gw2
import asyncio
import datetime

bossThumbnails = {
    "Vale Guardian": "https://wiki.guildwars2.com/images/f/fb/Mini_Vale_Guardian.png",
    "Gorseval the Multifarious": "https://wiki.guildwars2.com/images/d/d1/Mini_Gorseval_the_Multifarious.png",
    "Sabetha the Saboteur": "https://wiki.guildwars2.com/images/5/54/Mini_Sabetha.png",
    "Slothasor": "https://wiki.guildwars2.com/images/1/12/Mini_Slothasor.png",
    "Matthias Gabrel": "https://wiki.guildwars2.com/images/5/5d/Mini_Matthias_Abomination.png",
    "Keep Construct": "https://wiki.guildwars2.com/images/e/ea/Mini_Keep_Construct.png",
    "Xera": "https://wiki.guildwars2.com/images/4/4b/Mini_Xera.png",
    "Cairn the Indomitable": "https://wiki.guildwars2.com/images/b/b8/Mini_Cairn_the_Indomitable.png",
    "Mursaat Overseer": "https://wiki.guildwars2.com/images/c/c8/Mini_Mursaat_Overseer.png",
    "Samarog": "https://wiki.guildwars2.com/images/f/f0/Mini_Samarog.png",
    "Deimos": "https://wiki.guildwars2.com/images/e/e0/Mini_Ragged_White_Mantle_Figurehead.png",
    "Soulless Horror": "https://wiki.guildwars2.com/images/d/d4/Mini_Desmina.png",
    "Dhuum": "https://wiki.guildwars2.com/images/e/e4/Mini_Dhuum.png",
    "Conjured Amalgamate": "https://wiki.guildwars2.com/images/d/d6/Conjured_Amalgamate_Shield.png",
    "Nikare": "https://wiki.guildwars2.com/images/e/e6/Mini_Nikare.png",
    "Qadim": "https://wiki.guildwars2.com/images/f/f2/Mini_Qadim.png",
    "Cardinal Adina": "https://wiki.guildwars2.com/images/a/a0/Mini_Earth_Djinn.png",
    "Cardinal Sabir": "https://wiki.guildwars2.com/images/f/fc/Mini_Air_Djinn.png",
    "Qadim the Peerless": "https://wiki.guildwars2.com/images/8/8b/Mini_Qadim_the_Peerless.png",
    "M A M A": "https://wiki.guildwars2.com/images/6/65/Mini_Clockheart.png",
    "Siax the Corrupted": "https://wiki.guildwars2.com/images/3/31/Mini_Toxic_Nimross.png",
    "Ensolyss of the Endless Torment": "https://wiki.guildwars2.com/images/thumb/5/5e/Mini_Toxic_Hybrid.png/40px-Mini_Toxic_Hybrid.png",
    "Skorvald the Shattered": "https://wiki.guildwars2.com/images/9/9d/Mini_Accumulated_Ley_Energy.png",
    "Artsariiv": "https://wiki.guildwars2.com/images/c/c5/Mini_Captain_Grumby.png",
    "Arkk": "https://wiki.guildwars2.com/images/3/3a/Mini_Tixx.png",
    "Elemental Ai, Keeper of the Peak": "https://wiki.guildwars2.com/images/c/c5/Mini_Captain_Grumby.png",
    "Dark Ai, Keeper of the Peak": "https://wiki.guildwars2.com/images/c/c5/Mini_Captain_Grumby.png",
}

class LogUploader(commands.Cog):
    def __init__(self, bot: commands.Bot, teams: list):
        self.bot = bot
        self.teams = teams
        self.threads = {}

    @commands.command()
    async def upload(self, ctx, team):
        # Check the team
        if team in self.teams:  # Valid team name
            thread = await ctx.message.start_thread(
                name=f"Upload for {gw2.teamNames[self.teams.index(team)]}",
                auto_archive_duration=60,
            )
            self.threads[thread.id] = (thread, Uploader(team))
            self.greeterButton = UploadGreeter(self, ctx.author)
            await thread.send("Waiting on logs.", view=self.greeterButton)

        else:  # invalid team name
            await ctx.send(f"Invalid team: {team}")

    async def stopUploads(self, threadID):
        thread = self.threads[threadID][0]
        # Disable all deleters
        print(f"Disabling deleters, {thread}")
        uploads = self.threads[threadID][1]
        await uploads.disableAllDeleters()

        # Generate summary statistics
        print(f"Generating summary statistics, {thread}")
        await self.threads[threadID][0].send(embed=uploads.completionEmbed())

        # Archive thread
        print(f"Archiving thread, {thread}")
        await self.threads[threadID][0].edit(archived=True, locked=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel in [thread[0] for thread in self.threads.values()]:
            # Check if there is a valid attachment
            if (
                len(log := message.attachments) == 1
                and (log := log[0]).filename.split(".")[1] == "zevtc"
            ):
                embed = discord.Embed(
                    title="Parsing",
                    description="Log is parsing.",
                    color=discord.Colour.blue(),
                )
                statusMsg = await message.reply(embed=embed)
                await log.save("uploads/" + log.filename)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    gw2.uploadLog,
                    log.filename,
                    self.threads[message.channel.id][1].team,
                    gw2.db,
                )
                if result["success"]:
                    # Save result
                    self.threads[message.channel.id][1].logs += [result]

                    # Build url for embed
                    raidedLink = f"https://andrexia.com/raidReport?boss={result['boss']}&encID={result['encID']}"

                    # Build embed for success
                    embed.colour = discord.Colour.green()
                    embed.title = gw2.bossIDs[result["boss"]]
                    embed.description = result["message"]
                    embed.timestamp = datetime.datetime.fromtimestamp(
                        result["date"]
                    ).astimezone(datetime.timezone.utc)
                    embed.set_thumbnail(
                        url=bossThumbnails[gw2.bossIDs[result["boss"]]]
                    )
                    embed.url = raidedLink
                    durStr = f"{int(result['duration'] // 60)}m {int(result['duration'] % 60)}s"
                    embed.add_field(name="Duration", value=durStr)

                    # Build UI for deletion
                    logDeleter = uploadDeleter(
                        self.greeterButton.owner,
                        result["encID"],
                        embed,
                        self.threads[message.channel.id][1],
                    )

                    # Update msg
                    await statusMsg.edit(
                        content=result["permalink"],
                        embed=embed,
                        view=logDeleter,
                    )
                    logDeleter.msg = statusMsg

                    # Save deleter for later
                    self.threads[message.channel.id][1].deleterViews += [
                        logDeleter
                    ]
                else:
                    embed.colour = discord.Colour.red()
                    embed.title = "Failed"
                    embed.description = result["message"]
                    await statusMsg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_thread_remove(self, thread):
        if thread in [thread[0] for thread in self.threads.values()]:
            del self.threads[thread.id]

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        if thread in [thread[0] for thread in self.threads.values()]:
            del self.threads[thread.id]

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        if after.id in [thread[0].id for thread in self.threads.values()]:
            if before.archived == False and after.archived == True:
                del self.threads[after.id]


class UploadGreeter(discord.ui.View):
    def __init__(self, cog, owner):
        super().__init__()
        self.cog = cog
        self.owner = owner

    async def interaction_check(self, interaction):
        return self.owner == interaction.user

    @discord.ui.button(
        label="Stop uploading", style=discord.ButtonStyle.danger
    )
    async def stopUploads(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        button.disabled = True
        button.label = "Uploads stopped"
        await interaction.message.edit(content="Uploads stopped.", view=self)
        self.stop()
        await self.cog.stopUploads(interaction.channel.id)


class uploadDeleter(discord.ui.View):
    def __init__(self, owner, id, embed, uploader):
        super().__init__()
        self.owner = owner
        self.id = id
        self.embed = embed
        self.uploader = uploader
        self.msg = None

    async def interaction_check(self, interaction):
        return self.owner == interaction.user

    @discord.ui.button(label="Delete log", style=discord.ButtonStyle.danger)
    async def deleteUpload(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        print(f"Deleting log id: {self.id}")
        # Delete from database
        gw2.deleteEncounter(self.id, gw2.db)

        # Create message
        print(f"Modifying embed: {self.embed}")
        self.embed.description = "Data deleted."
        self.embed.colour = discord.Colour.red()
        button.disabled = True
        button.label = "Log deleted"
        await interaction.message.edit(embed=self.embed, view=self)

        # Delete from completion log
        print("Removing log from Uploader class")
        self.uploader.deleteLog(self.id)

        # Kill interactions
        print("Stopping interaction")
        self.stop()


class Uploader:
    def __init__(self, team):
        self.team = team
        self.logs = []
        self.deleterViews = []

    async def disableAllDeleters(self):
        for view in self.deleterViews:
            if not view.children[0].disabled:
                view.children[0].disabled = True
                await view.msg.edit(view=view)

    def deleteLog(self, id):
        target = [log for log in self.logs if log["encID"] == id][0]
        targetIdx = self.logs.index(target)
        self.logs.pop(targetIdx)

    def completionEmbed(self):
        totalTime = sum([log["duration"] for log in self.logs])
        durStr = f"{int(totalTime // 60)}m {int(totalTime % 60)}s"
        bossStr = ", ".join([gw2.bossIDs[log["boss"]] for log in self.logs])
        if bossStr == "":
            bossStr = "None"

        embed = discord.Embed(
            title=f"Completion Log - {gw2.teamNames[gw2.teamIDs.index(self.team)]}",
            description=f"Total encounter time: {durStr}",
            url="https://andrexia.com/raidReport",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Kill Count", value=len(self.logs), inline=False)
        embed.add_field(name="Bosses Killed", value=bossStr, inline=False)
        return embed
