def regions():
	return ['CA', 'MX', 'CO', 'AR', 'CL', 'PE', 'JP', 'KR', 'HK', 'AU', 'NZ', 'AT', 'BE', 'CZ', 'DK', 'DE', 'ES', 'FI', 'FR', 'GR', 'HU', 'IT', 'NL', 'NO', 'PL', 'PT', 'RU', 'ZA', 'SE', 'GB', 'US']

def calc_sha256(fPath):
	f = open(fPath, 'rb')
	fSize = os.path.getsize(fPath)
	hash = sha256()
	
	if fSize >= 10000:
		t = Status.create(fSize, unit='B', desc=os.path.basename(fPath))
		while True:
			buf = f.read(4096)
			if not buf:
				break
			hash.update(buf)
			t.update(len(buf))
		t.close()
	else:
		hash.update(f.read())
	f.close()
	return hash.hexdigest()

def download_title(gameDir, titleId, ver, tkey=None, nspRepack=False, n='', verify=False, retry=0):
	try:
		Print.info('Downloading %s [%s] v%s:' % (get_name(titleId), titleId, ver))
		titleId = titleId.lower()
		isNsx = False
	
		if tkey:
			tkey = tkey.lower()
		
		if len(titleId) != 16:
			titleId = (16 - len(titleId)) * '0' + titleId

		url = 'https://atum%s.hac.%s.d4c.nintendo.net/t/a/%s/%s?device_id=%s' % (n, env, titleId, ver, deviceId)
		Print.debug(url)
		try:
			r = make_request('HEAD', url)
		except Exception as e:
			Print.error("Error downloading title. Check for incorrect titleid or version: " + str(e))
			return
		CNMTid = r.headers.get('X-Nintendo-Content-ID')

		if CNMTid == None:
			Print.info('title not available on CDN')
			return

		Print.debug('Downloading CNMT (%s.cnmt.nca)...' % CNMTid)
		url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/a/%s?device_id=%s' % (n, env, CNMTid, deviceId)
		fPath = os.path.join(gameDir, CNMTid + '.cnmt.nca')
		cnmtNCA = download_file(url, fPath, titleId)
		cnmtDir = decrypt_NCA(cnmtNCA)
		CNMT = cnmt(os.path.join(cnmtDir, 'section0', os.listdir(os.path.join(cnmtDir, 'section0'))[0]),
					os.path.join(cnmtDir, 'Header.bin'))

		if nspRepack == True:
			outf = os.path.join(gameDir, '%s.xml' % os.path.basename(cnmtNCA.strip('.nca')))
			cnmtXML = CNMT.gen_xml(cnmtNCA, outf)

			rightsID = '%s%s%s' % (titleId, (16 - len(CNMT.mkeyrev)) * '0', CNMT.mkeyrev)

			tikPath = os.path.join(gameDir, '%s.tik' % rightsID)
			certPath = os.path.join(gameDir, '%s.cert' % rightsID)
			if CNMT.type == 'Application' or CNMT.type == 'AddOnContent':
				shutil.copy(os.path.join(os.path.dirname(__file__), 'Certificate.cert'), certPath)

				if tkey:
					with open(os.path.join(os.path.dirname(__file__), 'Ticket.tik'), 'rb') as intik:
						data = bytearray(intik.read())
						data[0x180:0x190] = uhx(tkey)
						data[0x285] = int(CNMT.mkeyrev)
						data[0x2A0:0x2B0] = uhx(rightsID)

						with open(tikPath, 'wb') as outtik:
							outtik.write(data)
				else:
					isNsx = True
					with open(os.path.join(os.path.dirname(__file__), 'Ticket.tik'), 'rb') as intik:
						data = bytearray(intik.read())
						data[0x180:0x190] = uhx('00000000000000000000000000000000')
						data[0x285] = int(CNMT.mkeyrev)
						data[0x2A0:0x2B0] = uhx(rightsID)

						with open(tikPath, 'wb') as outtik:
							outtik.write(data)

				Print.debug('Generated %s and %s!' % (os.path.basename(certPath), os.path.basename(tikPath)))
			elif CNMT.type == 'Patch':
				Print.debug('Downloading cetk...')

				with open(download_cetk(rightsID, os.path.join(gameDir, '%s.cetk' % rightsID)), 'rb') as cetk:
					cetk.seek(0x180)
					tkey = hx(cetk.read(0x10)).decode()
					Print.info('Titlekey: %s' % tkey)

					with open(tikPath, 'wb') as tik:
						cetk.seek(0x0)
						tik.write(cetk.read(0x2C0))

					with open(certPath, 'wb') as cert:
						cetk.seek(0x2C0)
						cert.write(cetk.read(0x700))

				Print.debug('Extracted %s and %s from cetk!' % (os.path.basename(certPath), os.path.basename(tikPath)))

		NCAs = {
			0: [],
			1: [],
			2: [],
			3: [],
			4: [],
			5: [],
			6: [],
		}
		for type in [0, 3, 4, 5, 1, 2, 6]:  # Download smaller files first
			for ncaID in CNMT.parse(CNMT.ncaTypes[type]):
				Print.debug('Downloading %s entry (%s.nca)...' % (CNMT.ncaTypes[type], ncaID))
				url = 'https://atum%s.hac.%s.d4c.nintendo.net/c/c/%s?device_id=%s' % (n, env, ncaID, deviceId)
				fPath = os.path.join(gameDir, ncaID + '.nca')
				NCAs[type].append(download_file(url, fPath, titleId))
				if verify:
					if calc_sha256(fPath) != CNMT.parse(CNMT.ncaTypes[type])[ncaID][2]:
						Print.error('%s is corrupted, hashes don\'t match!' % os.path.basename(fPath))
					else:
						Print.info('Verified %s...' % os.path.basename(fPath))

		if nspRepack == True:
			files = []
			files.append(certPath)
			files.append(tikPath)
			for key in [1, 5, 2, 4, 6]:
				files.extend(NCAs[key])
			files.append(cnmtNCA)
			files.append(cnmtXML)
			files.extend(NCAs[3])
			return files
	except KeyboardInterrupt:
		raise
	except BaseException as e:
		retry += 1

		if retry < 5:
			Print.error('An error occured while downloading, retry attempt %d: %s' % (retry, str(e)))
			download_title(gameDir, titleId, ver, tkey, nspRepack, n, verify, retry)
		else:
			raise


