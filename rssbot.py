import discord
import asyncio
from pathlib import Path
import os
import time
import datetime
import aiohttp
import shutil
from config import SCREENSHOT_SAVE_PATH, RAID_IMAGE_CHANNELS, TOKEN

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return
    
    for channel in RAID_IMAGE_CHANNELS:
        if message.channel.id == channel:
            print(message.attachments)
            print(len(message.attachments))
            print(message.attachments[0]['url'])
            
            for attachment in message.attachments:                        
                if attachment['url'] is not None:
                    async with aiohttp.get(attachment['url']) as r:
                        if r.status == 200:
                            img = await r.read()
                            with open(attachment['filename'], 'wb') as f:
                                f.write(img)
                                print(attachment['filename'], 'saved')
                            shutil.move(attachment['filename'], SCREENSHOT_SAVE_PATH+attachment['filename'])
    
client.run(TOKEN)
