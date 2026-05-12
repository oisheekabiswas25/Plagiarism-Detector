import os
from flask import request
from models import db, AuditLog


def log_audit(action, user_id, ip_address=None, resource=None, details=None):
    """Log user actions for audit trail."""
    if ip_address is None:
        ip_address = request.remote_addr if request else '0.0.0.0'
    
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        ip_address=ip_address,
        details=details or {}
    )
    db.session.add(log)
    db.session.commit()


def get_client_ip():
    """Get client IP address, accounting for proxies."""
    if request.environ.get('HTTP_CF_CONNECTING_IP'):
        return request.environ['HTTP_CF_CONNECTING_IP']
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    return request.remote_addr


def validate_file_upload(file):
    """Validate uploaded file."""
    if not file:
        return False, "No file provided"
    
    if file.filename == '':
        return False, "No file selected"
    
    allowed_extensions = {'.txt', '.md', '.csv', '.pdf', '.docx', '.doc'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        return False, f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
    
    if file.content_length > 5 * 1024 * 1024:  # 5MB limit
        return False, "File size exceeds 5MB limit"
    
    return True, "Valid"
