global silent
enableInfo = True
enableError = True
enableWarning = True
enableDebug = False

silent = False

def info(s):
	if not silent and enableInfo:
		print(s)

def error(s):
	if not silent and enableError:
		print(s)

def warning(s):
	if not silent and enableWarning:
		print(s)

def debug(s):
	if not silent and enableDebug:
		print(s)