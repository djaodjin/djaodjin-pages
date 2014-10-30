#pylint: disable=invalid-name

from Crypto.Cipher import AES
import base64
from .settings import ENCRYPT_KEY
from Crypto import Random

BS = 16

def pad(string):
    return string + (BS - len(string) % BS) * chr(BS - len(string) % BS)

def unpad(string):
    return string[:-ord(string[len(string)-1:])]

def encode(path):
    if ENCRYPT_KEY:
        path = pad(path)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(ENCRYPT_KEY, AES.MODE_ECB, iv)
        return base64.b64encode(iv + cipher.encrypt(path))
    else:
        return path

def decode(path):
    if ENCRYPT_KEY:
        enc = base64.b64decode(path)
        iv = enc[:16]
        cipher = AES.new(ENCRYPT_KEY, AES.MODE_ECB, iv)
        return unpad(cipher.decrypt(enc[16:]))
    else:
        return path
