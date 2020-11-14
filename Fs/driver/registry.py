schemeDriverMap = {}

def add(scheme, driver):
	global schemeDriverMap
	schemeDriverMap[scheme.lower()] = driver

def get(scheme):
	if scheme in schemeDriverMap:
		return schemeDriverMap[scheme]()

	if '' in schemeDriverMap:
		return schemeDriverMap['']()
	return None

def isNative(scheme):
	if scheme in schemeDriverMap:
		return False

	if '' in schemeDriverMap:
		return True
	return None
