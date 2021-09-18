# -*- coding: utf-8 -*-
from string import ascii_letters, digits, punctuation

def bufferToHex(buffer, start, count):
	accumulator = ''
	for item in range(count):
		accumulator += f"{buffer[start + item]:02X} "
	return accumulator

def bufferToAscii(buffer, start, count):
	accumulator = ''
	for item in range(count):
		char = chr(buffer[start + item])
		if char in ascii_letters or \
		   char in digits or \
		   char in punctuation or \
		   char == ' ':
			accumulator += char
		else:
			accumulator += '.'
	return accumulator

def dump(data, size=16):
	bytesRead = len(data)
	index = 0
	hexFormat = '{:'+str(size*3)+'}'
	asciiFormat = '{:'+str(size)+'}'

	print()
	while index < bytesRead:

		hex_ = bufferToHex(data, index, size)
		ascii_ = bufferToAscii(data, index, size)

		print(hexFormat.format(hex_), end='')
		print('|', asciiFormat.format(ascii_), '|')

		index += size
		if bytesRead - index < size:
			size = bytesRead - index
