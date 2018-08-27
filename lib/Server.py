import http.server
import threading
import socket
import socketserver
import time
import Config
import sys
import os
import Print
import urllib
import Users
import base64

import Web.Api


global httpd
global sock
global addr
global mimes

mimes = {}
httpd = None
sock = None
addr = None
threads = []

mimes = {
		'.css': 'text/css',
		'.js': 'application/javascript',
		'.html': 'text/html',
		'.png': 'image/png',
		'.nsx': 'application/octet-stream',
		'.nsp': 'application/octet-stream',
		'.jpg': 'image/jpeg'
	}

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

	Print.info(time.asctime() + ' Server Starts - %s:%s' % (Config.server.hostname, Config.server.port))
	try:
		addr = (Config.server.hostname, Config.server.port)
		sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind(addr)
		sock.listen(5)

		[Thread(i) for i in range(16)]
		for thread in threads:
			thread.join()
	except KeyboardInterrupt:
		pass

	Print.info(time.asctime() + ' Server Stops - %s:%s' % (Config.server.hostname, Config.server.port))

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

	def setMime(self, fileName):
		name, ext = os.path.splitext(fileName)

		if ext in mimes:
			self.headers['Content-type'] = mimes[ext]

	def attachFile(self, fileName):
		Print.info('Attaching file ' + fileName)
		self.setMime(fileName)
		self.headers['Content-Disposition'] = 'attachment; filename=' + fileName

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

		self.bytesSent += len(data)

		return self.handler.wfile.write(data)

def Response404(request, response):
	response.setStatus(404)
	response.write('404')

def Response500(request, response):
	response.setStatus(500)
	response.write('500')

def Response401(request, response):
	response.setStatus(401)
	response.headers['WWW-Authenticate'] = 'Basic realm=\"Nut\"'
	response.write('401')


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

		if self.headers['Authorization'] == None:
			return Response401(request, response)

		id, password = base64.b64decode(self.headers['Authorization'].split(' ')[1]).decode().split(':')

		if not Users.auth(id, password, self.client_address[0]):
			return Response401(request, response)

		try:
			if len(request.bits) > 0 and request.bits[0] in self.mappings:
				i = request.bits[1]
				methodName = 'get' + i[0].capitalize() + i[1:]
				method = getattr(self.mappings[request.bits[0]], methodName, Response404)
				method(request, response)
			else:
				self.handleFile(request, response)
		except BaseException as e:
				self.wfile.write(Response500(request, response))

	def handleFile(self, request, response):
		path = os.path.abspath('public_html' + self.path)

		if os.path.isdir(path):
			path += '/index.html'

		if not os.path.isfile(path):
			return Response404(request, response)
		response.setMime(path)
		with open(path, 'rb') as f:
			response.write(f.read())