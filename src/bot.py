import discord
from discord.ext import commands


client_secret = 'iZ_Zpb3x6wAZSL0PwgHB-ibSIX-SBRlh'
bot_token = 'MTE4NDE2ODY4OTI1MjE5MjMwNg.Gi42VX.jgLbsUxS2DTr1p73R6WkuYBHjXmokOZz2ebagc'

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def hello(ctx):
    await ctx.send('Hello, world!')


@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel is not None:
        if after.channel.name == 'General':
            channel = discord.utils.get(member.guild.text_channels, name='general')
            if channel is not None:
                await channel.send(f'{member.name} joined the voice channel!')

bot.run(bot_token)
