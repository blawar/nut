from enum import IntEnum

class Fs(IntEnum):
	PFS0 = 0x2
	ROMFS = 0x3
	
class Crypto(IntEnum):
	NONE = 1
	XTS = 2
	CTR = 3
	BKTR = 4
	NCA0 = 0x3041434