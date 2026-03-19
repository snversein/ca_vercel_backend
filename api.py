from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import requests

load_dotenv()

# Config from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///taxpilot.db')
JWT_SECRET = os.environ.get('JWT_SECRET', 'taxpilot-secret-key')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-70b-versatile')

# Flask app
app = Flask(__name__, static_folder='public', static_url_path='')
app.config['SECRET_KEY'] = JWT_SECRET
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = JWT_SECRET
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

CORS(app, resources={r"/api/*": {"origins": "*"}})

db = SQLAlchemy(app)

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    pan = db.Column(db.String(10))
    phone = db.Column(db.String(15))
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id, 'email': self.email, 'name': self.name,
            'pan': self.pan, 'phone': self.phone, 'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Folder(db.Model):
    __tablename__ = 'folders'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_shared = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'description': self.description,
            'owner_id': self.owner_id, 'is_shared': self.is_shared,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50), default='general')
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'document_type': self.document_type,
            'file_path': self.file_path, 'file_size': self.file_size,
            'mime_type': self.mime_type, 'folder_id': self.folder_id,
            'owner_id': self.owner_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TaxRecord(db.Model):
    __tablename__ = 'tax_records'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assessment_year = db.Column(db.String(10))
    gross_income = db.Column(db.Float)
    deductions = db.Column(db.Float)
    tax_liability = db.Column(db.Float)
    tax_paid = db.Column(db.Float)
    refund_due = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id, 'assessment_year': self.assessment_year,
            'gross_income': self.gross_income, 'deductions': self.deductions,
            'tax_liability': self.tax_liability, 'tax_paid': self.tax_paid,
            'refund_due': self.refund_due,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Create tables
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@taxpilot.com').first():
        admin = User(email='admin@taxpilot.com', name='Admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

# ===================== ROUTES =====================

# Health
@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'TaxPilot API Running'})

# Auth
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Email, password, and name required'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    user = User(email=data['email'], name=data['name'], pan=data.get('pan'), phone=data.get('phone'), role='user')
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict(),
        'access_token': create_access_token(identity=user.id),
        'refresh_token': create_refresh_token(identity=user.id)
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': create_access_token(identity=user.id),
        'refresh_token': create_refresh_token(identity=user.id)
    }), 200

@app.route('/api/auth/profile')
@jwt_required()
def profile():
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()})

# Folders
@app.route('/api/folders')
@jwt_required()
def get_folders():
    uid = get_jwt_identity()
    folders = Folder.query.filter((Folder.owner_id == uid) | (Folder.is_shared == True)).all()
    return jsonify({'folders': [f.to_dict() for f in folders]})

@app.route('/api/folders', methods=['POST'])
@jwt_required()
def create_folder():
    data = request.get_json()
    folder = Folder(name=data['name'], description=data.get('description', ''), owner_id=get_jwt_identity(), is_shared=data.get('is_shared', True))
    db.session.add(folder)
    db.session.commit()
    return jsonify({'message': 'Folder created', 'folder': folder.to_dict()}), 201

@app.route('/api/folders/<int:id>/documents')
@jwt_required()
def folder_docs(id):
    docs = Document.query.filter_by(folder_id=id, owner_id=get_jwt_identity()).all()
    return jsonify({'documents': [d.to_dict() for d in docs]})

