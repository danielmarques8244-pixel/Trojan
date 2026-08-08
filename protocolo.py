import struct
import socket

MSG_TEXTO = 1
MSG_IMAGEM = 2
MSG_KEYLOG = 3

def enviar_mensagem(sock, tipo, payload_bytes):
    try:
        header = struct.pack(">II", tipo, len(payload_bytes))
        sock.sendall(header + payload_bytes)
    except socket.error as e:
        raise OSError(f"Falha ao transmitir payload do tipo {tipo}: {e}")

def receber_exato(sock, tamanho):
    dados = b""
    while len(dados) < tamanho:
        try:
            pacote = sock.recv(tamanho - len(dados))
            if not pacote:
                raise ConnectionResetError("Conexão interrompida de forma abrupta pelo par remoto.")
            dados += pacote
        except socket.timeout:
            if len(dados) > 0:
                continue
            raise socket.timeout
    return dados

def ler_mensagem(sock):
    try:
        header = receber_exato(sock, 8)
        tipo, tamanho = struct.unpack(">II", header)
        payload = receber_exato(sock, tamanho)
        return tipo, payload
    except socket.timeout as e:
        raise e
    except (ConnectionResetError, struct.error) as e:
        raise RuntimeError(f"Erro de integridade ou dessincronização no cabeçalho do protocolo: {e}")
