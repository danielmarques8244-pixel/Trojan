import os
import base64

class SecureChannel:
    def __init__(self, key=None):
        self.key = key or os.urandom(32)
    
    def set_key(self, key):
        self.key = key.encode() if isinstance(key, str) else key
    
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
            encrypted = base64.b64decode(data)
            decrypted = self.xor_crypt(encrypted)
            return decrypted
        except:
            return None
    
    def encrypt_to_string(self, data):
        return self.encrypt(data).decode('utf-8')
    
    def decrypt_from_string(self, data):
        return self.decrypt(data.encode('utf-8') if isinstance(data, str) else data)
