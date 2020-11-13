schemeDriverMap = {}

def add(scheme, driver):
	global schemeDriverMap
	schemeDriverMap[scheme.lower()] = driver

def get(scheme):
	if scheme in schemeDriverMap:
		return schemeDriverMap[scheme]()
	return None
