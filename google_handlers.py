from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import asyncio
import os.path
import pickle
import logging

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/spreadsheets']


def google_api_auth():
    """Authenticate with Google API."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


def upload_file_to_drive(creds, file_obj, file_name, folder_id):
    """Upload a file to Google Drive."""
    try:
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_obj, mimetype='image/png', resumable=True)
        _ = service.files().create(body=file_metadata,
                                   media_body=media, fields='id').execute()
    except Exception as e:
        logging.error(f"Error in upload_file_to_drive: {e}")


def create_sheet_entry(creds, spreadsheet_id, range_name, values):
    """Create an entry in a Google Sheet."""
    try:
        service = build('sheets', 'v4', credentials=creds)
        body = {
            'values': values
        }
        _ = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption='USER_ENTERED', body=body).execute()
    except Exception as e:
        logging.error(f"Error in create_sheet_entry: {e}")


async def async_upload_file_to_drive(creds, file_obj, file_name, folder_id):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, upload_file_to_drive, creds, file_obj, file_name, folder_id)


async def async_create_sheet_entry(creds, spreadsheet_id, range_name, values):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, create_sheet_entry, creds, spreadsheet_id, range_name, values)
