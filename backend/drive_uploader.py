import os
import json
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_drive_service():
    """
    Initializes the Google Drive API service.
    First tries user OAuth2 Refresh Token credentials (recommended for personal accounts to avoid quota issues).
    Otherwise, falls back to service account credentials.
    """
    # Method 1: Client ID / Secret / Refresh Token (Recommended for personal accounts)
    client_id = os.environ.get("GOOGLE_DRIVE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_DRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_DRIVE_REFRESH_TOKEN")
    
    if client_id and client_secret and refresh_token:
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"[ERROR drive_uploader.py] Failed to build service from Refresh Token: {e}")

    # Method 2: Service Account Credentials (fallback / Workspace shared drives)
    creds_json = os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
    if not creds_json:
        # Fallback to standard Google application credentials file path if available
        default_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if default_path and os.path.exists(default_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(default_path)
                scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/drive.file'])
                return build('drive', 'v3', credentials=scoped_credentials)
            except Exception as e:
                print(f"[ERROR drive_uploader.py] Failed to build service from file credentials: {e}")
        return None

    try:
        info = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/drive.file'])
        return build('drive', 'v3', credentials=scoped_credentials)
    except Exception as e:
        print(f"[ERROR drive_uploader.py] Failed to parse GOOGLE_DRIVE_CREDENTIALS JSON: {e}")
        return None

def upload_file_to_drive(file_path: str, mime_type: str = 'application/json') -> str:
    """
    Uploads a file to Google Drive.
    Returns the file ID if successful, otherwise None.
    """
    service = get_drive_service()
    if not service:
        print("[WARNING drive_uploader.py] Google Drive service not initialized. File upload skipped.")
        return None

    file_metadata = {
        'name': os.path.basename(file_path)
    }
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if folder_id:
        file_metadata['parents'] = [folder_id]

    try:
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        file_id = file.get('id')
        print(f"[INFO drive_uploader.py] Successfully uploaded feedback file to Google Drive. File ID: {file_id}")
        return file_id
    except Exception as e:
        print(f"[ERROR drive_uploader.py] Error uploading file to Google Drive: {e}")
        return None
