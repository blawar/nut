import re
from nut import aes128, Config
from binascii import hexlify as hx, unhexlify as uhx
from nut import Print

keys = {}
titleKeks = []
keyAreaKeys = []

def getMasterKeyIndex(i):
	if i > 0:
		return i-1
	else:
		return 0

def keyAreaKey(cryptoType, i):
	return keyAreaKeys[cryptoType][i]

def get(key):
	return keys[key]
	
def getTitleKek(i):
	return titleKeks[i]
	
def decryptTitleKey(key, i):
	kek = getTitleKek(i)
	
	crypto = aes128.AESECB(uhx(kek))
	return crypto.decrypt(key)
	
def encryptTitleKey(key, i):
	kek = getTitleKek(i)
	
	crypto = aes128.AESECB(uhx(kek))
	return crypto.encrypt(key)
	
def changeTitleKeyMasterKey(key, currentMasterKeyIndex, newMasterKeyIndex):
	return encryptTitleKey(decryptTitleKey(key, currentMasterKeyIndex), newMasterKeyIndex)

def generateKek(src, masterKey, kek_seed, key_seed):
	kek = []
	src_kek = []

	crypto = aes128.AESECB(masterKey)
	kek = crypto.decrypt(kek_seed)

	crypto = aes128.AESECB(kek)
	src_kek = crypto.decrypt(src)

	if key_seed != None:
		crypto = aes128.AESECB(src_kek)
		return crypto.decrypt(key_seed)
	else:
		return src_kek

def unwrapAesWrappedTitlekey(wrappedKey, keyGeneration):
	aes_kek_generation_source = uhx(keys['aes_kek_generation_source'])
	aes_key_generation_source = uhx(keys['aes_key_generation_source'])

	kek = generateKek(uhx(keys['key_area_key_application_source']), uhx(keys['master_key_0' + str(keyGeneration)]), aes_kek_generation_source, aes_key_generation_source)

	crypto = aes128.AESECB(kek)
	return crypto.decrypt(wrappedKey)
	

def load(fileName):
	global keyAreaKeys
	global titleKeks

	with open(fileName, encoding="utf8") as f:
		for line in f.readlines():
			r = re.match('\s*([a-z0-9_]+)\s*=\s*([A-F0-9]+)\s*', line, re.I)
			if r:
				keys[r.group(1)] = r.group(2)
	
	#crypto = aes128.AESCTR(uhx(key), uhx('00000000000000000000000000000010'))
	aes_kek_generation_source = uhx(keys['aes_kek_generation_source'])
	aes_key_generation_source = uhx(keys['aes_key_generation_source'])

	keyAreaKeys = []
	for i in range(10):
		keyAreaKeys.append([None, None, None])

	
	for i in range(10):
		masterKeyName = 'master_key_0' + str(i)
		if masterKeyName in keys.keys():
			# aes_decrypt(master_ctx, &keyset->titlekeks[i], keyset->titlekek_source, 0x10);
			masterKey = uhx(keys[masterKeyName])
			crypto = aes128.AESECB(masterKey)
			titleKeks.append(crypto.decrypt(uhx(keys['titlekek_source'])).hex())
			keyAreaKeys[i][0] = generateKek(uhx(keys['key_area_key_application_source']), masterKey, aes_kek_generation_source, aes_key_generation_source)
			keyAreaKeys[i][1] = generateKek(uhx(keys['key_area_key_ocean_source']), masterKey, aes_kek_generation_source, aes_key_generation_source)
			keyAreaKeys[i][2] = generateKek(uhx(keys['key_area_key_system_source']), masterKey, aes_kek_generation_source, aes_key_generation_source)
		else:
			titleKeks.append('0' * 32) 


try:			
	load(Config.paths.keys)
except BaseException as e:
	Print.error(f'Could not load keys.txt. You can safely ignore this error: {str(e)}')

#for k in titleKeks:
#	Print.info('titleKek = ' + k)

#for k in keyAreaKeys:
#	Print.info('%s, %s, %s' % (hex(k[0]), hex(k[1]), hex(k[2])))