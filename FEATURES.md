# Plagiarism Detector - Enhanced Edition

## 🎯 New Features Added

### 🔐 Security Features
1. **User Authentication System**
   - Secure login/registration with password hashing (PBKDF2)
   - User session management with Flask-Login
   - Remember-me functionality
   - Automatic session timeout

2. **Audit Logging**
   - Track all user actions (login, logout, analyze, download)
   - IP address logging
   - Timestamps for all activities
   - Detailed action records with context

3. **Access Control**
   - Role-based access (student, instructor, admin)
   - Analysis ownership verification
   - Unauthorized access prevention
   - Protected routes

### 💾 Database Backend
1. **SQLAlchemy Database Models**
   - User management with authentication
   - Analysis history storage
   - Audit trail logging
   - Relational data integrity

2. **SQLite Database**
   - File-based database at `plagiarism_detector.db`
   - Automatic table creation on startup
   - Supports full analysis record storage

### 👥 User Experience Improvements
1. **Dark Mode Toggle**
   - Easy theme switching
   - Persistent theme preference (localStorage)
   - Smooth transitions between themes
   - Better readability in both modes

2. **User Dashboard**
   - Professional navbar with user menu
   - Quick access to analysis history
   - User profile page
   - Recent analyses widget

3. **Analysis History**
   - Paginated view of all user analyses
   - Filter by date, score, and model
   - Detailed analysis viewing
   - Analysis metadata storage

4. **Responsive Design**
   - Mobile-friendly interface
   - Tablet optimization
   - Desktop-first approach with mobile enhancements

5. **Enhanced Navigation**
   - Sticky navigation bar
   - Quick profile access
   - Logout functionality
   - Analysis history link

### 📊 Data Management
1. **Analysis Storage**
   - Store full analysis results
   - Track file type and metadata
   - Save plagiarism scores and risk levels
   - Preserve text previews

2. **User Profile Management**
   - Display user information
   - Show registration date
   - Track last login
   - Display analysis statistics

## 📁 New Files Created

### Backend
- `models.py` - Database models (User, Analysis, AuditLog)
- `auth.py` - Authentication blueprint and routes
- `utils.py` - Helper functions (logging, validation)

### Templates
- `base.html` - Base template with navbar and footer
- `login.html` - User login page
- `register.html` - User registration page
- `profile.html` - User profile page
- `history.html` - Analysis history page
- `analysis_detail.html` - Detailed analysis view
- `404.html` - 404 error page
- `500.html` - 500 error page

### Styling
- `static/css/auth.css` - Authentication page styles
- `static/css/base.css` - Base layout and navigation styles

### Scripts
- `static/js/base.js` - Dark mode toggle and alert management

## 🚀 Getting Started

### Installation
```bash
# Install new dependencies
pip install Flask-SQLAlchemy Flask-Login werkzeug

# Run Flask app
python app.py
```

### First Time Setup
1. App automatically creates `plagiarism_detector.db` on first request
2. Navigate to `http://localhost:5000`
3. Register a new account
4. Start analyzing documents

### Default Configuration
- Database: SQLite (`plagiarism_detector.db`)
- Max file size: 5MB
- Session timeout: 7 days
- Supported formats: `.txt`, `.md`, `.csv`, `.pdf`, `.docx`, `.doc`

## 🔄 Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: User email
- `password_hash`: Hashed password
- `role`: User role (student/instructor/admin)
- `created_at`: Registration date
- `last_login`: Last login timestamp
- `is_active`: Account status

### Analyses Table
- `id`: Primary key
- `user_id`: Foreign key to User
- `source_name`: File/document name
- `file_type`: File extension
- `text_preview`: First 500 characters
- `plagiarism_score`: Detected plagiarism percentage
- `risk_level`: Low/Moderate/High Risk
- `model_used`: ML model name
- `results`: Full analysis results (JSON)
- `created_at`: Analysis timestamp

### AuditLog Table
- `id`: Primary key
- `user_id`: Foreign key to User
- `action`: Action type (login, analyze, etc.)
- `resource`: Affected resource
- `ip_address`: Client IP
- `details`: Additional context (JSON)
- `timestamp`: When action occurred

## 🔐 Security Best Practices

1. **Change Secret Key in Production**
   ```python
   app.config['SECRET_KEY'] = 'your-secret-key-here'
   ```

2. **Enable HTTPS**
   - Use SSL certificates in production
   - Update Flask configuration

3. **Database Backups**
   - Regularly backup `plagiarism_detector.db`
   - Implement automated backup schedule

4. **User Password Policy**
   - Minimum 6 characters
   - Consider enforcing complexity rules

## 📊 Features Summary

| Feature | Status | Details |
|---------|--------|---------|
| User Authentication | ✅ Complete | Login, register, logout |
| Database Storage | ✅ Complete | SQLite with Models |
| Analysis History | ✅ Complete | Paginated view |
| Audit Logging | ✅ Complete | All user actions |
| Dark Mode | ✅ Complete | Persistent preference |
| File Upload | ✅ Complete | .pdf, .docx, .doc, .txt, .csv, .md |
| User Profile | ✅ Complete | Personal dashboard |
| Security | ✅ Complete | Password hashing, access control |

## 🎨 UI/UX Features

- **Gradient Design**: Modern purple gradient theme
- **Dark Mode**: Eye-friendly dark theme option
- **Responsive Layout**: Works on all device sizes
- **Smooth Animations**: Subtle transitions and effects
- **Intuitive Navigation**: Clear menu structure
- **Status Badges**: Risk level color coding
- **Error Handling**: Detailed error pages

## 🔜 Future Enhancements

Potential features to add:
- Batch document analysis
- Export results as PDF
- Custom corpus management
- API key authentication
- Advanced statistics dashboard
- Email notifications
- Document comparison
- Plagiarism trend analytics

## 📝 Notes

- All passwords are hashed using PBKDF2:SHA256
- Session data stored in Flask session (can upgrade to Redis)
- IP addresses are stored for audit purposes
- Analysis results are preserved in JSON format
- User data is permanently stored on logout (secure)

## 🆘 Troubleshooting

### Database Issues
```bash
# Reset database
rm plagiarism_detector.db
# Restart app to recreate
```

### Login Issues
- Clear browser cache/cookies
- Check that user exists in database
- Verify password is correct

### File Upload Errors
- Check file size (max 5MB)
- Verify file format is supported
- Ensure file is readable

## 📧 Support

For issues or questions, please refer to the main README.md or contact the development team.
