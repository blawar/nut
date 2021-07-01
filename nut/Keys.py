import re
from binascii import hexlify as hx
from binascii import unhexlify as uhx

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS, PKCS1_v1_5, pss

from nut import Print, aes128

keys = {}
titleKeks = []
keyAreaKeys = []
keyGens = []

hasDecimalMasterKeys = True
ncaHdrFixedKeyModulus = int("bfbe406cf4a780e9f07d0c99611d772f96bc4b9e58381b03abb175499f2b4d5834b005a37522be1a3f0373ac7068d116b904465eb707912f078b26def60007b2b451f80d0a5e58adebbc9ad649b964efa782b5cf6d7013b00f85f6a908aa4d676687fa89ff7590181e6b3de98a68c92604d980ce3f5e92ce01ff063bf2c1a90cce026f16bc92420a4164cd52b6344daec02edea4df27683cc1a060ad43f3fc86c13e6c46f77c299ffafdf0e3ce64e735f2f656566f6df1e242b08340a5c3202bcc9aaecaed4d7030a8701c70fd1363290279ead2a7af3528321c7be62f1aaa407e328c2742fe8278ec0debe6834b6d8104401a9e9a67f67229fa04f09de4f403", 16)

def ini_Key(i, prefix = 'master_key_'):
	if hasDecimalMasterKeys:
		return prefix + str(i).zfill(2)
	else:
		return prefix + ('%x' % i).zfill(2)

def pssVerify(buffer, signature, modulus):
	p = PKCS1_PSS.new(RSA.RsaKey(n=modulus, e=65537))

	try:
		return p.verify(SHA256.new(buffer), signature)
	except BaseException:
		return False

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

def decrypt(key, i):
	crypto = aes128.AESECB(masterKey(i))
	return crypto.decrypt(key)

def changeTitleKeyMasterKey(key, currentMasterKeyIndex, newMasterKeyIndex):
	return encryptTitleKey(decryptTitleKey(key, currentMasterKeyIndex), newMasterKeyIndex)

def generateKek(src, masterKey, kek_seed, key_seed):
	kek = []
	src_kek = []

	crypto = aes128.AESECB(masterKey)
	kek = crypto.decrypt(kek_seed)

	crypto = aes128.AESECB(kek)
	src_kek = crypto.decrypt(src)

	if key_seed is not None:
		crypto = aes128.AESECB(src_kek)
		return crypto.decrypt(key_seed)
	else:
		return src_kek

def unwrapAesWrappedTitlekey(wrappedKey, keyGeneration):
	aes_kek_generation_source = uhx(keys['aes_kek_generation_source'])
	aes_key_generation_source = uhx(keys['aes_key_generation_source'])

	kek = generateKek(uhx(keys['key_area_key_application_source']), uhx(
		keys[ini_Key(keyGeneration)]), aes_kek_generation_source, aes_key_generation_source)

	crypto = aes128.AESECB(kek)
	return crypto.decrypt(wrappedKey)

def getKey(key):
	if key not in keys:
		raise IOError('%s missing from keys.txt' % key)
	return uhx(keys[key])

def masterKey(masterKeyIndex):
	return getKey(ini_Key(masterKeyIndex))

def getKeyGens():
	return keyGens

def load(fileName):
	global keyAreaKeys
	global titleKeks
	global hasDecimalMasterKeys

	with open(fileName, encoding="utf8") as f:
		for line in f.readlines():
			r = re.match(r'\s*([a-z0-9_]+)\s*=\s*([A-F0-9]+)\s*', line, re.I)
			if r:
				keys[r.group(1).lower()] = r.group(2)

	#crypto = aes128.AESCTR(uhx(key), uhx('00000000000000000000000000000010'))
	aes_kek_generation_source = uhx(keys['aes_kek_generation_source'])
	aes_key_generation_source = uhx(keys['aes_key_generation_source'])

	digits = ['a', 'b', 'c', 'd', 'e', 'f']

	for key in keys.keys():
		if not key.startswith('master_key_'):
			continue

		for c in key.lower().split('_')[-1]:
			if c in digits:
				hasDecimalMasterKeys = False
				break


	keyAreaKeys = []
	for i in range(0x10):
		keyAreaKeys.append([None, None, None])

	for i in range(0x10):
		masterKeyName = ini_Key(i)

		if masterKeyName in keys.keys():
			# aes_decrypt(master_ctx, &keyset->titlekeks[i], keyset->titlekek_source, 0x10);
			masterKey = uhx(keys[masterKeyName])
			crypto = aes128.AESECB(masterKey)
			titleKeks.append(crypto.decrypt(uhx(keys['titlekek_source'])).hex())
			keyAreaKeys[i][0] = generateKek(uhx(keys['key_area_key_application_source']), masterKey, aes_kek_generation_source, aes_key_generation_source)
			keyAreaKeys[i][1] = generateKek(uhx(keys['key_area_key_ocean_source']), masterKey, aes_kek_generation_source, aes_key_generation_source)
			keyAreaKeys[i][2] = generateKek(uhx(keys['key_area_key_system_source']), masterKey, aes_kek_generation_source, aes_key_generation_source)
			keyGens.append(i)
		else:
			titleKeks.append('0' * 32)


try:
	load('keys.txt')
except BaseException as e:
	try:
		load('keys.prod')
	except BaseException:
		Print.error('could not load keys.txt, all crypto operations will fail')

# for k in titleKeks:
#	Print.info('titleKek = ' + k)

# for k in keyAreaKeys:
#	Print.info('%s, %s, %s' % (hex(k[0]), hex(k[1]), hex(k[2])))