# Documents
@app.route('/api/documents')
@jwt_required()
def get_docs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    docs = Document.query.filter_by(owner_id=get_jwt_identity()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({'documents': [d.to_dict() for d in docs.items], 'total': docs.total, 'pages': docs.pages})

@app.route('/api/documents/upload', methods=['POST'])
@jwt_required()
def upload_doc():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    doc = Document(
        name=secure_filename(file.filename),
        document_type=request.form.get('document_type', 'general'),
        file_size=len(file.read()),
        mime_type=file.content_type or 'application/octet-stream',
        folder_id=request.form.get('folder_id', type=int),
        owner_id=get_jwt_identity()
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify({'message': 'Document uploaded', 'document': doc.to_dict()}), 201

@app.route('/api/documents/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_doc(id):
    doc = Document.query.filter_by(id=id, owner_id=get_jwt_identity()).first_or_404()
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'message': 'Document deleted'})

@app.route('/api/documents/types')
def doc_types():
    return jsonify({'types': ['general', 'form16', 'form26as', 'investment', 'receipt', 'other']})

# Tax
def calc_tax(income, deductions, age='general'):
    taxable = max(0, income - deductions)
    exempt = 500000 if age == 'super_senior' else (300000 if age == 'senior' else 250000)
    taxable = max(0, taxable - exempt)
    if taxable <= 0: return {'taxable_income': taxable, 'tax_before_cess': 0, 'cess': 0, 'total_tax': 0}
    tax = 0
    if taxable <= 500000: tax = taxable * 0.05
    elif taxable <= 1000000: tax = 25000 + (taxable - 500000) * 0.20
    elif taxable <= 1500000: tax = 25000 + 100000 + (taxable - 1000000) * 0.20
    elif taxable <= 2000000: tax = 25000 + 100000 + 100000 + (taxable - 1500000) * 0.30
    else: tax = 25000 + 100000 + 100000 + 150000 + (taxable - 2000000) * 0.30
    return {'taxable_income': taxable, 'tax_before_cess': tax, 'cess': tax * 0.04, 'total_tax': tax * 1.04}

@app.route('/api/tax/calculate', methods=['POST'])
@jwt_required()
def tax_calc():
    d = request.get_json()
    return jsonify({'result': calc_tax(float(d.get('income', 0)), float(d.get('deductions', 0)), d.get('age', 'general'))})

@app.route('/api/tax/slabs')
def tax_slabs():
    return jsonify({'slabs': [
        {'range': '0 - 2,50,000', 'rate': 'NIL'},
        {'range': '2,50,001 - 5,00,000', 'rate': '5%'},
        {'range': '5,00,001 - 10,00,000', 'rate': '20%'},
        {'range': 'Above 10,00,000', 'rate': '30%'}
    ]})

@app.route('/api/tax/suggestions')
def tax_suggestions():
    return jsonify({'suggestions': [
        'Maximize 80C deductions (PPF, ELSS, Life Insurance)',
        'Invest in NPS for 80CCD(1B) extra deduction',
        'Health Insurance premium under 80D',
        'Home loan interest under 80EE',
        'Donations under 80G'
    ]})

# Chatbot
@app.route('/api/chatbot/query', methods=['POST'])
def chatbot():
    data = request.get_json()
    message = data.get('message', '')
    if not message:
        return jsonify({'error': 'Message required'}), 400
    if not GROQ_API_KEY:
        return jsonify({'response': 'Chatbot not configured. Set GROQ_API_KEY.'})
    try:
        resp = requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': GROQ_MODEL, 'messages': [
                {"role": "system", "content": "You are an Indian tax assistant. Help with income tax, ITR filing, Section 80C, 80D, etc."},
                {"role": "user", "content": message}
            ], 'temperature': 0.7}, timeout=30)
        if resp.status_code == 200:
            return jsonify({'response': resp.json()['choices'][0]['message']['content']})
        return jsonify({'response': 'Error from Groq API', 'error': resp.text}), 500
    except Exception as e:
        return jsonify({'response': 'Chatbot unavailable', 'error': str(e)}), 500

@app.route('/api/chatbot/topics')
def chatbot_topics():
    return jsonify({'topics': ['Income Tax Basics', 'ITR Filing', 'Section 80C', 'Section 80D', 'Form 16', 'PAN Card']})

@app.route('/api/chatbot/quick-actions')
def chatbot_actions():
    return jsonify({'actions': [
        {'action': 'Calculate Tax', 'icon': 'calculator'},
        {'action': 'File ITR', 'icon': 'document'},
        {'action': 'View Deductions', 'icon': 'savings'},
        {'action': 'Upload Form 16', 'icon': 'upload'}
    ]})

# Admin Panel (Static files)
@app.route('/admin')
@app.route('/admin/<path:filename>')
def admin_panel(filename='index.html'):
    return send_from_directory('public/admin', filename)

@app.route('/')
def root():
    return send_from_directory('public', 'index.html')

# Vercel handler
app_entry = app
