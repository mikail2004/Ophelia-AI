import traceback
import datetime
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from firebase_admin import db
from modelMV4 import *
import os
from dotenv import load_dotenv

#import logging
#import botLogger
#logger = logging.getLogger(__name__) #initiates logger

#Setting environment variables and secret keys
load_dotenv()
TOKEN = os.getenv('TOKEN_KEY')
MAIN_GUILD_ID = int(os.getenv('MAIN_GUILD_ID')) #Guild ID for Ophelia's main server
category_id = int(os.getenv('CATEGORY_ID')) #ID for User Channel category in main server
ABD_ID = int(os.getenv('ABD_ID'))
MOK_ID = int(os.getenv('MOK_ID'))

intents = discord.Intents.all() # Change once out of dev ~~~~

bot = commands.Bot(command_prefix="~", intents = intents)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#      Bot initiation and housekeeping
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

#Initiates the bot
@bot.event
async def on_ready():
    await bot.tree.sync() # Remove once out of dev to avoid rate limits (Use Sync command below) ~~~~~
    print(f'Logged in as {bot.user}')

#Syncs slash commands with all servers
@bot.tree.command(name='sync', description='Owner only') # Convert to basic command (non slash) once outof dev
async def sync(interaction: discord.Interaction):
    if interaction.user.id == ABD_ID or MOK_ID:
        await bot.tree.sync()
        print('Command tree synced.')
        await interaction.response.send_message('Synced!', ephemeral= True)
    else:
        await interaction.response.send_message('You must be the owner to use this command!', ephemeral= True)

#fetches guild ID. Only for dev. Remove in final release ~~~~~
@bot.tree.command()
async def gid(interaction: discord.Interaction):
    await interaction.response.send_message(f"{interaction.guild_id}")


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#              Error handling 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@bot.event
async def on_application_command_error(ctx, error):
    
    embed = discord.Embed(title= "**An error has occured. Please try again!**", 
                        description= "If this problem persists please report the issue using the </feedback:1131265027052142670> command",
                        color=discord.Color.red(), )
    embed.set_footer(icon_url="https://i.imgur.com/AskjZEG.png")
    await ctx.send( embed = embed, ephemeral=True)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#           Bot Personality selection 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@bot.tree.command(description="Changes Ophelia's personality")
