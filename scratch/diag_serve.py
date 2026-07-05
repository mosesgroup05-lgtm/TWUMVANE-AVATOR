import sys
import os

# Add project root to path
sys.path.insert(0, os.getcwd())

from TRSL.backend.app import serve_video, app

with app.app_context():
    video_dir = app.config['VIDEO_DIR']
    filename = 'hello.mp4'
    video_path = os.path.join(video_dir, filename)
    print(f"VIDEO_DIR: {video_dir}")
    print(f"Checking Path: {video_path}")
    print(f"Exists? {os.path.exists(video_path)}")
    
    # Try to serve
    try:
        # Avoid printing emojis to prevent encoding errors
        import flask
        with app.test_request_context():
            response = serve_video(filename)
            print(f"Response Status: {response.status_code}")
    except Exception as e:
        print(f"Error type: {type(e)}")
        print(f"Error: {e}")
