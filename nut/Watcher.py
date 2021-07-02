import time
import os.path
from watchdog.observers import Observer
from watchdog.events import RegexMatchingEventHandler
from nut import Nsps
from nut import Config

class FileEventHandler(RegexMatchingEventHandler):
	def __init__(self):
		super().__init__([r".*\.ns[pz]$", r".*\.xc[iz]$"])

	def on_created(self, event):
		print('added: ' + event.src_path)
		Nsps.registerFile(event.src_path)

	def on_deleted(self, event):
		print('deleted: ' + event.src_path)
		Nsps.unregisterFile(event.src_path)

	def on_moved(self, event):
		print('moved: %s -> %s' % (event.src_path, event.dest_path))
		Nsps.moveFile(event.src_path, event.dest_path)

	def process(self, event):
		pass

class Watcher:
	def __init__(self, src_path):
		self.__src_path = src_path
		self.__event_handler = FileEventHandler()
		self.__event_observer = Observer()

	def run(self):
		self.start()
		try:
			while True:
				time.sleep(1)
		except KeyboardInterrupt:
			self.stop()

	def start(self):
		self.__schedule()
		self.__event_observer.start()

	def stop(self):
		self.__event_observer.stop()
		self.__event_observer.join()

	def __schedule(self):
		self.__event_observer.schedule(
			self.__event_handler,
			self.__src_path,
			recursive=True
		)

watchers = {}

def refresh():
	global watchers
	scanPaths = []

	for path in Config.paths.scan:
		scanPaths.append(os.path.abspath(path))

	for path, watcher in watchers.items():
		path = os.path.abspath(path)

		if path not in scanPaths:
			watcher.stop()
			watchers[path] = None
			continue

	for path in scanPaths:
		if path not in watchers or watchers[path] is None:
			watchers[path] = Watcher(path)
			watchers[path].start()

def start():
	if len(watchers):
		return False

	refresh()
	return True

