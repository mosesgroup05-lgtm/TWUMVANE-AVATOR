"""
TWUMVANE - Unified Rwanda Sign Language Platform
Serves both RSL (recognition) and TRSL (text-to-sign) on http://localhost:5000
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS

# ─── Create the main Flask app ───────────────────────────────────────────────
app = Flask(__name__, template_folder='templates')
CORS(app)

# Track module statuses
module_status = {
    'RSL': {'loaded': False, 'error': None},
    'TRSL': {'loaded': False, 'error': None}
}

# ──────────────────────────────────────────────────────────────────────────────
#  Register RSL Blueprint
# ──────────────────────────────────────────────────────────────────────────────
try:
    from RSL.rsl_blueprint import rsl_bp, init_rsl
    app.register_blueprint(rsl_bp, url_prefix='/rsl')
    # Use strict_slashes=False for more flexible URLs
    rsl_bp.strict_slashes = False
    module_status['RSL']['loaded'] = True
    print("[SUCCESS] RSL blueprint registered at /rsl")
except Exception as e:
    module_status['RSL']['error'] = str(e)
    print(f"[ERROR] Could not load RSL blueprint: {e}")

# ──────────────────────────────────────────────────────────────────────────────
#  Register TRSL Blueprint
# ──────────────────────────────────────────────────────────────────────────────
try:
    from TRSL.trsl_blueprint import trsl_bp
    app.register_blueprint(trsl_bp, url_prefix='/trsl')
    # Use strict_slashes=False for more flexible URLs
    trsl_bp.strict_slashes = False
    module_status['TRSL']['loaded'] = True
    print("[SUCCESS] TRSL blueprint registered at /trsl")
except Exception as e:
    module_status['TRSL']['error'] = str(e)
    print(f"[ERROR] Could not load TRSL blueprint: {e}")

# ──────────────────────────────────────────────────────────────────────────────
#  Welcome page
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/')
def welcome():
    """Serve the welcome page with two module cards."""
    return render_template('welcome.html', status=module_status)


# ──────────────────────────────────────────────────────────────────────────────
#  Main entry point
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print()
    print("=" * 65)
    print("  ---  TWUMVANE - Rwanda Sign Language Platform")
    print("=" * 65)
    print()
    print("  Modules:")
    print("    * Welcome page   >>  http://localhost:5000/")
    print("    * RSL  (Recog.)  >>  http://localhost:5000/rsl")
    print("    * TRSL (Text-to-SL) >>  http://localhost:5000/trsl")
    print()

    # Initialise RSL model / mediapipe if successfully loaded
    if module_status['RSL']['loaded']:
        try:
            init_rsl()
            print("  [SUCCESS] RSL Model initialized")
        except Exception as e:
            print(f"  [ERROR] RSL initialization error: {e}")
    else:
        print("  [WARNING] RSL initialization skipped (module not loaded)")

    print("=" * 65)
    print("  [STARTED] Starting server on http://localhost:5000")
    print("=" * 65)
    print()

    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
