# TWUMVANE - Rwanda Sign Language Platform

TWUMVANE is a web-based platform for Rwanda Sign Language (RSL) support. It combines a Flask backend with a browser-based frontend to provide:

- a welcome landing page
- a text-to-sign translation experience for the TRSL module
- video upload, management, and playback features
- a simple admin area for managing translation assets

## Project Overview 

This project is designed to help users interact with sign-language content through a web interface. The main application is served from the project root, while the TRSL functionality is organized under the TRSL folder.

## Main Features

- Web app powered by Flask
- Frontend built with HTML, CSS, and JavaScript
- Video upload and playback support
- Translation workflow for text-to-sign content
- Admin page for managing videos and database entries
- Local storage of videos and metadata in the project folders

## Technologies Used

- Python
- Flask
- Flask-CORS
- HTML5 / CSS3 / JavaScript
- JSON for local database storage
- ffmpeg for video processing and concatenation
- Werkzeug for file handling

## Project Structure

```text
AVATOR/
├── app.py                  # Main Flask application entry point
├── run_twumvane.bat       # Windows batch launcher
├── run_twumvane.ps1       # PowerShell launcher
├── templates/             # Welcome page templates
├── TRSL/                  # TRSL module
│   ├── backend/           # Flask backend logic for translation/video handling
│   ├── frontend/          # Web interface for TRSL
│   ├── uploads/           # Uploaded videos
│   ├── videos/            # Stored videos
│   └── video_database.json
└── scratch/               # Experimental or helper scripts
```

## Prerequisites

Before running the project, make sure you have:

- Python 3.8 or newer
- pip installed
- Windows PowerShell or Command Prompt
- ffmpeg installed and available on your PATH

### Install ffmpeg

On Windows, install ffmpeg and make sure the binary is available in your environment.

You can verify it with:

```powershell
ffmpeg -version
```

## First-Time Setup

Open a terminal in the project root and follow these steps.

### 1. Create a virtual environment

```powershell
py -m venv .venv
```

### 2. Activate the virtual environment

In PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 3. Install dependencies

Install the required Python packages:

```powershell
pip install flask flask-cors Werkzeug python-dotenv
```

If you want the TRSL backend dependencies as well, use:

```powershell
pip install -r TRSL\backend\requirements.txt
```

## How to Run the Project

### Option 1: Run directly with Python

From the project root:

```powershell
py app.py
```

Then open your browser at:

- http://localhost:5000/
- http://localhost:5000/trsl/
- http://localhost:5000/trsl/admin

### Option 2: Use the Windows launcher

You can also start the app using the provided scripts:

- Double-click the batch file: run_twumvane.bat
- Or run it from PowerShell: .\run_twumvane.ps1

## Default Application Routes

- / - Welcome page
- /trsl/ - TRSL interface
- /trsl/admin - Admin dashboard
- /trsl/api/translate - Translation endpoint
- /trsl/api/videos - Video listing endpoint

## Notes for First Run

- The application will create folders such as uploads and videos when it starts.
- Video files and database data are stored locally in the TRSL folders.
- If you are missing certain Python packages, install them before launching the server.
- If ffmpeg is not installed, video processing features may fail.

## Troubleshooting

### Import errors

If Python reports missing modules, install them again using pip.

### Server does not start

Check that:

- you are in the correct project folder
- your virtual environment is activated
- ffmpeg is installed
- required packages are installed

### Port already in use

If port 5000 is busy, stop the process using that port and try again.

## Summary

TWUMVANE is a Flask-based web platform for Rwanda Sign Language support with a focus on translation, media handling, and a simple admin experience. With the steps above, you should be able to install, run, and explore the project locally on your machine.
