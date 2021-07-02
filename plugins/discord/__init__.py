import discord
import asyncio
import time
from threading import Thread
from nut import Config, Hook

client = discord.Client()
channels = {}
initialized = False
ready = False

async def _send(channelId, msg):
	global channels

	if channelId not in channels:
		channels[channelId] = client.get_channel(int(channelId))

	await channels[channelId].send(msg)

def send(channelId, msg):
	coro = _send(channelId, msg)

	fut = asyncio.run_coroutine_threadsafe(coro, client.loop)
	try:
		fut.result()
	except BaseException as e:
		print(str(e))
		pass

@client.event
async def on_ready():
	global ready
	print(f'{client.user} has connected to Discord!')
	ready = True

def run():
	client.run(Config.original['discord']['token'])

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
		send(channelId, 'added %s' % str(nsp.titleId))

def deleteFile(nsp):
	start()

	if nsp.isUpdate():
		channelIds = Config.original['discord']['channels']['files']['update']
	elif nsp.isDLC():
		channelIds = Config.original['discord']['channels']['files']['dlc']
	else:
		channelIds = Config.original['discord']['channels']['files']['base']

	for channelId in channelIds:
		send(channelId, 'deleted %s' % str(nsp.titleId))


if Config.original['discord']['token']:
	Hook.register('files.move', moveFile)
	Hook.register('files.register', addFile)
	Hook.register('files.unregister', deleteFile)

