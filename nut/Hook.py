import importlib
import os.path
from nut import Print

_hooks = {}
initialized = False

def init():
	global initialized
	if initialized:
		return False

	initialized = True
	path = os.path.abspath(os.path.join(__file__, '../../plugins'))

	for f in os.listdir(path):
		try:
			if not os.path.isfile(os.path.join(os.path.join(path, f), '__init__.py')) or os.path.isfile(os.path.join(os.path.join(path, f), 'disabled')):
				continue
			name = f
			importlib.import_module('plugins.%s' % name)
		except BaseException as e:
			Print.error("plugin loader exception: %s" % str(e))
	return True

def register(name, func):
	global _hooks

	if name not in _hooks:
		_hooks[name] = []

	_hooks[name].append(func)

def call(*argv):
	global _hooks

	argv = list(argv)

	if len(argv) == 0:
		return False

	name = argv.pop(0)

	if name not in _hooks:
		return False

	for func in _hooks[name]:
		try:
			func(*argv)
		except BaseException as e:
			Print.error('plugin exception: %s' % str(e))

	return True
