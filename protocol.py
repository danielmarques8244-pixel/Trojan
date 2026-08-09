
import struct
import socket

MAX_PAYLOAD = 100 * 1024 * 1024

class ProtocolHandler:
    def __init__(self, crypto=None):
        self.crypto = crypto
    
    def send(self, sock, payload):
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        if payload.startswith(b'[FILE]'):
            msg_type = b'F'
            payload = payload[6:]
        elif payload.startswith(b'[SCREENSHOT]'):
            msg_type = b'S'
            payload = payload[12:]
        elif payload.startswith(b'[WEBCAM]'):
            msg_type = b'W'
            payload = payload[8:]
        else:
            msg_type = b'T'
        
        if self.crypto:
            payload = self.crypto.encrypt(payload)
        
        frame = msg_type + struct.pack(">I", len(payload)) + payload
        sock.sendall(frame)
    
    def recv_exact(self, sock, size):
        data = b""
        while len(data) < size:
            chunk = sock.recv(min(65536, size - len(data)))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data
    
    def receive(self, sock):
        try:
            msg_type = sock.recv(1)
            if not msg_type:
                return None, None
            
            size_data = self.recv_exact(sock, 4)
            size = struct.unpack(">I", size_data)[0]
            
            if size > MAX_PAYLOAD:
                return None, None
            
            payload = self.recv_exact(sock, size)
            
            if self.crypto:
                payload = self.crypto.decrypt(payload)
                if payload is None:
                    return None, None
            
            type_map = {b'F': 'file', b'S': 'screenshot', b'W': 'webcam', b'T': 'text'}
            return type_map.get(msg_type, 'unknown'), payload
            
        except (ConnectionError, struct.error, socket.error):
            return None, None
