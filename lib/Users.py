import os
import re
import Print

global users
users = {}

class User:
	def __init__(self):
		self.id = None
		self.password = None
		self.isAdmin = False
		self.remoteAddr = None
		self.requireAuth = True
		pass

	def loadCsv(self, line, map = ['id', 'key', 'name']):
		split = line.split('|')
		for i, value in enumerate(split):
			if i >= len(map):
				Print.info('invalid map index: ' + str(i) + ', ' + str(len(map)))
				continue
			
			i = str(map[i])
			methodName = 'set' + i[0].capitalize() + i[1:]
			method = getattr(self, methodName, lambda x: None)
			method(value.strip())

	def setId(self, id):
		self.id = id

	def getId(self):
		return str(self.id)

	def setPassword(self, password):
		self.password = password

	def getPassword(self):
		return self.password

	def setIsAdmin(self, isAdmin):
		try:
			self.isAdmin = False if int(isAdmin) == 0 else True
		except:
			pass
	def getIsAdmin(self):
		return str(self.isAdmin)

	def setRequireAuth(self, requireAuth):
		try:
			self.requireAuth = False if int(requireAuth) == 0 else True
		except:
			pass

	def getRequireAuth(self):
		return str(self.requireAuth)

def auth(id, password, address):
	#print('Authing: ' + str(id) + ' - ' + str(password) + ', ' + str(address))

	if not id in users:
		return False

	user = users[id]

	if user.requireAuth == 0 and address == user.remoteAddr:
		return True

	if user.remoteAddr and user.remoteAddr != address:
		return False

	if user.password != password:
		return False

	return True

def load(path = 'conf/users.conf'):
	if not os.path.isfile(path):
		return

	global users
	firstLine = True
	map = ['id', 'password', 'isAdmin', 'remoteAddr', 'requireAuth']
	with open(path, encoding="utf-8-sig") as f:
		for line in f.readlines():
			line = line.strip()
			if len(line) == 0 or line[0] == '#':
				continue
			if firstLine:
				firstLine = False
				if re.match('[A-Za-z\|\s]+', line, re.I):
					map = line.split('|')
					continue
		
			t = User()
			t.loadCsv(line, map)

			users[t.id] = t

			Print.info('loaded user ' + str(t.id))

def save():
	pass

def export(fileName = 'conf/users.conf', map = ['id', 'password', 'isAdmin', 'remoteAddr', 'requireAuth']):
	global users
	buffer = ''
	
	buffer += '|'.join(map) + '\n'
	for k,t in users.items():
		buffer += t.serialize(map) + '\n'
		
	with open(fileName, 'w', encoding='utf-8') as csv:
		csv.write(buffer)

load()