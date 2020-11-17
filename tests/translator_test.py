import unittest

from pyfakefs.fake_filesystem_unittest import TestCase
from nut import Config
from translator import tr, reload

ABOUT_KEY = "ABOUT"
TRANSLATION_FILE = "translate.json"

TRANSLATION_FILE_CONTENT =	"""{
	"None": {
		"ABOUT": "About"
	},
	"ru": {
		"ABOUT": "\u041e \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0435"}
}
"""

class TranslatorTest(TestCase):
	"""TranslatorTest
	"""
	def setUp(self):
		self.setUpPyfakefs()

	def test_missing_lang_file(self):
		self.assertEqual(tr(ABOUT_KEY), ABOUT_KEY)
		self.assertEqual(tr(""), "")

	def test_translation_to_english(self):
		self.fs.create_file(TRANSLATION_FILE, contents=TRANSLATION_FILE_CONTENT)
		reload(TRANSLATION_FILE)
		self.assertEqual(Config.language, "en")
		self.assertEqual(tr(ABOUT_KEY), "About")

	def test_translation_to_russian(self):
		self.fs.create_file(TRANSLATION_FILE, contents=TRANSLATION_FILE_CONTENT)
		Config.language="ru"
		reload(TRANSLATION_FILE)
		self.assertEqual(tr(ABOUT_KEY), "\u041e \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0435")

if __name__ == "__main__":
	unittest.main()
