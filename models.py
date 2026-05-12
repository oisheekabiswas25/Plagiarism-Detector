from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication and profile management."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, instructor, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    analyses = db.relationship('Analysis', backref='user', lazy=True, cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'


class Analysis(db.Model):
    """Model for storing plagiarism analysis history."""
    __tablename__ = 'analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    source_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10))  # .txt, .pdf, .docx, etc.
    text_preview = db.Column(db.Text)
    plagiarism_score = db.Column(db.Float)
    risk_level = db.Column(db.String(20))  # Low Risk, Moderate Risk, High Risk
    model_used = db.Column(db.String(20))  # svm, rf, lr, knn
    results = db.Column(db.JSON)  # Store full analysis results
    user_rating = db.Column(db.Integer, default=0)  # Star rating 0-5
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Analysis {self.source_name} - {self.plagiarism_score}%>'


class AuditLog(db.Model):
    """Model for audit logging - track all user actions."""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)  # login, logout, analyze, download, etc.
    resource = db.Column(db.String(255))  # file/analysis identifier
    ip_address = db.Column(db.String(45))
    details = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by user {self.user_id}>'
