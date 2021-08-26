from Fs.Xci import Xci
from Fs.Nca import Nca
from Fs.Nsp import Nsp
from Fs.Rom import Rom
from Fs.Nacp import Nacp
from Fs.Pfs0 import Pfs0
from Fs.Ticket import Ticket
from Fs.Cnmt import Cnmt
from Fs.File import File

def factory(name, file=None, mode='rb'):
	if name.endswith('.xci') or name.endswith('.xcz'):
		f = Xci(file, mode)
	elif name.endswith('.nsp') or name.endswith('.nsz'):
		f = Nsp(file, mode)
	elif name.endswith('.nsx'):
		f = Nsp(file, mode)
	elif name.endswith('.nca') or name.endswith('.ncz'):
		f = Nca(file, mode)
	elif name.endswith('.nacp'):
		f = Nacp(file, mode)
	elif name.endswith('.tik'):
		f = Ticket(file, mode)
	elif name.endswith('.cnmt'):
		f = Cnmt(file, mode)
	else:
		f = File(file, mode)

	return f
