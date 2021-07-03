import discord
import asyncio
import time
import os.path
from datetime import datetime
from threading import Thread
from nut import Config, Hook, Titles

client = discord.Client()
loop = asyncio.get_event_loop()
channels = {}
initialized = False
ready = False

async def _send(channelId, msg = None, embed = None):
	global channels

	if channelId not in channels:
		channels[channelId] = client.get_channel(int(channelId))

	if embed is not None:
		await channels[channelId].send(embed = embed)
	else:
		await channels[channelId].send(msg)

def send(channelId, msg = None, embed = None):
	coro = _send(channelId, msg, embed)

	fut = asyncio.run_coroutine_threadsafe(coro, client.loop)
	try:
		fut.result()
	except BaseException as e:
		print(str(e))
		pass

def formatSize(size):
	return size

prefixes = [' B', ' KB', ' MB', ' GB', ' TB']

def formatSize(n):
	if not n:
		return None

	for i in range(len(prefixes)):
		if n < 1000:
			return str(round(n, 1)) + prefixes[i];

		n /= 1000;

	return str(round(n, 1)) + ' PB';


def formatDate(d):
	d = str(d)

	if len(d) != 8:
		return discord.Embed.Empty

	return datetime(int(d[0:4]), int(d[4:6]), int(d[6:8]))

def sendTitleCard(channelId, titleId, nsp = None):
	if not Titles.contains(titleId):
		send(channelId, titleId)
		return

	title = Titles.get(titleId)
	titleBase = title.getBase() or title

	filename = None

	if nsp:
		filename = os.path.basename(nsp.fileName())

	embed = discord.Embed(title=title.name or titleBase.name, description=title.intro, color=0x3498DB, url = "https://tinfoil.io/Title/" + titleId.upper(), timestamp = formatDate(title.releaseDate))

	if filename:
		embed.add_field(name="File Name", value=filename, inline=False)
	else:
		embed.add_field(name="ID", value=titleId.upper(), inline=True)

	if title.isUpdate:
		embed.add_field(name="Type", value='Update', inline=True)
	elif title.isDLC:
		embed.add_field(name="Type", value='DLC', inline=True)
	else:
		embed.add_field(name="Type", value='Base', inline=True)

	if nsp:
		if nsp.getFileSize():
			embed.add_field(name="Size", value=formatSize(nsp.getFileSize()), inline=True)
	else:
		if title.size:
			embed.add_field(name="Size", value=formatSize(title.size), inline=True)

	

	if title.iconUrl or titleBase.iconUrl:
		embed.set_thumbnail(url = title.iconUrl or titleBase.iconUrl)

	if nsp:
		ext = nsp.path.split('.')[-1].lower()
		#if nsp.version:
		#	embed.add_field(name="Version", value=str(nsp.version), inline=True)

		if ext == 'nsz':
			try:
				embed.add_field(name="Compression", value='-' + str(100 - int(nsp.getCr())) + '%', inline=True)
			except:
				pass

	send(channelId, embed = embed)

@client.event
async def on_ready():
	global ready
	print(f'{client.user} has connected to Discord!')
	ready = True

def run():
	global loop
	loop.run_until_complete(client.start(Config.original['discord']['token']))
	print('run exited')

def start():
	global initialized

	if not Config.original['discord']['token']:
		raise IOError('no discord token set in nut.conf')

	if initialized:
		return False

	initialized = True

	thread = Thread(target = run)
	thread.start()

	while not ready:
		time.sleep(1)

	return True

def moveFile(nsp, oldPath):
	pass

def addFile(nsp):
	start()

	if nsp.isUpdate():
		channelIds = Config.original['discord']['channels']['files']['update']
	elif nsp.isDLC():
		channelIds = Config.original['discord']['channels']['files']['dlc']
	else:
		channelIds = Config.original['discord']['channels']['files']['base']

	for channelId in channelIds:
		#send(channelId, 'added %s' % str(nsp.titleId))
		sendTitleCard(channelId, nsp.titleId, nsp)

def deleteFile(nsp):
	start()

	if nsp.isUpdate():
		channelIds = Config.original['discord']['channels']['files']['update']
	elif nsp.isDLC():
		channelIds = Config.original['discord']['channels']['files']['dlc']
	else:
		channelIds = Config.original['discord']['channels']['files']['base']

	for channelId in channelIds:
		#send(channelId, 'deleted %s' % str(nsp.titleId))
		sendTitleCard(channelId, nsp.titleId, nsp)

def cleanup():
	if not ready:
		return

	coro = client.close()
	fut = asyncio.run_coroutine_threadsafe(coro, client.loop)

if Config.original['discord']['token']:
	Hook.register('files.move', moveFile)
	Hook.register('files.register', addFile)
	Hook.register('files.unregister', deleteFile)
	Hook.register('exit', cleanup)

