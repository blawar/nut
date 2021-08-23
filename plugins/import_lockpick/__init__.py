from nut import Config, Hook, Titles, Print
import nut

def parse(parser):
	parser.add_argument('--import-title-keys', help='import title keys from lockpick RCM')
	
	
def post(args):
	if not args.import_title_keys:
		return

	nut.initTitles()
	nut.initFiles()
	with open(args.import_title_keys, 'r') as f:
		for line in f.read().split('\n'):
			if '=' not in line:
				continue
			try:
				rightsId, key = line.split('=')
				rightsId = rightsId.strip()
				titleId = rightsId[0:16]
				key = key.strip()
				title = Titles.get(titleId)
				
				nsp = title.getLatestNsp()
				nsz = title.getLatestNsz()
				print(nsp)
				if not nsp and not nsz:
					Print.info('title import: new title detected: %s - %s' % (title.id, title.name))
				elif not title.key:
					Print.info('title import: new title key detected: %s - %s' % (title.id, title.name))
				title.rightsId = rightsId
				title.key = key
			except:
				raise
	Titles.save()

Hook.register('args.pre', parse)
Hook.register('args.post', post)


