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
	ext = name.split('.')[-1]
	if ext == 'xci' or ext == 'xcz':
		f = Xci(file, mode)
	elif ext == 'nsp' or ext == 'nsz' or ext == 'nsx':
		f = Nsp(file, mode)
	elif ext == 'nca' or ext == 'ncz':
		f = Nca(file, mode)
	elif ext == 'nacp':
		f = Nacp(file, mode)
	elif ext == 'tik':
		f = Ticket(file, mode)
	elif ext == 'cnmt':
		f = Cnmt(file, mode)
	else:
		f = File(file, mode)

	return f
