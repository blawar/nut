class Download: # pylint: disable=too-many-instance-attributes
	"""Download-releate settings
	"""

	def __init__(self):
		self.base = True
		self.demo = False
		self.DLC = True
		self.update = False
		self.sansTitleKey = False
		self.deltas = False
		self.regions = []
		self.rankMin = None
		self.rankMax = None
		self.fileSizeMax = None
		self.fileSizeMin = None
		self.ratingMin = None
		self.ratingMax = None
		self.releaseDateMin = None
		self.releaseDateMax = None

	def addRegion(self, region_):
		region_ = region_.upper()
		if region_ not in self.regions:
			self.regions.append(region_)

	def removeRegion(self, region_):
		region_ = region_.upper()
		if region_ not in self.regions:
			return

		self.regions.remove(region_)

	def hasRegion(self, regions, default=True):
		if not self.regions or len(self.regions) == 0 or regions is None:
			return default

		for a in self.regions:
			for b in regions:
				if a == b:
					return True

		return False