@app_commands.describe(u_selection="Select a personality, for more information on these visit our website")
@app_commands.rename(u_selection="behave_like")
@app_commands.choices(u_selection=[
    app_commands.Choice(name="Witty", value= "A"),
    app_commands.Choice(name="Regular", value= "B"),
    app_commands.Choice(name="Playful", value= "C")
])
async def personality(interaction: discord.Interaction,  u_selection: app_commands.Choice[str]):
    if await usernameExists(str(interaction.user.id)) == True:
        await changePersona(str(interaction.user.id), u_selection.value.upper())
        await interaction.response.send_message(f"{u_selection.name} has been selected", ephemeral=True) 
    else:
        embed = discord.Embed(title= "**Your account has not been registered with Ophelia yet**", #Typo 2
                            description= f"Run this command to get started **```/register```**",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.set_footer(text="Generated",
                            icon_url="https://i.imgur.com/AskjZEG.png")
        await interaction.response.send_message( embed = embed, ephemeral=True)
        

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#              Memory Deletion
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


class SimpleView(discord.ui.View):
    async def disable_all_items(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        print("timeout")
        await self.disable_all_items() 

    @discord.ui.button(label="Cancel", 
                       style=discord.ButtonStyle.success)
    async def hello(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title= "**Ophelia's memories were not deleted**",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.set_footer(text="Generated",
                        icon_url="https://i.imgur.com/AskjZEG.png")
        await interaction.response.send_message( embed = embed, ephemeral=True)
        self.stop()

    @discord.ui.button(label="Continue", 
                       style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        #db.reference(f"/{interaction.user.id}/Memories").set([{"role":"system", "content": personaA}]))
        await asyncFirebaseCall(db.reference(f"/{interaction.user.id}/Memories/0").set, {"role":"system", "content": personaA})
        embed = discord.Embed(title= "**Ophelia's memories have been deleted**",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.set_footer(text="Generated",
                        icon_url="https://i.imgur.com/AskjZEG.png")
        await interaction.response.send_message( embed = embed, ephemeral=True)
        self.stop()

@bot.hybrid_command(description="Deletes Ophelia's memories")
async def clear_memories(ctx):
    if await usernameExists(str(ctx.author.id)) == True:
        view = SimpleView(timeout=20)
        embed = discord.Embed(title= "**Running this command will erase all of Ophelia's memories**",
                        description= "Are you sure?",
                        color=discord.Color.red())
        message = await ctx.send(view = view, embed = embed, ephemeral = True)
        view.message = message
        await view.wait()
        await view.disable_all_items()
    else:
        embed = discord.Embed(title= "**Your account has not been registered with Ophelia yet**", #Typo 3
                            description= f"Run this command to get started **```/register```**",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.set_footer(text="Generated",
                            icon_url="https://i.imgur.com/AskjZEG.png")
        await ctx.send( embed = embed, ephemeral=True)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#              Message visibility
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@bot.tree.command(description="Toggles public visibility of Ophelia's replies")
@app_commands.describe(u_selection="Select 'Public' to make messages publically visible or 'Private' to make them visible only to you") #Update 1
@app_commands.rename(u_selection="status")
@app_commands.choices(u_selection=[
    app_commands.Choice(name="Public", value= "True"),
    app_commands.Choice(name="Private", value= "False")
])
async def visibility(interaction: discord.Interaction,  u_selection: app_commands.Choice[str]):
    if await usernameExists(str(interaction.user.id)) == True:
        if interaction.guild == None:
            await interaction.response.send_message("This command is only for use on third party servers", ephemeral=True)
        elif interaction.guild.id == MAIN_GUILD_ID:
            await interaction.response.send_message("This command is only for use on third party servers", ephemeral=True)
        else:
            if u_selection.value == "False":
                #db.reference(f"/{interaction.user.id}").update({"Visibility": False})
                await asyncFirebaseCall(db.reference(f"/{interaction.user.id}").update, {"Visibility": False})
                await interaction.response.send_message("Ophelia's replies will now be privately sent to you.\n```Note: These private messages will dissappear if Discord is restarted.```", ephemeral=True) #Typo 4  
            else:
                await asyncFirebaseCall(db.reference(f"/{interaction.user.id}").update, {"Visibility": True})
                await interaction.response.send_message("Ophelia's replies to you will now be publicly visible")
    else:
        embed = discord.Embed(title= "**Your account has not been registered with Ophelia yet**", #Typo 5
                            description= f"Run this command to get started **```/register```**",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.set_footer(text="Generated",
                            icon_url="https://i.imgur.com/AskjZEG.png")
        await interaction.response.send_message( embed = embed, ephemeral=True)
        
        
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#            The auto talk command
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# 

@bot.tree.command(description="Toggles Ophelia's auto-reply mode") #Update 2
@app_commands.describe(u_selection="Selecting auto-reply will allow Ophelia to read all messages sent in this channel") #Update 3
@app_commands.rename(u_selection="reply")
@app_commands.choices(u_selection=[
    app_commands.Choice(name="Automatically to all messages", value= "True"),
    app_commands.Choice(name="Only to the /talk command", value= "False")
])
async def reply_mode(interaction: discord.Interaction,  u_selection: app_commands.Choice[str]):
    if await usernameExists(str(interaction.user.id)) == True:
        if interaction.guild == None:
            if u_selection.value == "True":
                #db.reference(f"/{interaction.user.id}").update({"AutoReply": True})
                await asyncFirebaseCall(db.reference(f"/{interaction.user.id}").update, {"AutoReply": True})
                await interaction.response.send_message("Ophelia will now auto-reply to all your messages") #Update 6
            else:
                 await asyncFirebaseCall(db.reference(f"/{interaction.user.id}").update, {"AutoReply": False})
                 await interaction.response.send_message("Ophelia will now only reply to you when </talk:1133312077793075263> is used") #Update 7
        elif interaction.guild.id == MAIN_GUILD_ID:
            if u_selection.value == "True":
                #db.reference(f"/{interaction.user.id}").update({"AutoReply": True})
                await asyncFirebaseCall(db.reference(f"/{interaction.user.id}").update, {"AutoReply": True})
                await interaction.response.send_message("Ophelia will now auto-reply to all your messages") #Update 8
            else:
                 #db.reference(f"/{interaction.user.id}").update({"AutoReply": False})
                 await asyncFirebaseCall(db.reference(f"/{interaction.user.id}").update, {"AutoReply": False})
                 await interaction.response.send_message("Ophelia will now only reply to you when </talk:1133312077793075263> is used") 
        else:
            await interaction.response.send_message("This command can only be used in direct messages or [Ophelia's main server](https://discord.gg/z8taFsrEcE)", ephemeral=True)

    else:
        embed = discord.Embed(title= "**Your account has not been registered with Ophelia yet**", #Typo
                            description= f"Run this command to get started **```/register```**",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.set_footer(text="Generated",
                            icon_url="https://i.imgur.com/AskjZEG.png")
        await interaction.response.send_message( embed = embed, ephemeral=True)

@bot.event
async def on_message(message):
    if message.guild == bot.get_guild(MAIN_GUILD_ID):

        if message.channel.category_id == category_id:

            msg_mode = await asyncFirebaseCall(db.reference(f"/{message.author.id}/AutoReply").get)

            if msg_mode == True:

                response = await callModel(str(message.author.id), message.content)

                if response == False:
                    await message.channel.send("You are out of balance! Please recharge your account here [Ophelia's website](https://ophelia-ai.netlify.app/)") #Update
                else:
                    await message.channel.send(f"{response}")

    elif message.guild == None:

        msg_mode = await asyncFirebaseCall(db.reference(f"/{message.author.id}/AutoReply").get)

        if msg_mode == True:

            response = await callModel(str(message.author.id), message.content)

            if response == False:
                await message.channel.send("You are out of balance! Please recharge your account here [Ophelia's website](https://ophelia-ai.netlify.app/)") #Update
            else:
                await message.channel.send(f"{response}")
                
# @on_message.error
# async def talk_error(ctx, error):
#     embed = discord.Embed(title= "**An error has occured. Please try again!**", 
#                         description= "If this problem persists please report the issue using the </feedback:1131265027052142670> command",
#                         color=discord.Color.red(), )
#     embed.set_footer(icon_url="https://i.imgur.com/AskjZEG.png")
#     await ctx.send( embed = embed, ephemeral=True)
    


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#              The talk command
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@bot.tree.command(description="Chat with Ophelia!")
@app_commands.describe(text_to_send="      ୧‿︵‿︵‿︵‿୨♡୧‿︵‿︵‿︵‿୨♡୧‿︵‿︵‿︵‿୨♡୧‿︵‿︵‿︵‿୨♡୧‿︵‿︵‿︵‿୨♡୧‿︵‿︵‿︵‿୨♡୧‿︵‿︵‿︵‿୨♡୧‿︵‿︵‿︵‿୨")
@app_commands.rename(text_to_send="message")
async def talk(interaction: discord.Interaction, text_to_send : str):
    if await usernameExists(str(interaction.user.id)) == True:
            if interaction.guild == bot.get_guild(MAIN_GUILD_ID) or None:
                await interaction.response.defer()
                response = await callModel(str(interaction.user.id), text_to_send)
                if response == False:
                    await interaction.followup.send("You are out of balance! Please recharge your account here [Ophelia's website](https://ophelia-ai.netlify.app/)") #Update
                else:
                    await interaction.followup.send(f"> ***`{text_to_send}`***\n\n{response}")
            else:
                status = await asyncFirebaseCall(db.reference(f"/{interaction.user.id}/Visibility").get)
                await interaction.response.defer(ephemeral=not status)
                response = await callModel(str(interaction.user.id), text_to_send)

                if response == False:
                    await interaction.followup.send("You are out of balance! Please recharge your account here [Ophelia's website](https://ophelia-ai.netlify.app/)") #Update
                else:
                    await interaction.followup.send(f"> ***`{text_to_send}`***\n\n{response}")
    else:
        embed = discord.Embed(title= "**Your account has not been registered with Ophelia yet**", #Typo
                            description= f"Run this command to get started **```/register```**",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.set_footer(text="Generated",
                            icon_url="https://i.imgur.com/AskjZEG.png")
        await interaction.response.send_message( embed = embed, ephemeral=True)
        
@talk.error
async def talk_error(ctx, error):
    embed = discord.Embed(title= "**An error has occured. Please try again!**", 
                        description= "If this problem persists please report the issue using the </feedback:1131265027052142670> command",
                        color=discord.Color.red(), )
    embed.set_footer(icon_url="https://i.imgur.com/AskjZEG.png")
    await ctx.send( embed = embed, ephemeral=True)



#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#       Direct message functionality
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@bot.tree.command(description="Create a DM with Ophelia")
async def dms(interaction: discord.Interaction):
    channel = await interaction.user.create_dm()
    bot.tree.copy_global_to(guild=channel)
    embed = discord.Embed(title= "**For the best experience use Ophelia in auto-reply mode!**",
                          description= "Use </reply_mode:1133325372688171048> `[Automatically to all messages]` to configure this",
                          color=discord.Color.blurple(),
                          type = "rich")
    embed.set_thumbnail(url="https://i.imgur.com/AskjZEG.png")
    await channel.send(embed=embed)
    await interaction.response.send_message("A DM with Ophelia has been created",  ephemeral= True)

@bot.tree.context_menu(name="Create a DM")
async def dmsC(interaction: discord.Interaction,  member: discord.Member):
    channel = await interaction.user.create_dm()
    bot.tree.copy_global_to(guild=channel)
    embed = discord.Embed(title= "**For the best experience use Ophelia in auto-reply mode!**",
                          description= "Use </reply_mode:1133325372688171048> `[Automatically to all messages]` to configure this setting",
                          color=discord.Color.blurple(),
                          type = "rich")
    embed.set_thumbnail(url="https://i.imgur.com/AskjZEG.png")
    await channel.send(embed=embed)
    await interaction.response.send_message("A DM with Ophelia has been created",  ephemeral= True)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#             User Registration
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


#Command for registration of non existing users
@bot.tree.command(description="Registers your Discord account with Ophelia") #Typo
async def register(interaction: discord.Interaction):


    MAIN_GUILD = bot.get_guild(MAIN_GUILD_ID)
    uc_category = discord.utils.get(MAIN_GUILD.categories, id = category_id)

    overwrites = { # Permisions for the new channel created in the main server
        MAIN_GUILD.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True)}
    
    await interaction.response.defer(ephemeral = True)
    await asyncio.sleep(3)

    if await registerAcc(str(interaction.user.id)) == True:

        if interaction.guild == None: #when called in DM
            privc = await MAIN_GUILD.create_text_channel(f"{interaction.user}'s Channel", overwrites=overwrites, category= uc_category)
            embed = discord.Embed(title= "**For the best experience use Ophelia in auto-reply mode!**",
                        description= "Use </reply_mode:1133325372688171048> `[Automatically to all messages]` to configure this setting",
                        color=discord.Color.blurple(),
                        type = "rich")
            embed.set_thumbnail(url="https://i.imgur.com/AskjZEG.png")
            await privc.send(embed=embed)

            embed = discord.Embed(title= "**You are now registered with Ophelia!**",
                                description= "Use ``/help`` to learn more about Ophelia",
                                color=discord.Color.blurple(),
                                timestamp = datetime.datetime.now())
            embed.set_thumbnail(url=f"{interaction.user.avatar}")
            embed.set_footer(text="Generated",
                            icon_url="https://i.imgur.com/AskjZEG.png")
            await interaction.followup.send( embed = embed, ephemeral=True)


        elif interaction.guild.id == MAIN_GUILD_ID: 

            privc = await interaction.guild.create_text_channel(f"{interaction.user}'s Channel", overwrites=overwrites, category= uc_category)
            embed = discord.Embed(title= "**For the best experience use Ophelia in auto-reply mode!**",
                        description= "Use </reply_mode:1133325372688171048> `[Automatically to all messages]` to configure this setting",
                        color=discord.Color.blurple(),
                        type = "rich")
            embed.set_thumbnail(url="https://i.imgur.com/AskjZEG.png")
            await privc.send(embed=embed)
            
            embed = discord.Embed(title= "**You are now registered with Ophelia!**", #Typo
                                description= f"Please go to <#{privc.id}>",
                                color=discord.Color.blurple(),
                                timestamp = datetime.datetime.now())
            embed.set_thumbnail(url=f"{interaction.user.avatar}")
            embed.set_footer(text="Generated",
                            icon_url="https://i.imgur.com/AskjZEG.png")
            await interaction.followup.send( embed = embed, ephemeral=True)

        else:
            privc = await MAIN_GUILD.create_text_channel(f"{interaction.user}'s Channel", overwrites=overwrites, category= uc_category)
            embed = discord.Embed(title= "**You are now registered with Ophelia!**",
                                description= "Use ``/help`` to learn more about Ophelia",
                                color=discord.Color.blurple(),
                                timestamp = datetime.datetime.now())
            embed.set_thumbnail(url=f"{interaction.user.avatar}")
            embed.set_footer(text="Generated",
                            icon_url="https://i.imgur.com/AskjZEG.png")
            await interaction.followup.send( embed = embed, ephemeral=True)

    else:
        embed = discord.Embed(title= "**Your account has been already registered!**",
                            description= "Please navigate to your assigned message channel to use Ophelia",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.set_thumbnail(url=f"{interaction.user.avatar}")
        embed.set_footer(text="Generated",
                         icon_url="https://i.imgur.com/AskjZEG.png")
        await interaction.followup.send( embed = embed, ephemeral=True)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#          Account information command
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@bot.tree.command(name= "account", description = "Displays account information")
async def account_info(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral = True)

    if await usernameExists(str(interaction.user.id)) == True:

        balance = await asyncFirebaseCall(db.reference(f"/{str(interaction.user.id)}/Balance").get)
        userTokens = await asyncFirebaseCall(db.reference(f"/{str(interaction.user.id)}/TotalUserTokens").get)
        accType = await asyncFirebaseCall(db.reference(f"/{str(interaction.user.id)}/Type").get)
        balanceRemaining = int(balance) - int(float(userTokens))

        embed = discord.Embed(title= f"**{interaction.user}'s account**",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.add_field(name="", value="", inline=False)
        embed.add_field(name="", value="", inline=False)
        embed.set_thumbnail(url=f"{interaction.user.avatar}")
        # embed.add_field(name="Account ID",
        #                 value=f"`{interaction.user.id}`",
        #                 inline=False)
        # embed.add_field(name="", value="", inline=False)
        embed.add_field(name="Account type‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ",
                        value=f"`{accType}`",
                        inline=True)
        embed.add_field(name="Balance",
                        value=f"`{balanceRemaining}`",
                        inline=True,)
        embed.add_field(name="", value="", inline=False)
        embed.set_footer(text="Generated",
                        icon_url="https://i.imgur.com/AskjZEG.png")
        await interaction.followup.send( embed = embed, ephemeral=True)
    else:
        embed = discord.Embed(title= "**Your account has not been registered with Ophelia yet**", #Typo
                            description= f"Run this command to get started **```/register```**",
                            color=discord.Color.blurple(),
                            timestamp = datetime.datetime.now())
        embed.set_footer(text="Generated",
                         icon_url="https://i.imgur.com/AskjZEG.png")
        await interaction.followup.send( embed = embed, ephemeral=True)





#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#               Help command
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@bot.tree.command(description="Discover Ophelia's Commands")
async def help(interaction: discord.Interaction):
    embed1 = discord.Embed(title= "**Ophelia Help Center**",
                          description= "Below is a list of all our available commands. For more information visit [Ophelia's website](https://ophelia-ai.netlify.app/)",
                          color=discord.Color.blurple(),
                          type = "rich")
    embed1.set_thumbnail(url="https://i.imgur.com/AskjZEG.png")
    embed1.add_field(name="", value="", inline=False)
    embed1.add_field(name="", value="", inline=False)
    embed1.add_field(name="💙 ‎ ‎ ‎ User Utilities:", value="", inline=False)
    embed1.add_field(name="", value="", inline=False)
    embed1.add_field(name="</account:1131265027052142668>",
                    value="> Displays your account information, including balance and account type",
                    inline=False)
    embed1.add_field(name="", value="", inline=False)
    embed1.add_field(name="", value="", inline=False)
    embed1.add_field(name="</feedback:1131265027052142670> `[submit_report]`",
                    value="> Allows you to report problems and suggestions regarding Ophelia",
                    inline=False)
    embed1.add_field(name="", value="", inline=False)
    embed1.add_field(name="", value="", inline=False)
    embed1.add_field(name="</register:1131265027052142665>",
                    value="> Registers your account with Ophelia. You only need to use this command once.", #Typo
                    inline=False)
    embed1.add_field(name="", value="", inline=False)
    embed1.add_field(name="", value="", inline=False)

    embed2 = discord.Embed(
                        color=discord.Color.blurple(),
                        type = "rich")
    embed2.add_field(name="💜 ‎ ‎ ‎ Bot Utilities:", value="", inline=False)
    embed2.add_field(name="", value="", inline=False)

    embed2.add_field(name="</talk:1133312077793075263> `[message]`",
                    value="> Allows you to talk with Ophelia", #Typo
                    inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="</personality:1132944948933705751> `[behave_like]`",
                    value="> Changes the way Ophelia talks with you",
                    inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="</reply_mode:1133325372688171048> `[reply]`",
                    value="> Toggles automatic replies \n> \n> *Note: This command is only for use in DMs (see </dms:1133700164746485863> below) or [Ophelia's main server](https://discord.gg/z8taFsrEcE)* ",
                    inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="</dms:1133700164746485863>",
                    value="> Automatically creates a DM with Ophelia",
                    inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="</visibility:1131527971841245254> `[status]`",
                    value="> Toggles public visibility of Ophelia's replies to you in 3rd party servers \n> \n> *Note: This command is only for use in 3rd party servers*",
                    inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="", value="", inline=False)
    embed2.add_field(name="</clear_memories:1133692597827809392>",
                    value="> Deletes Ophelia's memory of past conversations, resetting the chat",
                    inline=False)

    await interaction.channel.send( embed = embed1)
    await interaction.channel.send( embed = embed2)




#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#    Interface for user based bug reporting
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

# Popup (Modal)
class FeedbackModal(discord.ui.Modal, title="Feedback & Report Terminal"):

    fb_title = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="Subject",
        required=False,
        placeholder="Brief summary of the issue"
    )

    message = discord.ui.TextInput(
        style=discord.TextStyle.long,
        label="Message",
        required=False,
        max_length=500,
        placeholder="Give a detailed description of the issue. Attach any images as links to http://imgur.com/."
    )

    async def on_submit(self, interaction: discord.Interaction):

        MAIN_GUILD = bot.get_guild(MAIN_GUILD_ID) 
        FEEDBACK_CHANNEL_ID = 1131266628768772168

        channel = MAIN_GUILD.get_channel(FEEDBACK_CHANNEL_ID)

        embed = discord.Embed(title=self.fb_title.value,
                              description=self.message.value,
                              color=discord.Color.yellow())
        embed.set_author(name=self.user)

        await channel.send(embed=embed)
        await interaction.response.send_message(f"Thank you, {self.user} for submitting this bug report. We'll get right to fixing it!", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error : Exception):
        traceback.print_tb(error.__traceback__)

# Slash command implementation

@bot.tree.command(description="Submit a bug report")
@app_commands.describe(text_to_send="Select 'True' to be prompted to our report submission page.") #Update
@app_commands.rename(text_to_send="submit_report")
async def feedback(interaction: discord.Interaction,  text_to_send: bool):

    if text_to_send == False:
        await interaction.response.send_message(f"No problem? Yay!", ephemeral=True)

    feedback_modal = FeedbackModal()
    feedback_modal.user = interaction.user
    await interaction.response.send_modal(feedback_modal)

# Context menu (USER) implementation

@bot.tree.context_menu(name="Report a bug")
async def get_joined_date(interaction: discord.Interaction, member: discord.Member):
    feedback_modal = FeedbackModal()
    feedback_modal.user = interaction.user
    await interaction.response.send_modal(feedback_modal)

# Context menu (MESSAGE) implementation

@bot.tree.context_menu(name="Report Message")
async def report_message(interaction: discord.Interaction, message: discord.Message):
    feedback_modal = FeedbackModal()
    feedback_modal.user = interaction.user
    await interaction.response.send_modal(feedback_modal)


bot.run(TOKEN)





#Registration checkers
# if ophie.usernameExists(str(interaction.user.id)) == True:

# else:
#     embed = discord.Embed(title= "**Your account has not been registered with Opehlia yet**",
#                         description= f"Run this command to get started **```/register```**",
#                         color=discord.Color.blurple(),
#                         timestamp = datetime.now() )
#     embed.set_footer(text="Generated",
#                         icon_url="https://i.imgur.com/AskjZEG.png")
#     await interaction.followup.send( embed = embed, ephemeral=True)



#EXAMPLE OF STANDARD COMMAND
# @bot.command(aliases = ["AO"])
# async def Activate_Ophelia(ctx, intent):

#     global O_Status

#     if intent.lower() == "yes":
#         O_Status = True
#         await ctx.send("Ophelia will now reply to you!")
#     else:
#         await ctx.send("Unknown reply!")

# if O_Status == True:
#     @bot.event
#     async def on_message(message):

#         msg = message.content.lower()

#         if message.author == bot.user:
#             return



#PLACE THE FIRST TWO LINES INSIDE ON READY

    # account_grp = AccountGroup(name= "account", description = "manage account")
    # bot.tree.add_command(account_grp)

# class AccountGroup(app_commands.Group):

#     @app_commands.command(name= "info", description = "Display account information")
#     async def account_info(self,interaction: discord.Interaction):
#         await interaction.response.send_message(f"ping", ephemeral=True)

#     @app_commands.command(name= "balance", description = "Check remaining token balance")
#     async def balance(self,interaction: discord.Interaction):
#         await interaction.response.send_message(f"pong", ephemeral=True)

# @bot.tree.command(description="Discover Ophelia's Commands")
# async def say(interaction: discord.Interaction, text_to_send : str):
#     await interaction.response.send_message(f"{text_to_send}", ephemeral=True)
