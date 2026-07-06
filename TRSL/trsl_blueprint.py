from flask import Blueprint, request, jsonify, send_from_directory, send_file
import os
import sys

# Add TRSL backend directory to path
trsl_backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
if trsl_backend_dir not in sys.path:
    sys.path.insert(0, trsl_backend_dir)

# Import the logic from the TRSL app.py
from TRSL.backend.app import (
    translate_text, serve_concatenated_video, upload_video,
    record_from_camera, serve_video, manage_database,
    get_available_words, get_stats, list_videos, 
    reload_database, export_database, clean_unused_videos, app as trsl_app
)

# Define the blueprint
trsl_bp = Blueprint('trsl', __name__,
                  static_folder='frontend',
                  template_folder='frontend')

# Copy configuration from original app if needed
# (Assuming the original app's settings are enough for the functions to work)

@trsl_bp.route('/')
def index():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend'), 'index.html')

@trsl_bp.route('/admin')
def admin():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend'), 'admin.html')

@trsl_bp.route('/api/translate', methods=['POST'])
def translate():
    return translate_text()

@trsl_bp.route('/api/concatenated-videos/<filename>')
def serve_concat(filename):
    return serve_concatenated_video(filename)

@trsl_bp.route('/api/upload', methods=['POST'])
def upload():
    return upload_video()

@trsl_bp.route('/api/record', methods=['POST'])
def record():
    return record_from_camera()

@trsl_bp.route('/api/videos', methods=['GET'])
def list_vids():
    return list_videos()

@trsl_bp.route('/api/videos/<filename>')
def serve_vid(filename):
    return serve_video(filename)

@trsl_bp.route('/api/database', methods=['GET', 'POST', 'DELETE'])
def database():
    return manage_database()

@trsl_bp.route('/api/stats', methods=['GET'])
def stats():
    return get_stats()

@trsl_bp.route('/api/available-words', methods=['GET'])
def available_words():
    return get_available_words()

@trsl_bp.route('/api/reload', methods=['POST'])
def trsl_reload():
    return reload_database()

@trsl_bp.route('/api/export', methods=['GET'])
def trsl_export():
    return export_database()

@trsl_bp.route('/api/clean-unused', methods=['POST'])
def trsl_clean_unused():
    return clean_unused_videos()

# Static files fallback
@trsl_bp.route('/<path:path>')
def static_files(path):
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend'), path)
