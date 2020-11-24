import os
import unittest
from importlib import reload
#from pathlib import Path

from pyfakefs.fake_filesystem_unittest import TestCase

from nut import Nsps

_FILENAME = 'titledb/files.json'
_SCAN_PATH = 'NSPs'

class NutNspsTest(TestCase):
	"""Tests for nut/Nsps.py
	"""

	def setUp(self):
		self.setUpPyfakefs()

	def test_scan_missing_path(self):
		with self.assertRaises(FileNotFoundError):
			Nsps.scan(_SCAN_PATH)

	def test_scan_empty_dir(self):
		self.fs.makedir(_SCAN_PATH)
		self.fs.makedir('titledb')
		Nsps.scan(_SCAN_PATH)

	def test_renames_old_filename(self):
		filename = 'files.json'
		self.fs.create_file(filename)
		self.fs.makedir('titledb')
		reload(Nsps)
		self.assertFalse(os.path.exists(filename))

	def test_scan(self):
		#self.fs.makedir(_SCAN_PATH)
		#self.fs.makedir('titledb')
		#self.fs.create_file(Path(_SCAN_PATH) / "1.nsp")
		#Nsps.scan(_SCAN_PATH)
		#while Status.isActive():
		#	continue
		pass

if __name__ == "__main__":
	unittest.main()
