import os
import sys
import json
import socket
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

class OAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress server logs for cleaner terminal output
        return

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'code' in params:
            self.server.auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization successful!</h1><p>You can now close this window and return to the terminal.</p></body></html>")
        else:
            self.send_response(400)
            self.end_headers()

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_available_port(start_port=8080):
    port = start_port
    while port < start_port + 20:
        if not is_port_in_use(port):
            return port
        port += 1
    return None

def exchange_code_for_token(client_id, client_secret, redirect_uri, code):
    url = "https://oauth2.googleapis.com/token"
    payload = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
        'access_type': 'offline'
    }
    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data.get('refresh_token')
    except Exception as e:
        print(f"[ERROR] Failed to exchange code for token: {e}")
        if hasattr(e, 'read'):
            print(f"Details: {e.read().decode('utf-8')}")
        return None

def update_env_file(client_id, client_secret, refresh_token):
    env_path = "backend/.env"
    if not os.path.exists(env_path):
        env_path = ".env"
    
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
    keys_to_update = {
        'GOOGLE_DRIVE_CLIENT_ID': client_id,
        'GOOGLE_DRIVE_CLIENT_SECRET': client_secret,
        'GOOGLE_DRIVE_REFRESH_TOKEN': refresh_token
    }
    
    new_lines = []
    updated_keys = set()
    
    for line in lines:
        stripped = line.strip()
        if '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in keys_to_update:
                new_lines.append(f"{key}={keys_to_update[key]}\n")
                updated_keys.add(key)
                continue
        new_lines.append(line)
        
    for key, val in keys_to_update.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")
            
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"[INFO] Successfully updated {env_path} with OAuth2 configuration.")

def main():
    print("=== Google Drive OAuth2 Setup Helper ===")
    print("This helper will obtain a refresh token for your personal Google account.\n")
    
    port = find_available_port(8080)
    if not port:
        print("[ERROR] No available ports found between 8080 and 8100.")
        sys.exit(1)
        
    redirect_uri = f"http://localhost:{port}/"
    if port != 8080:
        print(f"[WARNING] Port 8080 is currently occupied (by a running process like Remark42).")
        print(f"Selecting next available port: {port}")
        print(f"IMPORTANT: You MUST add '{redirect_uri}' as an Authorized redirect URI in your Google Cloud Console first!")
        input("Press Enter once you have added it to proceed...")
    else:
        print(f"Using Redirect URI: {redirect_uri}")
        print(f"Make sure 'Authorized redirect URIs' in Google Cloud Console includes: {redirect_uri}\n")
    
    client_id = input("Enter your OAuth Client ID: ").strip()
    client_secret = input("Enter your OAuth Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("[ERROR] Client ID and Client Secret are required.")
        sys.exit(1)
        
    # Generate Auth URL
    auth_params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/drive.file',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(auth_params)
    
    server = HTTPServer(('127.0.0.1', port), OAuthHandler)
    server.auth_code = None
    
    print("\n1. Opening your browser to authorize access...")
    print(f"If the browser doesn't open automatically, visit this URL:\n{auth_url}\n")
    webbrowser.open(auth_url)
    
    print(f"Waiting for authorization callback on port {port}...")
    while server.auth_code is None:
        server.handle_request()
        
    print("\n2. Code received. Exchanging authorization code for refresh token...")
    refresh_token = exchange_code_for_token(client_id, client_secret, redirect_uri, server.auth_code)
    
    if refresh_token:
        print(f"\nSuccess! Refresh token obtained:\n{refresh_token}\n")
        update_env_file(client_id, client_secret, refresh_token)
    else:
        print("[ERROR] Failed to obtain refresh token. Please check your credentials and try again.")

if __name__ == "__main__":
    main()
