import struct
import socket

MAX_PAYLOAD_SIZE = 10 * 1024 * 1024

def enviar_mensagem(sock, payload):
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    pacote = struct.pack(">I", len(payload)) + payload
    sock.sendall(pacote)

def receber_bytes_exatos(sock, tamanho_esperado):
    dados_acumulados = b""
    while len(dados_acumulados) < tamanho_esperado:
        bytes_restantes = tamanho_esperado - len(dados_acumulados)
        pacote = sock.recv(bytes_restantes)
        if not pacote:
            raise ConnectionResetError()
        dados_acumulados += pacote
    return dados_acumulados

def receber_mensagem(sock):
    try:
        bytes_do_tamanho = receber_bytes_exatos(sock, 4)
        tamanho_do_payload = struct.unpack(">I", bytes_do_tamanho)[0]
        
        if tamanho_do_payload > MAX_PAYLOAD_SIZE:
            raise ValueError()
            
        return receber_bytes_exatos(sock, tamanho_do_payload)
    except (ConnectionResetError, struct.error, socket.error, ValueError):
        return None
