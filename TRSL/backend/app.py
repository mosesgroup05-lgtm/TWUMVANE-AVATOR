from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import json
import os
import re
import uuid
import tempfile
import subprocess
from datetime import datetime
from werkzeug.utils import secure_filename
import mimetypes
from pathlib import Path

app = Flask(__name__, static_folder='../frontend', template_folder='../frontend')
CORS(app)

# Dynamic paths relative to this file's parent or the TRSL root
BASE_TRSL_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['VIDEO_DIR'] = os.path.join(BASE_TRSL_DIR, 'videos')
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_TRSL_DIR, 'uploads')
app.config['DATABASE_FILE'] = os.path.join(BASE_TRSL_DIR, 'video_database.json')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', 'ogg'}
app.config['CONCATENATED_VIDEOS'] = os.path.join(BASE_TRSL_DIR, 'concatenated_videos')
app.config['CACHE_DURATION'] = 3600  # 1 hour cache for concatenated videos

# Ensure directories exist
os.makedirs(app.config['VIDEO_DIR'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CONCATENATED_VIDEOS'], exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def load_video_database():
    """Load or create the video database"""
    try:
        with open(app.config['DATABASE_FILE'], 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Create default database structure
        default_db = {
            "words": {},
            "phrases": {},
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        save_database(default_db)
        return default_db

def save_database(db):
    """Save database with proper metadata"""
    # Ensure metadata exists
    if "metadata" not in db:
        db["metadata"] = {}
    
    # Update metadata
    db["metadata"]["last_updated"] = datetime.now().isoformat()
    
    # Ensure required keys exist
    if "words" not in db:
        db["words"] = {}
    if "phrases" not in db:
        db["phrases"] = {}
    
    # Save to file
    with open(app.config['DATABASE_FILE'], 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def find_phrase_match_for_position(words, start_idx, words_db, phrases_db):
    """Find the best phrase match starting from a specific position"""
    n = len(words)
    if start_idx >= n:
        return None
    
    # Get the remaining text from this position
    remaining_words = words[start_idx:]
    remaining_text = ' '.join(remaining_words)
    
    print(f"    Looking for phrases starting at position {start_idx}: '{remaining_text}'")
    
    # Try all possible phrase lengths from longest to shortest
    for phrase_length in range(min(4, n - start_idx), 0, -1):
        phrase_words = words[start_idx:start_idx + phrase_length]
        phrase = ' '.join(phrase_words)
        
        print(f"      Checking phrase '{phrase}' (length {phrase_length})")
        
        # Check if this exact phrase exists in words database (has direct video)
        if phrase in words_db:
            print(f"      ✅ Found direct video for phrase: '{phrase}'")
            return {
                'type': 'direct_phrase',
                'phrase': phrase,
                'words': phrase_words,
                'length': phrase_length,
                'has_direct_video': True
            }
        
        # Check if this phrase exists in phrases database (has components)
        elif phrase in phrases_db:
            components = phrases_db[phrase]
            # Check if all components have videos
            all_components_have_videos = True
            missing_components = []
            for component in components:
                if component not in words_db:
                    all_components_have_videos = False
                    missing_components.append(component)
            
            if all_components_have_videos:
                print(f"      ✅ Found phrase with all components: '{phrase}' -> {components}")
                return {
                    'type': 'phrase_components',
                    'phrase': phrase,
                    'components': components,
                    'length': phrase_length,
                    'has_direct_video': False
                }
            else:
                print(f"      ❌ Phrase '{phrase}' missing components: {missing_components}")
    
    return None

def translate_with_exact_hierarchy(text, words_db, phrases_db):
    """Translate text using exact hierarchical logic"""
    print(f"🔍 Exact hierarchical translation for: '{text}'")
    
    # Split text into words
    words = text.split()
    n = len(words)
    video_sequence = []
    i = 0
    
    while i < n:
        print(f"\n  Processing from position {i}:")
        
        # Special handling for patterns starting with 'a'
        if i == 0 and n >= 4 and words[0] == 'a':
            print(f"  Starting with 'a', checking complete patterns...")
            
            # Check "a nkunda mama cyane" (if we have exactly 4 words)
            if n == 4:
                full_phrase = ' '.join(words)
                if full_phrase in words_db:
                    print(f"  ✅ Found complete phrase: '{full_phrase}'")
                    video_sequence.append({
                        "word": full_phrase,
                        "video_url": f"/api/videos/{words_db[full_phrase]}",
                        "has_video": True,
                        "is_complete_phrase": True
                    })
                    return video_sequence
            
            # Check "a nkunda mama" (positions 0-3 if exists)
            if n >= 3:
                phrase_3 = ' '.join(words[0:3])
                if phrase_3 in words_db:
                    print(f"  ✅ Found phrase: '{phrase_3}'")
                    video_sequence.append({
                        "word": phrase_3,
                        "video_url": f"/api/videos/{words_db[phrase_3]}",
                        "has_video": True
                    })
                    # Check remaining word(s)
                    if n > 3:
                        remaining = ' '.join(words[3:])
                        remaining_seq = translate_with_exact_hierarchy(remaining, words_db, phrases_db)
                        video_sequence.extend(remaining_seq)
                    return video_sequence
            
            # Check "a nkunda" (positions 0-2 if exists)
            if n >= 2:
                phrase_2 = ' '.join(words[0:2])
                if phrase_2 in words_db:
                    print(f"  ✅ Found phrase: '{phrase_2}'")
                    video_sequence.append({
                        "word": phrase_2,
                        "video_url": f"/api/videos/{words_db[phrase_2]}",
                        "has_video": True
                    })
                    # Check remaining words
                    if n > 2:
                        remaining = ' '.join(words[2:])
                        remaining_seq = translate_with_exact_hierarchy(remaining, words_db, phrases_db)
                        video_sequence.extend(remaining_seq)
                    return video_sequence
            
            # Check "a"
            if 'a' in words_db:
                print(f"  ✅ Found single word: 'a'")
                video_sequence.append({
                    "word": 'a',
                    "video_url": f"/api/videos/{words_db['a']}",
                    "has_video": True
                })
                i += 1
                continue
        
        # For non-starting position or other patterns
        best_match = find_phrase_match_for_position(words, i, words_db, phrases_db)
        
        if best_match:
            if best_match['type'] == 'direct_phrase':
                phrase = best_match['phrase']
                print(f"  ✅ Adding direct phrase video: '{phrase}'")
                video_sequence.append({
                    "word": phrase,
                    "video_url": f"/api/videos/{words_db[phrase]}",
                    "has_video": True,
                    "is_phrase": True
                })
                i += best_match['length']
                
            elif best_match['type'] == 'phrase_components':
                components = best_match['components']
                print(f"  ✅ Adding phrase components: {components}")
                for component in components:
                    video_sequence.append({
                        "word": component,
                        "video_url": f"/api/videos/{words_db[component]}",
                        "has_video": True,
                        "is_phrase_component": True
                    })
                i += best_match['length']
        
        else:
            # No phrase found, process single word
            word = words[i]
            print(f"  Processing single word: '{word}'")
            if word in words_db:
                video_sequence.append({
                    "word": word,
                    "video_url": f"/api/videos/{words_db[word]}",
                    "has_video": True
                })
            else:
                video_sequence.append({
                    "word": word,
                    "video_url": None,
                    "has_video": False,
                    "error": f"No video available for '{word}'"
                })
            i += 1
    
    return video_sequence

def concatenate_videos(video_paths, output_filename):
    """Concatenate multiple videos into one using ffmpeg"""
    try:
        if not video_paths:
            return None
        
        # Create a temporary file list for ffmpeg
        list_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        list_filename = list_file.name
        
        # Write all video files to the list
        for video_path in video_paths:
            # Ensure the path is properly escaped for ffmpeg
            abs_path = os.path.abspath(video_path).replace('\\', '/')
            list_file.write(f"file '{abs_path}'\n")
        list_file.close()
        
        # Output file path
        output_path = os.path.join(app.config['CONCATENATED_VIDEOS'], output_filename)
        
        # Use ffmpeg to concatenate videos
        # First, convert all videos to have the same format (if needed)
        temp_files = []
        converted_paths = []
        
        for i, video_path in enumerate(video_paths):
            if not os.path.exists(video_path):
                print(f"❌ Video file not found: {video_path}")
                continue
                
            # Check if video needs conversion (simple check by extension)
            if not video_path.lower().endswith('.mp4'):
                temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                temp_file.close()
                
                # Convert to mp4 with h264 codec
                convert_cmd = [
                    'ffmpeg', '-y', '-i', video_path,
                    '-c:v', 'libx264', '-preset', 'fast',
                    '-c:a', 'aac', '-strict', 'experimental',
                    temp_file.name
                ]
                
                try:
                    subprocess.run(convert_cmd, check=True, capture_output=True, timeout=30)
                    converted_paths.append(temp_file.name)
                    temp_files.append(temp_file.name)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    print(f"⚠️ Failed to convert {video_path}: {e}")
                    # Use original if conversion fails
                    converted_paths.append(video_path)
            else:
                converted_paths.append(video_path)
        
        # Update list file with converted paths
        with open(list_filename, 'w', encoding='utf-8') as f:
            for video_path in converted_paths:
                abs_path = os.path.abspath(video_path).replace('\\', '/')
                f.write(f"file '{abs_path}'\n")
        
        # Concatenate command
        concat_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_filename,
            '-c', 'copy',  # Copy codecs (fast)
            '-movflags', '+faststart',  # Optimize for web playback
            output_path
        ]
        
        print(f"🔗 Concatenating {len(converted_paths)} videos...")
        result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"❌ FFmpeg error: {result.stderr}")
            # Try alternative method with re-encoding
            print("🔄 Trying alternative concatenation method...")
            alt_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_filename,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-c:a', 'aac',
                '-movflags', '+faststart',
                output_path
            ]
            result = subprocess.run(alt_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"❌ Alternative method also failed: {result.stderr}")
                return None
        
        # Clean up temporary files
        try:
            os.unlink(list_filename)
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
        except:
            pass
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Successfully created concatenated video: {output_path} ({file_size} bytes)")
            return output_path
        else:
            print("❌ Concatenated video file not created")
            return None
            
    except Exception as e:
        print(f"❌ Error concatenating videos: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Clean up any temporary files
        for filename in [list_filename] + temp_files:
            try:
                if filename and os.path.exists(filename):
                    os.unlink(filename)
            except:
                pass
        return None

def get_concatenated_video_filename(text, video_sequence):
    """Generate a unique filename for concatenated video"""
    # Create a hash from text and video sequence
    sequence_hash = hash(tuple(item['word'] for item in video_sequence if item['has_video']))
    safe_text = re.sub(r'[^\w\s-]', '', text.lower())
    safe_text = re.sub(r'[-\s]+', '_', safe_text)
    
    # Limit filename length
    if len(safe_text) > 50:
        safe_text = safe_text[:50]
    
    filename = f"concat_{safe_text}_{abs(sequence_hash) % 1000000}.mp4"
    return secure_filename(filename)

@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

@app.route('/admin')
def serve_admin():
    return send_from_directory('../frontend', 'admin.html')

@app.route('/api/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        text = data.get('text', '').strip().lower()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        print(f"\n" + "="*60)
        print(f"🔍 Translating text: '{text}'")
        
        video_db = load_video_database()
        words_db = video_db.get('words', {})
        phrases_db = video_db.get('phrases', {})
        
        print(f"📊 Words in database: {len(words_db)} items")
        print(f"📊 Phrases in database: {len(phrases_db)} items")
        
        # Normalize text
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Check if entire text is a single word in database
        if text in words_db:
            print(f"✅ Found exact match as word: '{text}'")
            video_sequence = [{
                "word": text,
                "video_url": f"/api/videos/{words_db[text]}",
                "has_video": True
            }]
            
            return jsonify({
                "original_text": text,
                "translation_type": "exact_word",
                "video_sequence": video_sequence,
                "concatenated_video_url": f"/api/videos/{words_db[text]}",
                "is_single_video": True,
                "message": f"Found exact word match"
            })
        
        # Use exact hierarchical phrase matching
        video_sequence = translate_with_exact_hierarchy(text, words_db, phrases_db)
        
        # Calculate statistics
        matched = len([v for v in video_sequence if v['has_video']])
        missing = len([v for v in video_sequence if not v['has_video']])
        
        # Check if we can create a concatenated video
        video_paths = []
        for item in video_sequence:
            if item['has_video']:
                filename = item['video_url'].split('/')[-1]
                video_path = os.path.join(app.config['VIDEO_DIR'], filename)
                if os.path.exists(video_path):
                    video_paths.append(video_path)
        
        concatenated_video_url = None
        if len(video_paths) > 1:
            # Generate concatenated video
            output_filename = get_concatenated_video_filename(text, video_sequence)
            output_path = os.path.join(app.config['CONCATENATED_VIDEOS'], output_filename)
            
            # Check if concatenated video already exists
            if not os.path.exists(output_path):
                # Create new concatenated video
                result = concatenate_videos(video_paths, output_filename)
                if result:
                    concatenated_video_url = f"/api/concatenated-videos/{output_filename}"
                    print(f"✅ Created concatenated video: {concatenated_video_url}")
                else:
                    print("⚠️ Could not create concatenated video, using individual videos")
            else:
                concatenated_video_url = f"/api/concatenated-videos/{output_filename}"
                print(f"✅ Using cached concatenated video: {concatenated_video_url}")
        
        print(f"\n📊 Translation Summary:")
        print(f"  Sequence length: {len(video_sequence)} items")
        print(f"  Matched: {matched}")
        print(f"  Missing: {missing}")
        print(f"  Videos for concatenation: {len(video_paths)}")
        print(f"  Concatenated video: {concatenated_video_url}")
        print("="*60)
        
        return jsonify({
            "original_text": text,
            "translation_type": "hierarchical",
            "video_sequence": video_sequence,
            "concatenated_video_url": concatenated_video_url,
            "is_single_video": concatenated_video_url is not None,
            "matched_count": matched,
            "missing_count": missing,
            "message": f"Translated {matched} signs, {missing} missing"
        })
        
    except Exception as e:
        print(f"❌ Translation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Translation error: {str(e)}"}), 500

@app.route('/api/concatenated-videos/<filename>')
def serve_concatenated_video(filename):
    """Serve concatenated video files"""
    try:
        if '..' in filename or filename.startswith('/'):
            return jsonify({"error": "Invalid filename"}), 400
        
        # Remove any URL parameters
        filename = filename.split('?')[0]
        
        video_path = os.path.join(app.config['CONCATENATED_VIDEOS'], filename)
        if not os.path.exists(video_path):
            print(f"❌ Concatenated video not found: {filename}")
            return jsonify({"error": "Concatenated video not found"}), 404
        
        print(f"✅ Serving concatenated video: {filename}")
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(video_path)
        if not mime_type:
            mime_type = 'video/mp4'
        
        # Send file with proper headers for video streaming
        response = send_file(
            video_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=filename
        )
        
        # Set cache headers
        response.headers['Cache-Control'] = f'public, max-age={app.config["CACHE_DURATION"]}'
        response.headers['Accept-Ranges'] = 'bytes'
        
        return response
    
    except Exception as e:
        print(f"❌ Error serving concatenated video {filename}: {str(e)}")
        return jsonify({"error": f"Error serving video: {str(e)}"}), 500

@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Handle video file uploads"""
    print("\n" + "="*60)
    print("📤 UPLOAD ENDPOINT CALLED")
    print("="*60)
    
    try:
        # Debug: Log all incoming data
        print("📋 Request form data:")
        for key, value in request.form.items():
            print(f"  {key}: {value}")
        
        print("📁 Files in request:", list(request.files.keys()))
        
        # Check if file exists
        if 'file' not in request.files and 'video' not in request.files:
            print("❌ No file part in request")
            return jsonify({"error": "No file part"}), 400
        
        # Handle both 'file' and 'video' field names
        file_field = None
        if 'video' in request.files:
            file_field = 'video'
        elif 'file' in request.files:
            file_field = 'file'
        
        if not file_field:
            print("❌ No file field found")
            return jsonify({"error": "No file field found"}), 400
        
        file = request.files[file_field]
        print(f"📄 File received: {file.filename}")
        
        if file.filename == '' or not file:
            print("❌ No selected file")
            return jsonify({"error": "No selected file"}), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            print(f"❌ File type not allowed: {file.filename}")
            return jsonify({"error": f"File type not allowed. Supported: {', '.join(app.config['ALLOWED_EXTENSIONS'])}"}), 400
        
        # Get word/phrase
        word = request.form.get('word', '').lower().strip()
        if not word:
            print("❌ No word provided")
            return jsonify({"error": "Word or phrase is required"}), 400
        
        print(f"📝 Word to add: '{word}'")
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        word_slug = re.sub(r'[^a-z0-9]+', '_', word.lower()).strip('_')
        unique_id = str(uuid.uuid4())[:8]
        original_ext = file.filename.rsplit('.', 1)[-1].lower()
        filename = f"upload_{word_slug}_{timestamp}_{unique_id}.{original_ext}"
        filename = secure_filename(filename)
        
        print(f"💾 Saving as: {filename}")
        
        # Save file
        filepath = os.path.join(app.config['VIDEO_DIR'], filename)
        print(f"📂 Saving to: {filepath}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save the file
        file.save(filepath)
        
        # Verify file was saved
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"✅ File saved successfully: {file_size} bytes")
        else:
            print("❌ File not saved properly")
            return jsonify({"error": "Failed to save file"}), 500
        
        # Load and update database
        video_db = load_video_database()
        print(f"📊 Database loaded. Current words: {len(video_db.get('words', {}))}")
        
        # Add word to database
        video_db['words'][word] = filename
        print(f"➕ Added word '{word}' with filename '{filename}'")
        
        # Handle phrase components if provided
        phrase_words_json = request.form.get('phrase_words', '[]')
        print(f"📋 Phrase words JSON: {phrase_words_json}")
        
        try:
            phrase_words = json.loads(phrase_words_json)
            if phrase_words and len(phrase_words) > 1:
                video_db['phrases'][word] = phrase_words
                print(f"📝 Added phrase '{word}' with components: {phrase_words}")
        except (json.JSONDecodeError, TypeError) as e:
            print(f"⚠️ Could not parse phrase words: {e}")
            # Not an error, just not a phrase
        
        # Save database
        save_database(video_db)
        print("💾 Database saved")
        print("="*60)
        
        return jsonify({
            "success": True,
            "message": "Video uploaded successfully",
            "filename": filename,
            "word": word,
            "file_size": file_size,
            "video_url": f"/api/videos/{filename}"
        })
    
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*60)
        return jsonify({"error": f"Upload error: {str(e)}"}), 500

@app.route('/api/record', methods=['POST'])
def record_from_camera():
    """Handle camera recordings"""
    print("\n" + "="*60)
    print("🎥 RECORD ENDPOINT CALLED")
    print("="*60)
    
    try:
        if 'video' not in request.files:
            print("❌ No video file in request")
            return jsonify({"error": "No video file provided"}), 400
        
        file = request.files['video']
        if file.filename == '' or not file:
            print("❌ No selected file")
            return jsonify({"error": "No selected file"}), 400
        
        word = request.form.get('word', '').lower().strip()
        if not word:
            print("❌ No word provided")
            return jsonify({"error": "Word or phrase is required"}), 400
        
        print(f"📝 Word to add: '{word}'")
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        word_slug = re.sub(r'[^a-z0-9]+', '_', word.lower()).strip('_')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"camera_{word_slug}_{timestamp}_{unique_id}.webm"
        filename = secure_filename(filename)
        
        print(f"💾 Saving as: {filename}")
        
        # Save file
        filepath = os.path.join(app.config['VIDEO_DIR'], filename)
        print(f"📂 Saving to: {filepath}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save the file
        file.save(filepath)
        
        # Verify file was saved
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"✅ File saved successfully: {file_size} bytes")
        else:
            print("❌ File not saved properly")
            return jsonify({"error": "Failed to save file"}), 500
        
        # Load and update database
        video_db = load_video_database()
        
        # Add word to database
        video_db['words'][word] = filename
        print(f"➕ Added word '{word}' with filename '{filename}'")
        
        # Handle phrase components if provided
        phrase_words_json = request.form.get('phrase_words', '[]')
        try:
            phrase_words = json.loads(phrase_words_json)
            if phrase_words and len(phrase_words) > 1:
                video_db['phrases'][word] = phrase_words
                print(f"📝 Added phrase '{word}' with components: {phrase_words}")
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Save database
        save_database(video_db)
        print("💾 Database saved")
        print("="*60)
        
        return jsonify({
            "success": True,
            "message": "Camera recording saved successfully",
            "filename": filename,
            "word": word,
            "file_size": file_size,
            "video_url": f"/api/videos/{filename}"
        })
        
    except Exception as e:
        print(f"❌ Recording error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*60)
        return jsonify({"error": f"Recording error: {str(e)}"}), 500

@app.route('/api/videos/<filename>')
def serve_video(filename):
    """Serve video files"""
    try:
        if '..' in filename or filename.startswith('/'):
            return jsonify({"error": "Invalid filename"}), 400
        
        # Remove any URL parameters
        filename = filename.split('?')[0]
        
        video_path = os.path.join(app.config['VIDEO_DIR'], filename)
        if not os.path.exists(video_path):
            print(f"❌ Video not found: {filename}")
            return jsonify({"error": "Video not found"}), 404
        
        print(f"✅ Serving video: {filename}")
        return send_from_directory(app.config['VIDEO_DIR'], filename)
    
    except Exception as e:
        print(f"❌ Error serving video {filename}: {str(e)}")
        return jsonify({"error": f"Error serving video: {str(e)}"}), 500

@app.route('/api/database', methods=['GET', 'POST', 'DELETE'])
def manage_database():
    """Manage database entries"""
    try:
        if request.method == 'GET':
            video_db = load_video_database()
            return jsonify(video_db)
        
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            action = data.get('action')
            
            if action == 'add_word':
                word = data.get('word')
                filename = data.get('filename')
                
                if not word or not filename:
                    return jsonify({"error": "Missing word or filename"}), 400
                
                video_db = load_video_database()
                video_db['words'][word.lower()] = filename
                save_database(video_db)
                
                return jsonify({
                    "success": True,
                    "message": f"Added word: {word}",
                    "word": word,
                    "filename": filename
                })
            
            elif action == 'add_phrase':
                phrase = data.get('phrase')
                words = data.get('words')
                
                if not phrase or not words:
                    return jsonify({"error": "Missing phrase or words"}), 400
                
                video_db = load_video_database()
                video_db['phrases'][phrase.lower()] = words
                save_database(video_db)
                
                return jsonify({
                    "success": True,
                    "message": f"Added phrase: {phrase}",
                    "phrase": phrase,
                    "words": words
                })
            
            return jsonify({"error": "Invalid action"}), 400
        
        elif request.method == 'DELETE':
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            word = data.get('word')
            
            if not word:
                return jsonify({"error": "No word specified"}), 400
            
            video_db = load_video_database()
            
            if word in video_db.get('words', {}):
                filename = video_db['words'][word]
                del video_db['words'][word]
                
                # Remove from phrases if present
                phrases_to_remove = []
                for phrase, words_list in video_db.get('phrases', {}).items():
                    if word in words_list:
                        phrases_to_remove.append(phrase)
                
                for phrase in phrases_to_remove:
                    del video_db['phrases'][phrase]
                
                save_database(video_db)
                
                return jsonify({
                    "success": True,
                    "message": f"Deleted word: {word}",
                    "deleted_file": filename,
                    "removed_from_phrases": len(phrases_to_remove)
                })
            
            return jsonify({"error": "Word not found"}), 404
    
    except Exception as e:
        print(f"Database error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/api/videos', methods=['GET'])
def list_videos():
    """List all video files in the directory"""
    try:
        videos = []
        if os.path.exists(app.config['VIDEO_DIR']):
            for f in os.listdir(app.config['VIDEO_DIR']):
                path = os.path.join(app.config['VIDEO_DIR'], f)
                if os.path.isfile(path):
                    size = os.path.getsize(path)
                    if size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                    ext = f.split('.')[-1].upper() if '.' in f else 'UNKNOWN'
                    videos.append({
                        "name": f,
                        "size": size_str,
                        "extension": ext,
                        "path": f"/api/videos/{f}"
                    })
        return jsonify({"success": True, "videos": videos})
    except Exception as e:
        print(f"Videos list error: {str(e)}")
        return jsonify({"error": f"Error listing videos: {str(e)}"}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    try:
        video_db = load_video_database()
        video_files = []
        
        # Count video files in directory
        if os.path.exists(app.config['VIDEO_DIR']):
            video_files = [f for f in os.listdir(app.config['VIDEO_DIR']) 
                         if os.path.isfile(os.path.join(app.config['VIDEO_DIR'], f))]
        
        # Count concatenated videos
        concatenated_files = []
        if os.path.exists(app.config['CONCATENATED_VIDEOS']):
            concatenated_files = [f for f in os.listdir(app.config['CONCATENATED_VIDEOS'])
                                if os.path.isfile(os.path.join(app.config['CONCATENATED_VIDEOS'], f))]
        
        # Get used filenames from database
        used_files = set(video_db.get('words', {}).values())
        unused_files = [f for f in video_files if f not in used_files]
        
        return jsonify({
            "success": True,
            "total_words": len(video_db.get('words', {})),
            "total_phrases": len(video_db.get('phrases', {})),
            "total_videos": len(video_files),
            "concatenated_videos": len(concatenated_files),
            "unused_videos": len(unused_files),
            "database_created": video_db.get('metadata', {}).get('created', ''),
            "database_updated": video_db.get('metadata', {}).get('last_updated', '')
        })
    except Exception as e:
        print(f"Stats error: {str(e)}")
        return jsonify({"error": f"Error getting stats: {str(e)}"}), 500

@app.route('/api/available-words', methods=['GET'])
def get_available_words():
    """Get list of available words and phrases"""
    try:
        video_db = load_video_database()
        
        return jsonify({
            "success": True,
            "words": list(video_db.get('words', {}).keys()),
            "phrases": list(video_db.get('phrases', {}).keys()),
            "count": len(video_db.get('words', {})),
            "last_updated": video_db.get('metadata', {}).get('last_updated', datetime.now().isoformat())
        })
    except Exception as e:
        print(f"Available words error: {str(e)}")
        return jsonify({"error": f"Error getting available words: {str(e)}"}), 500

@app.route('/api/reload', methods=['POST'])
def reload_database():
    """Reload database from disk"""
    try:
        load_video_database()
        return jsonify({"success": True, "message": "Database reloaded successfully"})
    except Exception as e:
        return jsonify({"error": f"Error reloading database: {str(e)}"}), 500

@app.route('/api/export', methods=['GET'])
def export_database():
    """Export the database JSON file"""
    try:
        if os.path.exists(app.config['DATABASE_FILE']):
            return send_file(app.config['DATABASE_FILE'], as_attachment=True, download_name='video_database.json')
        return jsonify({"error": "Database file not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Error exporting database: {str(e)}"}), 500

@app.route('/api/clean-unused', methods=['POST'])
def clean_unused_videos():
    """Delete all physical video files that are not referenced in the database"""
    try:
        video_db = load_video_database()
        used_files = set(video_db.get('words', {}).values())
        
        deleted_count = 0
        if os.path.exists(app.config['VIDEO_DIR']):
            for f in os.listdir(app.config['VIDEO_DIR']):
                if f not in used_files:
                    path = os.path.join(app.config['VIDEO_DIR'], f)
                    if os.path.isfile(path):
                        os.unlink(path)
                        deleted_count += 1
                        
        return jsonify({
            "success": True, 
            "message": f"Deleted {deleted_count} unused video files",
            "deleted_count": deleted_count
        })
    except Exception as e:
        return jsonify({"error": f"Error cleaning unused videos: {str(e)}"}), 500

# Serve static files
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(413)
def too_large(error):
    return jsonify({"error": "File too large. Maximum size is 100MB."}), 413

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("RSL (Text to Rwanda Sign Language) Backend")
    print("=" * 60)
    print(f"Video directory: {app.config['VIDEO_DIR']}")
    print(f"Concatenated videos: {app.config['CONCATENATED_VIDEOS']}")
    print(f"Database file: {app.config['DATABASE_FILE']}")
    print(f"Static files: ../frontend")
    print("-" * 60)
    
    # Check if directories exist
    if not os.path.exists(app.config['VIDEO_DIR']):
        print(f"⚠️ Videos directory does not exist: {app.config['VIDEO_DIR']}")
        print(f"📁 Creating videos directory...")
        os.makedirs(app.config['VIDEO_DIR'], exist_ok=True)
    
    if not os.path.exists(app.config['CONCATENATED_VIDEOS']):
        print(f"⚠️ Concatenated videos directory does not exist: {app.config['CONCATENATED_VIDEOS']}")
        print(f"📁 Creating concatenated videos directory...")
        os.makedirs(app.config['CONCATENATED_VIDEOS'], exist_ok=True)
    
    if not os.path.exists(app.config['DATABASE_FILE']):
        print(f"⚠️ Database file does not exist: {app.config['DATABASE_FILE']}")
        print(f"📁 Creating initial database...")
        save_database({
            "words": {},
            "phrases": {},
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
        })
    
    print("✅ Server ready")
    print("-" * 60)
    print("Starting server...")
    print(f"Main application: http://localhost:5000")
    print(f"Admin panel: http://localhost:5000/admin")
    print("=" * 60)
    
    app.run(debug=True, port=5000, host='0.0.0.0')