def download_game(titleId, ver, tkey=None, nspRepack=False, name='', verify=False):
	name = get_name(titleId)
	gameType = ''

	if name == 'Uknown Title':
		temp = "[" + titleId + "]"
	else:
		temp = name + " [" + titleId + "]"

	outputDir = os.path.join(os.path.dirname(__file__), nspout)

	basetitleId = ''
	if titleId.endswith('000'):  # Base game
		gameDir = os.path.join(outputDir, temp)
		gameType = 'BASE'
	elif titleId.endswith('800'):  # Update
		basetitleId = '%s000' % titleId[:-3]
		gameDir = os.path.join(outputDir, temp)
		gameType = 'UPD'
	else:  # DLC
		basetitleId = '%s%s000' % (titleId[:-4], str(int(titleId[-4], 16) - 1))
		gameDir = os.path.join(outputDir, temp)
		gameType = 'DLC'

	os.makedirs(gameDir, exist_ok=True)

	if not os.path.exists(outputDir):
		os.makedirs(outputDir, exist_ok=True)

	if name != "":
		if gameType == 'BASE':
			 outf = os.path.join(outputDir, '%s [%s][v%s]' % (name,titleId,ver))
		else:
			outf = os.path.join(outputDir, '%s [%s][%s][v%s]' % (name,gameType,titleId,ver))
	else:
		if gameType == 'BASE':
			outf = os.path.join(outputDir, '%s [v%s]' % (titleId,ver))
		else:
			outf = os.path.join(outputDir, '%s [%s][v%s]' % (titleId,gameType,ver))

	if truncateName:
		name = name.replace(' ','')[0:20]
		outf = os.path.join(outputDir, '%s%sv%s' % (name,titleId,ver))


	if tkey:
		outf = outf + '.nsp'
	else:
		outf = outf + '.nsx'

	for item in os.listdir(outputDir):
		if item.find('%s' % titleId) != -1:
			if item.find('v%s' % ver) != -1:
				Print.info('%s already exists, skipping download' % outf)
				shutil.rmtree(gameDir)
				return


	files = download_title(gameDir, titleId, ver, tkey, nspRepack, verify=verify)

	if gameType != 'UPD':
		if tkey:
			verified = verify_NCA(get_biggest_file(gameDir), tkey)

			if not verified:
				shutil.rmtree(gameDir)
				Print.debug('cleaned up downloaded content')
				return

	if nspRepack == True:
		if files == None:
			return
		NSP = nsp(outf, files)
		Print.debug('starting repack, This may take a while')
		NSP.repack()
		shutil.rmtree(gameDir)
		Print.debug('cleaned up downloaded content')

		if enxhop:
			enxhopDir = os.path.join(outputDir,'switch')
			os.makedirs(enxhopDir, exist_ok=True)
			with open(os.path.join(enxhopDir,'eNXhop.txt'), 'a+') as f:
				f.write(titleId + '\n')

		return outf

	return gameDir



