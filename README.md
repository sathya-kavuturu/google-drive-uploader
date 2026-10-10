# Google Drive Uploader

A Python script to automatically upload files and folders from a local directory to Google Drive.

## Features

- Authenticates with Google Drive API via OAuth 2.0.
- Interactive menu to select a recent Google Drive folder or create a new one.
- Recursively uploads files and directories from a local `Pending_Uploads` folder.
- Moves successfully uploaded items to a `Completed_Uploads` folder locally to avoid re-uploading.

## Prerequisites

- Python 3.7+
- A Google Cloud Project with the Google Drive API enabled.
- OAuth 2.0 credentials (`credentials.json`) downloaded from your Google Cloud Console and placed in the same directory as the script.

## Installation

1. Clone this repository or download the source code.
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Place the files or folders you want to upload into the `Pending_Uploads` directory (the script will create it if it doesn't exist).
2. Ensure your `credentials.json` file is in the root directory.
3. Run the script:

```bash
python auth.py
```

4. Follow the prompt to authenticate with Google (only required the first time or when the token expires).
5. Choose the destination folder in Google Drive using the interactive menu.
6. The script will upload the files and move them to `Completed_Uploads` upon success.

## Note

- If you modify the scopes in `auth.py`, you need to delete the `token.json` file to force a re-authentication with the new scopes.
