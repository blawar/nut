import os
import unittest

from pyfakefs.fake_filesystem_unittest import TestCase

from nut import Users

_DEFAULT_USER = 'guest'
_DEFAULT_PASSWORD = 'guest'
_DEFAULT_HOST = 'localhost'

class NutUsersTest(TestCase):
	"""Tests for nut/Users.py
	"""
	def setUp(self):
		self.setUpPyfakefs()

	def test_first_user(self):
		first_user = Users.first()
		self.assertEqual(first_user.id, _DEFAULT_USER)
		self.assertEqual(first_user.password, _DEFAULT_PASSWORD)

	def test_auth_positive(self):
		auth_result = Users.auth(_DEFAULT_USER, _DEFAULT_PASSWORD, _DEFAULT_HOST)
		self.assertEqual(auth_result.id, _DEFAULT_USER)
		self.assertEqual(auth_result.password, _DEFAULT_PASSWORD)

		self.assertEqual(Users.first().remoteAddr, None)
		self.assertIsNotNone(Users.auth(_DEFAULT_USER, _DEFAULT_PASSWORD, 'any_adrr'))

	def test_auth_negative(self):
		self.assertEqual(Users.auth(_DEFAULT_USER, 'wrong_pwd', _DEFAULT_HOST), None)
		self.assertEqual(Users.auth('wrong_user', _DEFAULT_PASSWORD, _DEFAULT_HOST), None)

	def test_list_default_users(self):
		values = Users.users.values()
		self.assertIsNotNone(values)
		self.assertGreater(len(values), 0)

	def test_export(self):
		FILENAME = 'conf/users.conf'
		self.assertFalse(os.path.exists(FILENAME))
		Users.export()
		self.assertTrue(os.path.exists(FILENAME))

	def test_user_serialize(self):
		user = Users.first()
		serialized = user.serialize()
		self.assertEqual(serialized, "guest|guest")

	def test_user_load_csv(self):
		user = Users.User()
		USER = 'user1'
		PASSWORD = 'password1'
		csv = f'{USER}|{PASSWORD}'
		user.loadCsv(csv, map=['id', 'password'])
		self.assertEqual(user.id, USER)
		self.assertEqual(user.password, PASSWORD)

	def test_user_load_csv_with_empty_map(self):
		user = Users.User()
		user.loadCsv("id|pwd")
		self.assertIsNone(user.id)
		self.assertIsNone(user.password)

if __name__ == "__main__":
	unittest.main()
