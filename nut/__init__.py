from nut import Titles
from nut import Nsps
from nut import Print

def refreshRegions():
	for region in Config.regionLanguages():
		for language in Config.regionLanguages()[region]:
			for i in Titles.data(region, language):
				regionTitle = Titles.data(region, language)[i]

				if regionTitle.id:
					title = Titles.get(regionTitle.id, None, None)

					if not hasattr(title, 'regions') or not title.regions:
						title.regions = []

					if not hasattr(title, 'languages') or not title.languages:
						title.languages = []

					if not region in title.regions:
						title.regions.append(region)

					if not language in title.languages:
						title.languages.append(language)
	Titles.save()

def importRegion(region = 'US', language = 'en'):
	if not region in Config.regionLanguages() or language not in Config.regionLanguages()[region]:
		Print.error('Could not locate %s/%s !' % (region, language))
		return False

	for region2 in Config.regionLanguages():
		for language2 in Config.regionLanguages()[region2]:
			for nsuId, regionTitle in Titles.data(region2, language2).items():
				if not regionTitle.id:
					continue
				title = Titles.get(regionTitle.id, None, None)
				title.importFrom(regionTitle, region2, language2)

	for region2 in Config.regionLanguages():
		for language2 in Config.regionLanguages()[region2]:
			if language2 != language:
				continue
			for nsuId, regionTitle in Titles.data(region2, language2).items():
				if not regionTitle.id:
					continue
				title = Titles.get(regionTitle.id, None, None)
				title.importFrom(regionTitle, region2, language2)


	for nsuId, regionTitle in Titles.data(region, language).items():
		if not regionTitle.id:
			continue

		title = Titles.get(regionTitle.id, None, None)
		title.importFrom(regionTitle, region, language)

	Titles.loadTxtDatabases()
	Titles.save()

isInitTitles = False

def initTitles():
	global isInitTitles
	if isInitTitles:
		return

	isInitTitles = True

	Titles.load()

	Nsps.load()
	Titles.queue.load()

isInitFiles = False
def initFiles():
	global isInitFiles
	if isInitFiles:
		return

	isInitFiles = True

	Nsps.load()

global hasScanned
hasScanned = False

def scan():
	global hasScanned

	#if hasScanned:
	#	return
	hasScanned = True
	initTitles()
	initFiles()

	
	refreshRegions()
	importRegion(Config.region, Config.language)

	r = Nsps.scan(Config.paths.scan)
	Titles.save()
	return r
