import http.server
import threading
import socket
import socketserver
import time
import sys

#sys.path.append('./lib/web')

import Web.Api

HOST_NAME = 'localhost'
PORT_NUMBER = 9000

global httpd
global sock
global addr

httpd = None
sock = None
addr = None
threads = []

class Thread(threading.Thread):
	def __init__(self, i):
		threads.append(self)
		threading.Thread.__init__(self)
		self.i = i
		self.daemon = True
		self.start()
	def run(self):
		httpd = http.server.HTTPServer(addr, NutHandler, False)

		httpd.socket = sock
		httpd.server_bind = self.server_close = lambda self: None

		httpd.serve_forever()

def run():
	global httpd
	global sock
	global addr

	print(time.asctime(), 'Server Starts - %s:%s' % (HOST_NAME, PORT_NUMBER))
	try:
		addr = (HOST_NAME, PORT_NUMBER)
		sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind(addr)
		sock.listen(5)

		[Thread(i) for i in range(4)]
		for thread in threads:
			thread.join()
	except KeyboardInterrupt:
		pass

	print(time.asctime(), 'Server Stops - %s:%s' % (HOST_NAME, PORT_NUMBER))

class NutRequest:
	def __init__(self, handler):
		self.handler = handler
		self.path = handler.path
		self.bits = [x for x in self.path.split('/') if x]

class NutResponse:
	def __init__(self, handler):
		self.handler = handler
		self.bytesSent = 0
		self.status = 200
		self.headers = {'Content-type': 'text/html'}

	def setStatus(self, s):
		self.status = s

	def sendHeader(self):
		self.handler.send_response(self.status)

		for k,v in self.headers.items():
			self.handler.send_header(k, v)

		self.handler.end_headers()

	def write(self, data):
		if self.bytesSent == 0:
			self.sendHeader()

		if type(data) == str:
			data = data.encode('utf-8')

		return self.handler.wfile.write(data)

def Response404(request, response):
	response.setStatus(404)
	response.write('404')

def Response500(request, response):
	response.setStatus(500)
	response.write('500')


class NutHandler(http.server.BaseHTTPRequestHandler):
	def __init__(self, *args):
		self.mappings = {'api': Web.Api}
		super(NutHandler, self).__init__(*args)

	def do_HEAD(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()

	def do_GET(self):
		request = NutRequest(self)
		response = NutResponse(self)


		if request.bits[0] in self.mappings:
			try:
				i = request.bits[1]
				methodName = 'get' + i[0].capitalize() + i[1:]
				method = getattr(self.mappings[request.bits[0]], methodName, Response404)
				method(request, response)
			except BaseException as e:
				self.wfile.write(Response500(request, response))
		else:
			self.respond({'status': 500})

	def handle_http(self, status_code, path):
		self.send_response(status_code)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		content = '''
		<html><head><title>Title goes here.</title></head>
		<body><p>This is a test.</p>
		<p>You accessed path: {}</p>
		</body></html>
		'''.format(path)
		return bytes(content, 'UTF-8')

	def respond(self, opts):
		response = self.handle_http(opts['status'], self.path)
		self.wfile.write(response)