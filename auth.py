import os
import shutil
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate_google_drive():
    """Authenticates the user and returns the Drive API service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            # Set open_browser=False for Termux compatibility. It prints the URL
            # instead of trying to launch a GUI browser.
            creds = flow.run_local_server(port=0, open_browser=False)
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as error:
        print(f"An error occurred during authentication: {error}")
        return None


def create_drive_folder(service, folder_name, parent_folder_id=None):
    """Creates a folder in Google Drive and returns its ID."""
    try:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
            
        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        print(f"Folder '{folder_name}' created with ID: {folder_id}")
        return folder_id
    except HttpError as error:
        print(f"An HTTP error occurred creating the folder: {error}")
        return None
    except Exception as error:
        print(f"An unexpected error occurred creating the folder: {error}")
        return None


def upload_file(service, local_file_path, drive_folder_id=None):
    """Uploads a file to Google Drive using a resumable upload."""
    try:
        file_name = os.path.basename(local_file_path)
        file_metadata = {'name': file_name}
        if drive_folder_id:
            file_metadata['parents'] = [drive_folder_id]

        media = MediaFileUpload(local_file_path, resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        print(f"File '{file_name}' uploaded successfully.")
        return file_id
    except HttpError as error:
        print(f"An HTTP error occurred uploading the file: {error}")
        return None
    except Exception as error:
        print(f"An unexpected error occurred uploading the file: {error}")
        return None


def list_drive_folders(service):
    """Lists the top 10 most recently modified folders in Google Drive."""
    try:
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            orderBy="modifiedTime desc",
            pageSize=10,
            fields="nextPageToken, files(id, name)"
        ).execute()
        items = results.get('files', [])
        return items
    except Exception as error:
        print(f"An error occurred listing folders: {error}")
        return []


def get_target_folder(service):
    """Presents a console menu to the user to select or create a target folder."""
    print("\nFetching recent folders...")
    recent_folders = list_drive_folders(service)
    
    print("\nWhere do you want to upload these files?")
    print("0. Create a new folder")
    
    for i, folder in enumerate(recent_folders, start=1):
        print(f"{i}. {folder['name']}")
        
    while True:
        try:
            choice_str = input("\nEnter the number of your choice: ")
            choice = int(choice_str)
            if choice == 0:
                folder_name = input("Enter the name for the new folder: ")
                return create_drive_folder(service, folder_name)
            elif 1 <= choice <= len(recent_folders):
                return recent_folders[choice - 1]['id']
            else:
                print("Invalid choice. Please enter a valid number from the list.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")


def process_upload(service, local_path, drive_parent_id, completed_base_dir):
    """
    Recursively uploads files and directories to Drive and moves them locally to completed_base_dir.
    """
    item_name = os.path.basename(local_path)
    
    if os.path.isfile(local_path):
        # It's a standalone file
        file_id = upload_file(service, local_path, drive_parent_id)
        if file_id:
            # Move file to Completed_Uploads
            dest_path = os.path.join(completed_base_dir, item_name)
            os.makedirs(completed_base_dir, exist_ok=True)
            try:
                shutil.move(local_path, dest_path)
                print(f"Moved locally: '{item_name}' -> Completed_Uploads")
            except Exception as e:
                print(f"Warning: Could not move file {local_path}: {e}")
                
    elif os.path.isdir(local_path):
        # It's a folder, replicate in Google Drive
        new_drive_folder_id = create_drive_folder(service, item_name, drive_parent_id)
        if new_drive_folder_id:
            new_completed_base = os.path.join(completed_base_dir, item_name)
            os.makedirs(new_completed_base, exist_ok=True)
            
            # Iterate through the directory contents
            for sub_item in os.listdir(local_path):
                sub_item_path = os.path.join(local_path, sub_item)
                process_upload(service, sub_item_path, new_drive_folder_id, new_completed_base)
            
            # Clean up empty local directory
            if not os.listdir(local_path):
                try:
                    os.rmdir(local_path)
                except Exception as e:
                    print(f"Warning: Could not remove empty folder {local_path}: {e}")


def main():
    pending_dir = 'Pending_Uploads'
    completed_dir = 'Completed_Uploads'
    
    # Ensure local directories exist
    os.makedirs(pending_dir, exist_ok=True)
    os.makedirs(completed_dir, exist_ok=True)
    
    items_to_upload = os.listdir(pending_dir)
    
    # Check if there is anything to upload
    if not items_to_upload:
        print("Nothing to upload")
        return
        
    # Authenticate
    service = authenticate_google_drive()
    if not service:
        print("Authentication failed. Exiting.")
        return
        
    # Trigger interactive menu
    target_folder_id = get_target_folder(service)
    if not target_folder_id:
        print("No valid target folder selected. Exiting.")
        return
        
    print(f"\n--- Starting Upload Process ---")
    
    # Process everything in Pending_Uploads
    for item in items_to_upload:
        item_path = os.path.join(pending_dir, item)
        process_upload(service, item_path, target_folder_id, completed_dir)
        
    print("\nUpload process complete! All successfully uploaded items have been moved to 'Completed_Uploads'.")

if __name__ == '__main__':
    main()
