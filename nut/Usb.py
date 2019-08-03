'''
Copyright (c) 2018 Blake Warner

Copyright (c) 2017-2018 Adubbz	                    GNU GENERAL PUBLIC LICENSE
                        Version 3, 29 June 2007
Permission is hereby granted, free of charge, to any person obtaining a copy	
of this software and associated documentation files (the "Software"), to deal	 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
in the Software without restriction, including without limitation the rights	 Everyone is permitted to copy and distribute verbatim copies
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell	 of this license document, but changing it is not allowed.
copies of the Software, and to permit persons to whom the Software is	
furnished to do so, subject to the following conditions:	                            Preamble
 The above copyright notice and this permission notice shall be included in all	  The GNU General Public License is a free, copyleft license for
copies or substantial portions of the Software.	software and other kinds of works.
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR	  The licenses for most software and other practical works are designed
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,	to take away your freedom to share and change the works.  By contrast,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE	the GNU General Public License is intended to guarantee your freedom to
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER	share and change all versions of a program--to make sure it remains free
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,	software for all its users.  We, the Free Software Foundation, use the
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE	GNU General Public License for most of our software; it applies also to
SOFTWARE.
'''

# This script depends on PyUSB. You can get it with pip install pyusb.
# You will also need libusb installed

# My sincere apologies for this process being overly complicated. Apparently Python and Windows
# aren't very friendly :(
# Windows Instructions:
# 1. Download Zadig from https://zadig.akeo.ie/.
# 2. With your switch plugged in and DZ running, 
#	choose "List All Devices" under the options menu in Zadig, and select libnx USB comms. 
# 3. Choose libusbK from the driver list and click the "Replace Driver" button.
# 4. Run this script

# macOS Instructions:
# 1. Install Homebrew https://brew.sh
# 2. Install Python 3
#	  sudo mkdir /usr/local/Frameworks
#	  sudo chown $(whoami) /usr/local/Frameworks
#	  brew install python
# 3. Install PyUSB 
#	  pip3 install pyusb
# 4. Install libusb
#	  brew install libusb


import usb.core
import usb.util
import struct
import sys
from binascii import hexlify as hx, unhexlify as uhx
from pathlib import Path
import Server
import Server.Controller.Api
from nut import Print
import time
from urllib.parse import urlparse
from urllib.parse import parse_qs
import Server.Controller.Api

global status
status = 'initializing'

def getFiles():
	for k, f in Nsps.files.items():
		if f and f.hasValidTicket:
			o.append({'id': t.id, 'name': t.name, 'version': int(f.version) if f.version else None , 'size': f.getFileSize(), 'mtime': f.getFileModified() })

	return json.dumps(o)

class UsbResponse(Server.NutResponse):
	def __init__(self, packet):
		super(UsbResponse, self).__init__(None)
		self.packet = packet

	def sendHeader(self):
		pass

	def write(self, data):
		print('usbresponse write')
		if self.bytesSent == 0 and not self.headersSent:
			self.sendHeader()

		if type(data) == str:
			data = data.encode('utf-8')

		self.bytesSent += len(data)
		self.packet.payload = data
		self.packet.send()

		self.bytesSent += len(data)


class UsbRequest(Server.NutRequest):
	def __init__(self, url):
		self.headers = {}
		self.path = url
		self.head = False
		self.url = urlparse(self.path)

		print('url ' + self.path);

		self.bits = [x for x in self.url.path.split('/') if x]
		print(self.bits)
		self.query = parse_qs(self.url.query)

		try:
			for k,v in self.query.items():
				self.query[k] = v[0];
		except:
			pass

		self.user = None

class Packet:
	def __init__(self, i, o):
		self.size = 0
		self.payload = b''
		self.command = 0
		self.threadId = 0
		self.packetIndex = 0
		self.packetCount = 0
		self.timestamp = 0
		self.i = i
		self.o = o
		
	def recv(self, timeout = 60000):
		print('begin recv')
		header = bytes(self.i.read(32, timeout=timeout))
		print('read complete')
		magic = header[:4]
		self.command = int.from_bytes(header[4:8], byteorder='little')
		self.size = int.from_bytes(header[8:16], byteorder='little')
		self.threadId = int.from_bytes(header[16:20], byteorder='little')
		self.packetIndex = int.from_bytes(header[20:22], byteorder='little')
		self.packetCount = int.from_bytes(header[22:24], byteorder='little')
		self.timestamp = int.from_bytes(header[24:32], byteorder='little')
		
		if magic != b'\x12\x12\x12\x12':
			print('invalid magic! ' + str(magic));
			return False
		
		print('receiving %d bytes' % self.size)
		self.payload = bytes(self.i.read(self.size, timeout=0))
		return True
		
	def send(self, timeout = 60000):
		print('sending %d bytes' % len(self.payload))
		self.o.write(b'\x12\x12\x12\x12', timeout=timeout)
		self.o.write(struct.pack('<I', self.command), timeout=timeout)
		self.o.write(struct.pack('<Q', len(self.payload)), timeout=timeout) # size
		self.o.write(struct.pack('<I', 0), timeout=timeout) # threadId
		self.o.write(struct.pack('<H', 0), timeout=timeout) # packetIndex
		self.o.write(struct.pack('<H', 0), timeout=timeout) # packetCount
		self.o.write(struct.pack('<Q', 0), timeout=timeout) # timestamp
		self.o.write(self.payload, timeout=timeout)

def poll_commands(in_ep, out_ep):
	p = Packet(in_ep, out_ep)
	while True:
		if p.recv(0):
			if p.command == 1:
				print('Recv command! %d' % p.command)
				req = UsbRequest(p.payload.decode('utf-8'))
				resp = UsbResponse(p)

				Server.route(req, resp)
			else:
				print('Unknown command! %d' % p.command)
		else:
			print('failed to read!')

def daemon():
	global status
	while True:
		try:
			status = 'disconnected'
			while True:
				dev = usb.core.find(idVendor=0x057E, idProduct=0x3000)

				if dev != None:
					break
				time.sleep(1)

			Print.info('USB Connected')
			status = 'connected'

			dev.reset()
			dev.set_configuration()
			cfg = dev.get_active_configuration()

			is_out_ep = lambda ep: usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT
			is_in_ep = lambda ep: usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN
			out_ep = usb.util.find_descriptor(cfg[(0,0)], custom_match=is_out_ep)
			in_ep = usb.util.find_descriptor(cfg[(0,0)], custom_match=is_in_ep)

			assert out_ep is not None
			assert in_ep is not None

			poll_commands(in_ep, out_ep)
		except BaseException as e:
			print('usb exception: ' + str(e))
		time.sleep(1)