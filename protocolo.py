 import struct
import socket
import base64

MAX_PAYLOAD_SIZE = 100 * 1024 * 1024
HEADER_SIZE = 4

class ProtocolHandler:
    def __init__(self, crypto=None):
        self.crypto = crypto
    
    def send(self, sock, payload):
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        elif not isinstance(payload, bytes):
            payload = str(payload).encode('utf-8')
        
        if self.crypto:
            payload = self.crypto.encrypt(payload)
        
        if len(payload) > MAX_PAYLOAD_SIZE:
            raise ValueError("Payload too large")
        
        packet = struct.pack(">I", len(payload)) + payload
        sock.sendall(packet)
    
    def recv_exact(self, sock, expected_size):
        data = b""
        while len(data) < expected_size:
            remaining = expected_size - len(data)
            chunk = sock.recv(min(remaining, 65536))
            if not chunk:
                raise ConnectionResetError()
            data += chunk
        return data
    
    def receive(self, sock):
        try:
            header = self.recv_exact(sock, HEADER_SIZE)
            payload_size = struct.unpack(">I", header)[0]
            
            if payload_size > MAX_PAYLOAD_SIZE:
                return None
            
            payload = self.recv_exact(sock, payload_size)
            
            if self.crypto:
                decrypted = self.crypto.decrypt(payload)
                return decrypted
            
            return payload
            
        except (ConnectionResetError, ConnectionAbortedError, struct.error, socket.error):
            return None
