# Copyright (c) 2014, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
