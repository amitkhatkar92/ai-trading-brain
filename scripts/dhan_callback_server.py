#!/usr/bin/env python3
"""
Dhan OAuth Callback Server
===========================
Automatically captures authentication token from Dhan redirect.

Setup:
  1. Run this script on VPS: python3 dhan_callback_server.py
  2. Login manually at Dhan login page
  3. Dhan redirects to http://178.18.252.24:8000/?code=ABC123...
  4. Script captures code automatically
  5. Token saved to config/api_tokens.json

No manual copy-paste needed.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import json
import os
from pathlib import Path
from datetime import datetime

# Configuration
TOKEN_FILE = "/root/ai-trading-brain/config/api_tokens.json"
PORT = 8000

class DhanCallbackHandler(BaseHTTPRequestHandler):
    """Handle Dhan OAuth redirect with authorization code."""
    
    def do_GET(self):
        """Process GET request from Dhan redirect."""
        query = parse_qs(urlparse(self.path).query)
        
        # Check if authorization code is present
        if "code" in query:
            code = query["code"][0]
            
            # Save token to file
            try:
                token_data = {
                    "dhan_request_code": code,
                    "captured_at": datetime.now().isoformat(),
                    "status": "pending_exchange"
                }
                
                # Create directory if it doesn't exist
                Path(TOKEN_FILE).parent.mkdir(parents=True, exist_ok=True)
                
                # Write token file atomically
                with open(TOKEN_FILE, "w") as f:
                    json.dump(token_data, f, indent=2)
                
                # Send success response to browser
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                
                html_response = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Dhan Authentication Success</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        .success { color: #28a745; font-size: 24px; }
                        .code { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
                        code { font-family: monospace; color: #d63384; }
                    </style>
                </head>
                <body>
                    <h1>✅ Authentication Successful</h1>
                    <p class="success">Token captured successfully!</p>
                    <div class="code">
                        <p>Code: <code>%s</code></p>
                        <p>Saved to: <code>%s</code></p>
                    </div>
                    <p>You can close this page and return to the trading system.</p>
                    <p style="color: #666; margin-top: 30px; font-size: 12px;">
                        Trading system will now exchange this code for a session token.
                    </p>
                </body>
                </html>
                """ % (code[:20] + "...", TOKEN_FILE)
                
                self.wfile.write(html_response.encode())
                
                # Log to console
                print(f"\n✅ DHAN TOKEN CAPTURED")
                print(f"   Code: {code[:30]}...")
                print(f"   Saved: {TOKEN_FILE}")
                print(f"   Time: {datetime.now().isoformat()}")
                print(f"\n   Next step: Exchange code for session token")
                
            except Exception as e:
                self.send_error(500, f"Failed to save token: {str(e)}")
                print(f"❌ Error saving token: {e}")
        
        elif self.path == "/health":
            # Health check endpoint
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ready"}).encode())
        
        else:
            # Unknown endpoint
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            html_response = """
            <!DOCTYPE html>
            <html>
            <head><title>Dhan Callback Server</title></head>
            <body>
                <h1>Dhan Callback Server</h1>
                <p>Waiting for authentication redirect from Dhan...</p>
                <p style="color: #666; font-size: 12px;">
                    This page should not be accessed directly.
                    <br>
                    Expected redirect: http://178.18.252.24:8000/?code=ABC123...
                </p>
            </body>
            </html>
            """
            self.wfile.write(html_response.encode())
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass  # We handle logging manually above


def main():
    """Start the Dhan callback server."""
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, DhanCallbackHandler)
    
    print("\n" + "="*60)
    print("DHAN OAUTH CALLBACK SERVER")
    print("="*60)
    print(f"\n✓ Server listening on: http://0.0.0.0:{PORT}")
    print(f"✓ Public URL: http://178.18.252.24:{PORT}")
    print(f"✓ Token file: {TOKEN_FILE}")
    print(f"\nStep 1: Login to Dhan at: https://api.dhan.co/")
    print(f"Step 2: Dhan will redirect to: http://178.18.252.24:{PORT}/?code=...")
    print(f"Step 3: This script will capture the code automatically")
    print(f"\nWaiting for Dhan redirect...\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
        httpd.server_close()


if __name__ == "__main__":
    main()
