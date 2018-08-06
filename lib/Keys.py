import re
import aes128
from binascii import hexlify as hx, unhexlify as uhx

keys = {}
titleKeks = []

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
	
	

def load(fileName):
	with open(fileName, encoding="utf8") as f:
		for line in f.readlines():
			r = re.match('\s*([a-z0-9_]+)\s*=\s*([A-F0-9]+)\s*', line, re.I)
			if r:
				keys[r.group(1)] = r.group(2)
	
	#crypto = aes128.AESCTR(uhx(key), uhx('00000000000000000000000000000010'))
	
	for i in range(10):
		masterKeyName = 'master_key_0' + str(i)
		if masterKeyName in keys.keys():
			# aes_decrypt(master_ctx, &keyset->titlekeks[i], keyset->titlekek_source, 0x10);
			crypto = aes128.AESECB(uhx(keys[masterKeyName]))
			titleKeks.append(crypto.decrypt(uhx(keys['titlekek_source'])).hex())
		else:
			titleKeks.append('0' * 32)

				
load('Keys.txt')

#for k in titleKeks:
#	print('titleKek = ' + k)