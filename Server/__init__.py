import http.server
import threading
import socket
import socketserver
import time
from nut import Config
import sys
import os
from os import listdir
import re
from nut import Print
import urllib
from nut import Users
import base64
from urllib.parse import urlparse
from urllib.parse import parse_qs

import Server.Controller.Api
import __main__


global httpd
global sock
global addr
global mimes

mimes = {}
httpd = None
sock = None
addr = None
threads = []

mappings = {'api': Server.Controller.Api}

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
		self.headers = handler.headers
		self.path = handler.path
		self.head = False
		self.url = urlparse(self.path)

		try:
			length = int(self.headers['Content-Length'])
			if not length:
				self.post = None
			else:
				self.post = handler.rfile.read(length)
				#Print.info('reading %s bytes from post' % self.headers['Content-Length'])
		except:
			self.post = None

		self.bits = [urllib.parse.unquote(x) for x in self.url.path.split('/') if x]
		self.query = parse_qs(self.url.query)

		try:
			for k,v in self.query.items():
				self.query[k] = v[0];
		except:
			pass

		self.user = None

	def setHead(self, h):
		self.head = h

class NutResponse:
	def __init__(self, handler):
		self.handler = handler
		self.bytesSent = 0
		self.status = 200
		self.head = False
		self.headersSent = False
		self.headers = {'Content-type': 'text/html'}

	def setHead(self, h):
		self.head = h

	def setStatus(self, s):
		self.status = s

	def setHeader(self, k, v):
		self.headers[k] = v

	def setMime(self, fileName):
		try:
			name, ext = os.path.splitext(fileName)

			if ext in mimes:
				self.headers['Content-type'] = mimes[ext]
			else:
				raise IOError('Mime not found')
		except:
			pass

	def attachFile(self, fileName):
		#Print.info('Attaching file ' + fileName)
		self.setMime(fileName)
		self.headers['Content-Disposition'] = 'attachment; filename=' + fileName

	def sendHeader(self):
		self.handler.send_response(self.status)

		for k,v in self.headers.items():
			self.handler.send_header(k, v)

		self.handler.end_headers()
		self.headersSent = True

	def write(self, data):
		if self.bytesSent == 0 and not self.headersSent:
			self.sendHeader()

		if type(data) == str:
			data = data.encode('utf-8')

		self.bytesSent += len(data)

		return self.handler.wfile.write(data)

def Response400(request, response, error='400'):
	response.setStatus(400)
	response.write(error)

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

def route(request, response, verb = 'get'):
	try:
		print('routing')
		if len(request.bits) > 0 and request.bits[0] in mappings:
			i = request.bits[1]
			methodName = verb + i[0].capitalize() + i[1:]
			print('routing to ' + methodName)
			method = getattr(mappings[request.bits[0]], methodName, Response404)
			method(request, response, **request.query)
			return True
	except BaseException as e:
		print(str(e))
		return None
	return False

class NutHandler(http.server.BaseHTTPRequestHandler):
	def __init__(self, *args):
		self.basePath = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
		super(NutHandler, self).__init__(*args)

	def do_HEAD(self):
		request = NutRequest(self)
		response = NutResponse(self)
		request.setHead(True)
		response.setHead(True)
		
		if self.headers['Authorization'] == None:
			return Response401(request, response)

		id, password = base64.b64decode(self.headers['Authorization'].split(' ')[1]).decode().split(':')

		request.user = Users.auth(id, password, self.client_address[0])

		if not request.user:
			return Response401(request, response)
		
		try:
			if len(request.bits) > 0 and request.bits[0] in mappings:
				i = request.bits[1]
				methodName = 'get' + i[0].capitalize() + i[1:]
				method = getattr(mappings[request.bits[0]], methodName, Response404)
				method(request, response, **request.query)
			else:
				self.handleFile(request, response)
		except BaseException as e:
				self.wfile.write(Response500(request, response))

	def do(self, verb = 'get'):
		request = NutRequest(self)
		response = NutResponse(self)
		
		if self.headers['Authorization'] == None:
			return Response401(request, response)

		id, password = base64.b64decode(self.headers['Authorization'].split(' ')[1]).decode().split(':')

		request.user = Users.auth(id, password, self.client_address[0])

		if not request.user:
			return Response401(request, response)

		try:
			if not route(request, response, verb):
				self.handleFile(request, response)
		except BaseException as e:
				self.wfile.write(Response500(request, response))

	def do_GET(self):
		self.do('get')


	def do_POST(self):
		self.do('post')


	def handleFile(self, request, response):
		path = os.path.abspath(self.basePath + '/public_html' + self.path)
		if not path.startswith(self.basePath):
			raise IOError('invalid path requested: ' + self.basePath + ' vs ' + path)

		if os.path.isdir(path):
			path += '/index.html'

		if not os.path.isfile(path):
			return Response404(request, response)
		response.setMime(path)
		with open(path, 'rb') as f:
			response.write(f.read())