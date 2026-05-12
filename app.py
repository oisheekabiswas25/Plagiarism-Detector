from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json

from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_login import LoginManager, login_required, current_user

from detector import MODEL_NAMES, PlagiarismDetector, extract_text_from_bytes, normalize_text
from models import db, User, Analysis, AuditLog
from auth import auth_bp
from utils import log_audit, get_client_ip, validate_file_upload

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)

# Configuration
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{BASE_DIR}/plagiarism_detector.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'  # Change this!
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7 days

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Register blueprints
app.register_blueprint(auth_bp)


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


@app.before_request
def before_request():
    """Run before each request."""
    if current_user.is_authenticated:
        current_user.update_last_login()


@lru_cache(maxsize=1)
def get_detector() -> PlagiarismDetector:
    return PlagiarismDetector(BASE_DIR)


@app.route("/")
def index():
    """Home page - redirects to login if not authenticated."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    detector = get_detector()
    # Get user's recent analyses
    recent_analyses = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).limit(5).all()
    
    return render_template(
        "index.html",
        model_choices=detector.available_models(),
        default_model=detector.best_model,
        recent_analyses=recent_analyses,
    )


@app.route("/history")
@login_required
def history():
    """Show analysis history for current user."""
    page = request.args.get('page', 1, type=int)
    analyses = Analysis.query.filter_by(user_id=current_user.id).order_by(
        Analysis.created_at.desc()
    ).paginate(page=page, per_page=10)
    
    return render_template('history.html', analyses=analyses)


@app.route("/analysis/<int:analysis_id>")
@login_required
def view_analysis(analysis_id):
    """View detailed analysis results."""
    analysis = Analysis.query.get_or_404(analysis_id)
    
    # Security: ensure user owns this analysis
    if analysis.user_id != current_user.id:
        log_audit('unauthorized_access', current_user.id, get_client_ip(), f'analysis/{analysis_id}')
        return jsonify({"error": "Unauthorized"}), 403
    
    return render_template('analysis_detail.html', analysis=analysis)


@app.route("/health")
def health():
    detector = get_detector()
    return jsonify(
        {
            "status": "ok",
            "available_models": [item["name"] for item in detector.available_models()],
            "best_model": detector.best_model,
        }
    )


@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    submitted_text = request.form.get("text", "")
    model_name = request.form.get("model", "lr").lower()
    uploaded_file = request.files.get("file")

    source_name = "Pasted text"
    file_type = None
    
    try:
        if uploaded_file and uploaded_file.filename:
            # Validate file
            is_valid, message = validate_file_upload(uploaded_file)
            if not is_valid:
                log_audit('invalid_file_upload', current_user.id, get_client_ip(), uploaded_file.filename)
                return jsonify({"error": message}), 400
            
            source_name = uploaded_file.filename
            file_type = Path(uploaded_file.filename).suffix.lower()
            submitted_text = extract_text_from_bytes(uploaded_file.filename, uploaded_file.read())
    except ValueError as exc:
        log_audit('extraction_error', current_user.id, get_client_ip(), source_name)
        return jsonify({"error": str(exc)}), 400

    clean_text = normalize_text(submitted_text)
    if len(clean_text) < 40:
        return jsonify({"error": "Please paste more text or upload a supported text file."}), 400

    if model_name not in MODEL_NAMES:
        return jsonify({"error": "Invalid model selected."}), 400

    try:
        results = get_detector().analyze_text(clean_text, model_name=model_name)
    except ValueError as exc:
        log_audit('analysis_error', current_user.id, get_client_ip(), source_name)
        return jsonify({"error": str(exc)}), 400

    # Extract score and risk level
    plagiarism_score = results.get('plagiarism_score', 0)
    from detector import risk_label
    risk_level = risk_label(plagiarism_score)
    
    # Store analysis in database
    analysis = Analysis(
        user_id=current_user.id,
        source_name=source_name,
        file_type=file_type,
        text_preview=clean_text[:500],
        plagiarism_score=plagiarism_score,
        risk_level=risk_level,
        model_used=model_name,
        results=results
    )
    db.session.add(analysis)
    db.session.commit()
    
    # Log the analysis action
    log_audit('analysis_performed', current_user.id, get_client_ip(), source_name, {
        'score': plagiarism_score,
        'model': model_name,
        'analysis_id': analysis.id
    })
    
    return jsonify({
        "source_name": source_name,
        "text_preview": clean_text[:350],
        "results": results,
        "analysis_id": analysis.id
    })


@app.route("/api/rating", methods=["POST"])
@login_required
def save_rating():
    """Save user rating for an analysis."""
    data = request.get_json()
    analysis_id = data.get('analysis_id')
    rating = data.get('rating')
    
    if not analysis_id or not rating or rating < 1 or rating > 5:
        return jsonify({"error": "Invalid rating"}), 400
    
    analysis = Analysis.query.get_or_404(analysis_id)
    
    # Security: ensure user owns this analysis
    if analysis.user_id != current_user.id:
        log_audit('unauthorized_rating_access', current_user.id, get_client_ip(), f'analysis/{analysis_id}')
        return jsonify({"error": "Unauthorized"}), 403
    
    analysis.user_rating = rating
    db.session.commit()
    
    log_audit('analysis_rated', current_user.id, get_client_ip(), f'analysis/{analysis_id}', {'rating': rating})
    
    return jsonify({"success": True, "rating": rating})


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return render_template('500.html'), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        get_detector()
    app.run(debug=True)
