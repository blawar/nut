import unittest

import nut

REGION_LANG_TEST_DATA = [{'region': 'US', 'lang': 'en', 'expected_score': 119}, \
	{'region': 'FR', 'lang': 'fr', 'expected_score': 118}, \
	{'region': 'JA', 'lang': 'jp', 'expected_score': 110}, \
	{'region': 'ES', 'lang': 'es', 'expected_score': 116}]

class NutTest(unittest.TestCase):
	"""Tests for nut/__init__.py
	"""
	def test_region_language(self):
		for data in REGION_LANG_TEST_DATA:
			lang = nut.RegionLanguage(data['region'], data['lang'], data['region'], data['lang'])
			self.assertEqual(lang.region, data['region'])
			self.assertEqual(lang.language, data['lang'])
			self.assertEqual(lang.preferredRegion, data['region'])
			self.assertEqual(lang.preferredLanguage, data['lang'])
			lang.print()
			self.assertEqual(lang.score, data['expected_score'])

	def test_region_language_with_preffered(self):
		data = REGION_LANG_TEST_DATA[0]
		PREFERRED_REGION = 'RU'
		PREFERRED_LANGUAGE = 'ru'
		self.assertNotEqual(data['region'], PREFERRED_REGION)
		self.assertNotEqual(data['lang'], PREFERRED_LANGUAGE)
		lang = nut.RegionLanguage(data['region'], data['lang'], PREFERRED_REGION, PREFERRED_LANGUAGE)
		self.assertEqual(lang.region, data['region'])
		self.assertEqual(lang.language, data['lang'])
		self.assertEqual(lang.preferredRegion, PREFERRED_REGION)
		self.assertEqual(lang.preferredLanguage, PREFERRED_LANGUAGE)
		self.assertEqual(lang.score, 9)

	def test_region_language_less(self):
		data = REGION_LANG_TEST_DATA[0]
		PREFERRED_REGION = 'RU'
		PREFERRED_LANGUAGE = 'ru'
		lang1 = nut.RegionLanguage(data['region'], data['lang'], data['region'], data['lang'])
		lang2 = nut.RegionLanguage(data['region'], data['lang'], PREFERRED_REGION, PREFERRED_LANGUAGE)
		self.assertTrue(lang1 > lang2)


if __name__ == "__main__":
	unittest.main()
