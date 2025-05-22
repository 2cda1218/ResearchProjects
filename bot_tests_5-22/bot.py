import discord
from discord import app_commands as dac
import os
from dotenv import load_dotenv

# get env
load_dotenv()

# bot token
TOKEN = os.getenv("TOKEN")

# set bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.voice_states = True
bot = discord.Client(intents = intents)
tree = dac.CommandTree(bot)

@bot.event
async def on_ready():
    print('voice test bot 起動')
    activity = '音声認識のテストできます'
    await bot.change_presence(activity = discord.Game(activity))
    await tree.sync()


#--------------
# bot commands
#--------------

@tree.command(name = 'hello',description = 'botの動作確認用テストコマンド')
async def hello(ctx: discord.Interaction):
    await ctx.response.send_message(f'Hello {ctx.user.display_name}')

@tree.command(name = 'reboot',description = '再起動用')
async def reboot(ctx: discord.Interaction):
    await ctx.response.send_message('再起動を開始します')
    await bot.close()

#-------
# voice
#-------


#----------
# bot run
#----------
bot.run(TOKEN)