class cnmt:
	def __init__(self, fPath, hdPath):
		self.packTypes = {0x1: 'SystemProgram',
						  0x2: 'SystemData',
						  0x3: 'SystemUpdate',
						  0x4: 'BootImagePackage',
						  0x5: 'BootImagePackageSafe',
						  0x80: 'Application',
						  0x81: 'Patch',
						  0x82: 'AddOnContent',
						  0x83: 'Delta'}

		self.ncaTypes = {0: 'Meta', 1: 'Program', 2: 'Data', 3: 'Control',
						 4: 'HtmlDocument', 5: 'LegalInformation', 6: 'DeltaFragment'}

		f = open(fPath, 'rb')

		self.path = fPath
		self.type = self.packTypes[read_u8(f, 0xC)]
		self.id = '0%s' % format(read_u64(f, 0x0), 'x')
		self.ver = str(read_u32(f, 0x8))
		self.sysver = str(read_u64(f, 0x28))
		self.dlsysver = str(read_u64(f, 0x18))
		self.digest = hx(read_at(f, f.seek(0, 2) - 0x20, f.seek(0, 2))).decode()

		with open(hdPath, 'rb') as ncaHd:
			self.mkeyrev = str(read_u8(ncaHd, 0x220))

		f.close()

	def parse(self, ncaType=''):
		f = open(self.path, 'rb')

		data = {}
		if self.type == 'SystemUpdate':
			EntriesNB = read_u16(f, 0x12)
			for n in range(0x20, 0x10 * EntriesNB, 0x10):
				titleId = hex(read_u64(f, n))[2:]
				if len(titleId) != 16:
					titleId = '%s%s' % ((16 - len(titleId)) * '0', titleId)
				ver = str(read_u32(f, n + 0x8))
				packType = self.packTypes[read_u8(f, n + 0xC)]

				data[titleId] = ver, packType
		else:
			tableOffset = read_u16(f, 0xE)
			contentEntriesNB = read_u16(f, 0x10)
			cmetadata = {}
			for n in range(contentEntriesNB):
				offset = 0x20 + tableOffset + 0x38 * n
				hash = hx(read_at(f, offset, 0x20)).decode()
				titleId = hx(read_at(f, offset + 0x20, 0x10)).decode()
				size = str(read_u48(f, offset + 0x30))
				type = self.ncaTypes[read_u16(f, offset + 0x36)]

				if type == ncaType or ncaType == '':
					data[titleId] = type, size, hash

		f.close()
		return data
