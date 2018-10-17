# This script depends on PyUSB. You can get it with pip install pyusb.
# You will also need libusb installed

# My sincere apologies for this process being overly complicated. Apparently Python and Windows
# aren't very friendly :(
# Windows Instructions:
# 1. Download Zadig from https://zadig.akeo.ie/.
# 2. With your switch plugged in and on the Tinfoil USB install menu, 
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
# 5. Plug in your Switch and go to Tinfoil > Title Management > USB Install NSP
# 6. Run this script
#	  python3 usb_install_pc.py <path/to/nsp_folder>

import usb.core
import usb.util
import struct
import sys
from binascii import hexlify as hx, unhexlify as uhx
from pathlib import Path
import Titles
import Server
import Server.Controller.Api
import Print
import time
from urllib.parse import urlparse
from urllib.parse import parse_qs
import Server.Controller.Api


def getFiles():
	for k, t in Titles.items():
		f = t.getLatestFile()
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
		self.user = None

class Packet:
	def __init__(self, i, o):
		self.size = 0
		self.payload = b''
		self.command = 0
		self.i = i
		self.o = o
		
	def recv(self):
		print('begin recv')
		header = bytes(self.i.read(16, timeout=0))
		print('read complete')
		magic = header[:4]
		self.command = int.from_bytes(header[4:8], byteorder='little')
		self.size = int.from_bytes(header[8:16], byteorder='little')
		
		if magic != b'\x12\x12\x12\x12':
			print('invalid magic! ' + str(magic));
			return False
		
		print('receiving %d bytes' % self.size)
		self.payload = bytes(self.i.read(self.size, timeout=0))
		return True
		
	def send(self):
		print('sending %d bytes' % len(self.payload))
		self.o.write(b'\x12\x12\x12\x12')
		self.o.write(struct.pack('<I', self.command))
		self.o.write(struct.pack('<Q', len(self.payload)))
		self.o.write(self.payload)

def poll_commands(in_ep, out_ep):
	p = Packet(in_ep, out_ep)
	while True:
		if p.recv():
			if p.command == 1:
				req = UsbRequest(p.payload.decode('utf-8'))
				resp = UsbResponse(p)

				Server.route(req, resp)
			elif p.command == 2:
				#req = UsbRequest('/api/download/' + p.payload[8:].decode('utf-8')) #01000320000CC000
				req = UsbRequest('/api/download/0100000000010000')
				resp = UsbResponse(p)

				start = int.from_bytes(p.payload[0:8], byteorder='little')
				size = int.from_bytes(p.payload[8:16], byteorder='little')
				end = start + size
				print('%d - %d' % (start, end))
				Server.Controller.Api.getDownload(req, resp, start, end)
			else:
				print('Unknown command! %d' % p.command)
		else:
			print('failed to read!')

def daemon():
	while True:
		try:
			while True:
				dev = usb.core.find(idVendor=0x057E, idProduct=0x3000)

				if dev != None:
					break
				time.sleep(1)

			Print.info('USB Connected')

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
			print(str(e))
		time.sleep(1)