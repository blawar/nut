import time
from watchdog.observers import Observer
from watchdog.events import RegexMatchingEventHandler
from nut import Nsps

class FileEventHandler(RegexMatchingEventHandler):
	def __init__(self):
		super().__init__([r".*\.ns[pz]$", r".*\.xc[iz]$"])

	def on_created(self, event):
		print('added: ' + event.src_path)
		Nsps.registerFile(event.src_path)

	def on_deleted(self, event):
		print('deleted: ' + event.src_path)
		Nsps.unregisterFile(event.src_path)

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


watcher = Watcher('.')
watcher.run()
