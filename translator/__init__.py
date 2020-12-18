import json

from nut import Config, Print

DEFAULT_TRANSLATION_FILE = 'public_html/translate.json'
ENGLISH_LANG_ID = "None"

_initialized = False
_lang_db = {}
_en_db = {}
_lang = ENGLISH_LANG_ID
_locale = Config.region
_file_name = ""

def reload(file_name=DEFAULT_TRANSLATION_FILE):
	global _initialized
	global _lang_db
	global _en_db
	global _lang
	global _locale
	global _file_name

	_file_name = file_name
	_lang = ENGLISH_LANG_ID if Config.language is None or Config.language == "en" else Config.language
	Print.debug(f"translation file is '{_file_name}'")
	Print.debug(f"_lang is '{_lang}'")
	try:
		with open(_file_name, encoding='utf-8') as json_file:
			data = json.load(json_file)
			_en_db = data[ENGLISH_LANG_ID]
			if _lang != ENGLISH_LANG_ID:
				_lang_db = data[_lang]
		_initialized = True
	except (FileNotFoundError, ValueError):
		Print.warning(f"missing translation file '{_file_name}' or it's not a JSON-file")
		_initialized = False
	Print.debug(f"_initialized is '{_initialized}'")
	return _initialized

def tr(str_):
	global _initialized
	global _lang_db
	global _lang
	global _lang
	global _locale
	global _file_name

	if not _initialized:
		if not reload():
			return str_

	try:
		translated = _lang_db[str_]
	except: # pylint: disable=bare-except
		try:
			translated = _en_db[str_]
		except: # pylint: disable=bare-except
			Print.warning(f"missing translation for '{str_}' key")
			translated = str_
	return translated
