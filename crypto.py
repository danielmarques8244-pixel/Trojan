import os
import base64
import struct
import hmac
import hashlib

class SecureChannel:
    def __init__(self, key=None):
        self.key = key
    
    def set_key(self, key):
        if isinstance(key, str):
            key = key.encode('utf-8')
        self.key = key
    
    def xor_crypt(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        if not self.key:
            return data
        key_len = len(self.key)
        return bytes([data[i] ^ self.key[i % key_len] for i in range(len(data))])
    
    def encrypt(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        encrypted = self.xor_crypt(data)
        return encrypted
    
    def decrypt(self, data):
        if data is None:
            return None
        try:
            return self.xor_crypt(data)
        except Exception:
            return None
    
    @staticmethod
    def send_key(sock, key):
        if isinstance(key, str):
            key = key.encode('utf-8')
        encoded = base64.b64encode(key)
        packet = struct.pack(">I", len(encoded)) + encoded
        sock.sendall(packet)
    
    @staticmethod
    def recv_key(sock):
        length_data = sock.recv(4)
        if len(length_data) != 4:
            raise ConnectionError("Key length receive failed")
        length = struct.unpack(">I", length_data)[0]
        encoded = b""
        while len(encoded) < length:
            chunk = sock.recv(min(4096, length - len(encoded)))
            if not chunk:
                raise ConnectionError("Connection closed during key exchange")
            encoded += chunk
        return base64.b64decode(encoded)
