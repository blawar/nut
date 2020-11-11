from Crypto.Util import Counter
from Crypto.Cipher import AES
from binascii import hexlify
from nut import Keys

import binascii, sys, random, asn1
from fractions import gcd

def extended_gcd(aa, bb):
    lastremainder, remainder = abs(aa), abs(bb)
    x, lastx, y, lasty = 0, 1, 1, 0
    while remainder:
        lastremainder, (quotient, remainder) = remainder, divmod(lastremainder, remainder)
        x, lastx = lastx - quotient*x, x
        y, lasty = lasty - quotient*y, y
    return lastremainder, lastx * (-1 if aa < 0 else 1), lasty * (-1 if bb < 0 else 1)

def modinv(a, m):
    g, x, _ = extended_gcd(a, m)
    if g != 1:
        raise ValueError
    return x % m

def get_primes(D, N, E = 0x10001):
    '''Computes P, Q given E,D where pow(pow(X, D, N), E, N) == X'''
    assert(pow(pow(0xCAFEBABE, D, N), E, N) == 0xCAFEBABE) # Check privk validity
    # code taken from https://stackoverflow.com/a/28299742
    k = E*D - 1
    if k & 1:
        raise ValueError('Could not compute factors. Is private exponent incorrect?')
    t = 0
    while not k & 1:
        k >>= 1
        t += 1
    r = k
    while True:
        g = random.randint(0, N)
        y = pow(g, r, N)
        if y == 1 or y == N - 1:
            continue
        for _ in range(1, t):
            x = pow(y, 2, N)
            if x == 1 or x == N - 1:
                break
            y = x
        if x == 1:
            break
        elif x == N - 1:
            continue
        x = pow(y, 2, N)
        if x == 1:
            break
    p = gcd(y - 1, N)
    q = N // p
    assert N % p == 0
    if p < q:
        p, q = q, p
    return (p, q)

def get_pubk(clcert):
    clcert_decoder = asn1.Decoder()
    clcert_decoder.start(clcert)
    clcert_decoder.enter() # Seq, 3 elem
    clcert_decoder.enter() # Seq, 8 elem
    clcert_decoder.read() 
    clcert_decoder.read()
    clcert_decoder.read()
    clcert_decoder.read()
    clcert_decoder.read()
    clcert_decoder.read()
    clcert_decoder.enter()
    clcert_decoder.enter()
    _, v = clcert_decoder.read()
    assert(v == '1.2.840.113549.1.1.1') # rsaEncryption(PKCS #1)
    clcert_decoder.leave()
    _, v = clcert_decoder.read()
    rsa_decoder = asn1.Decoder()
    rsa_decoder.start(v[1:])
    rsa_decoder.enter()
    _, N = rsa_decoder.read()
    _, E = rsa_decoder.read()
    return (E, N)


def get_priv_key_der(clcert, privk):
    '''Script to create switch der from raw private exponent.'''

    if len(privk) != 0x100:
        print('Error: Private key is not 0x100 bytes...')
        sys.exit(1)

    E, N = get_pubk(clcert)
    D = int(binascii.hexlify(privk), 0x10)

    if pow(pow(0xDEADCAFE, E, N), D, N) != 0xDEADCAFE:
        print('Error: privk does not appear to be inverse of pubk!')
        sys.exit(1)

    P, Q = get_primes(D, N, E)
    dP = D % (P - 1)
    dQ = D % (Q - 1)
    Q_inv = modinv(Q, P)

    enc = asn1.Encoder()
    enc.start()
    enc.enter(0x10)
    enc.write(0)
    enc.write(N)
    enc.write(E)
    enc.write(D)
    enc.write(P)
    enc.write(Q)
    enc.write(dP)
    enc.write(dQ)
    enc.write(Q_inv)
    enc.leave()
    return enc.output()

class Cal0:
  def __init__(self):
    self.serialNumber = None
    self.sslCertificate = None
    self.rsa2048ETicketCertificate = None
    self.extendedRsa2048ETicketKey = None
    self.extendedSslKey = None
    self.deviceId = None

  def readFile(self, filePath):
    try:
      cal0File = open(filePath, 'rb')
      cal0 = cal0File.read()
      if int.from_bytes(cal0[0x0:0x4], byteorder='little', signed=False) == 810303811:
        self.serialNumber = cal0[0x250:0x25E].decode('utf-8')
        sslCertificateSize = int.from_bytes(cal0[0xAD0:0xAD4], byteorder='little', signed=False)
        self.sslCertificate = cal0[0xAE0:0xAE0+sslCertificateSize]
        self.rsa2048ETicketCertificate = cal0[0x2A90:0x2CD0]
        self.deviceId = hexlify(cal0[0x35E0:0x35E8]).decode('utf-8')
        self.extendedRsa2048ETicketKey = cal0[0x3890:0x3AD0]
        ctr = Counter.new(128, initial_value=int(hexlify(cal0[0x3AE0:0x3AF0]), 16))
        dec = AES.new(Keys.getKey('ssl_rsa_kek'), AES.MODE_CTR, counter=ctr).decrypt(cal0[0x3AF0:0x3C10])
        self.extendedSslKey = get_priv_key_der(self.sslCertificate, dec[:0x100])
        return True
      else:
        print('File specified is not a valid CAL0 file')
      cal0File.close()
    except FileNotFoundError:
      print('CAL0 specified not found! Unable to read information')
    return False

  def getCertFile(self):
    return self.deviceId + '.ssl_cert.pem'