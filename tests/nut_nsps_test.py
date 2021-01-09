import os
import unittest
from importlib import reload
#from pathlib import Path

from pyfakefs.fake_filesystem_unittest import TestCase

from nut import Nsps

_TITLEDB_FILES_PATH = 'titledb/files.json'
_SCAN_PATH = 'NSPs'

nsp_fixture_path = os.path.join(os.path.dirname(__file__), 'assets')


class NutNspsTest(TestCase):
	"""Tests for nut/Nsps.py
	"""

	def __prepare_hbl_title_fixture(self, name):
		_content = f"""[{{
		"extractedNcaMeta": 0,
		"fileSize": null,
		"hasValidTicket": true,
		"path": "{name}",
		"timestamp": 1610138007.788741,
		"titleId": "0000000000000000",
		"version": "0"
	}}]
	"""
		self.__prepare_nsp_fixture(name, _content)

	def __prepare_nsp_fixture(self, name, content):
		self.fs.create_file(_TITLEDB_FILES_PATH, contents=content)
		self.fs.add_real_directory(nsp_fixture_path)
		_nsp_contents = None
		with open(os.path.join(nsp_fixture_path, name), 'rb') as f:
			_nsp_contents = f.read()

		self.fs.create_file(name, contents=_nsp_contents)

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

	def test_load_with_empty_filesize_in_files_json(self):
		_title_id = '0000000000000000'
		_nsp_hbl_name = f"hbl [{_title_id}].nsp"
		self.__prepare_hbl_title_fixture(_nsp_hbl_name)
		Nsps.load()
		_nsp = Nsps.get('/' + _nsp_hbl_name)
		self.assertIsNotNone(_nsp)
		self.assertGreater(_nsp.fileSize, 0)
		self.assertEqual(_nsp.titleId, _title_id)

if __name__ == "__main__":
	unittest.main()
