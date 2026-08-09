import os
import base64
import struct

class SecureChannel:
    def __init__(self, key=None):
        self.key = key or os.urandom(32)
    
    def set_key(self, key):
        self.key = key if isinstance(key, bytes) else key.encode('utf-8')
    
    def xor_crypt(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        key_len = len(self.key)
        return bytes([data[i] ^ self.key[i % key_len] for i in range(len(data))])
    
    def encrypt(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        encrypted = self.xor_crypt(data)
        return base64.b64encode(encrypted)
    
    def decrypt(self, data):
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            encrypted = base64.b64decode(data)
            return self.xor_crypt(encrypted)
        except Exception:
            return None
    
    @staticmethod
    def send_key(sock, key):
        encoded = base64.b64encode(key)
        packet = struct.pack(">I", len(encoded)) + encoded
        sock.sendall(packet)
    
    @staticmethod
    def recv_key(sock):
        length_bytes = sock.recv(4)
        if len(length_bytes) != 4:
            raise ConnectionError("Key length receive failed")
        length = struct.unpack(">I", length_bytes)[0]
        encoded = b""
        while len(encoded) < length:
            chunk = sock.recv(min(4096, length - len(encoded)))
            if not chunk:
                raise ConnectionError("Connection closed during key exchange")
            encoded += chunk
        return base64.b64decode(encoded)
