from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///beehive.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)

# Models
class Honeypot(db.Model):
    __tablename__ = 'honeypots'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # ssh, telnet, http
    host = db.Column(db.String(50), nullable=False, default='0.0.0.0')
    port = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='inactive')  # active, inactive
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship to logs
    logs = db.relationship('Log', backref='honeypot', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'host': self.host,
            'port': self.port,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'logs_count': len(self.logs)
        }

class Log(db.Model):
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True)
    honeypot_id = db.Column(db.Integer, db.ForeignKey('honeypots.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # Support both IPv4 and IPv6
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)  # connection_attempt, login_attempt, command_executed, etc.
    details = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'honeypot_id': self.honeypot_id,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'details': self.details
        }

# Routes for Honeypots
@app.route('/api/honeypots', methods=['GET'])
def get_honeypots():
    """Get all honeypots"""
    honeypots = Honeypot.query.all()
    return jsonify([honeypot.to_dict() for honeypot in honeypots])

@app.route('/api/honeypots', methods=['POST'])
def create_honeypot():
    """Create a new honeypot"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'type', 'port']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate honeypot type
        valid_types = ['ssh', 'telnet', 'http']
        if data['type'] not in valid_types:
            return jsonify({'error': f'Invalid type. Must be one of: {valid_types}'}), 400
        
        honeypot = Honeypot(
            name=data['name'],
            type=data['type'],
            host=data.get('host', '0.0.0.0'),
            port=data['port'],
            status=data.get('status', 'inactive')
        )
        
        db.session.add(honeypot)
        db.session.commit()
        
        return jsonify(honeypot.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/honeypots/<int:honeypot_id>', methods=['GET'])
def get_honeypot(honeypot_id):
    """Get a specific honeypot"""
    honeypot = Honeypot.query.get_or_404(honeypot_id)
    return jsonify(honeypot.to_dict())

@app.route('/api/honeypots/<int:honeypot_id>', methods=['PUT'])
def update_honeypot(honeypot_id):
    """Update a honeypot"""
    try:
        honeypot = Honeypot.query.get_or_404(honeypot_id)
        data = request.get_json()
        
        # Validate honeypot type if provided
        if 'type' in data:
            valid_types = ['ssh', 'telnet', 'http']
            if data['type'] not in valid_types:
                return jsonify({'error': f'Invalid type. Must be one of: {valid_types}'}), 400
        
        # Update fields
        honeypot.name = data.get('name', honeypot.name)
        honeypot.type = data.get('type', honeypot.type)
        honeypot.host = data.get('host', honeypot.host)
        honeypot.port = data.get('port', honeypot.port)
        honeypot.status = data.get('status', honeypot.status)
        
        db.session.commit()
        
        return jsonify(honeypot.to_dict())
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/honeypots/<int:honeypot_id>', methods=['DELETE'])
def delete_honeypot(honeypot_id):
    """Delete a honeypot"""
    try:
        honeypot = Honeypot.query.get_or_404(honeypot_id)
        db.session.delete(honeypot)
        db.session.commit()
        
        return jsonify({'message': 'Honeypot deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Routes for Logs
@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get all logs with optional filtering"""
    honeypot_id = request.args.get('honeypot_id', type=int)
    ip_address = request.args.get('ip_address')
    event_type = request.args.get('event_type')
    
    query = Log.query
    
    if honeypot_id:
        query = query.filter(Log.honeypot_id == honeypot_id)
    if ip_address:
        query = query.filter(Log.ip_address == ip_address)
    if event_type:
        query = query.filter(Log.event_type == event_type)
    
    logs = query.order_by(Log.timestamp.desc()).all()
    return jsonify([log.to_dict() for log in logs])

@app.route('/api/logs', methods=['POST'])
def create_log():
    """Create a new log entry"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['honeypot_id', 'ip_address', 'event_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate honeypot exists
        honeypot = Honeypot.query.get(data['honeypot_id'])
        if not honeypot:
            return jsonify({'error': 'Honeypot not found'}), 404
        
        log = Log(
            honeypot_id=data['honeypot_id'],
            ip_address=data['ip_address'],
            event_type=data['event_type'],
            details=data.get('details', '')
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify(log.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/<int:log_id>', methods=['GET'])
def get_log(log_id):
    """Get a specific log"""
    log = Log.query.get_or_404(log_id)
    return jsonify(log.to_dict())

@app.route('/api/logs/<int:log_id>', methods=['DELETE'])
def delete_log(log_id):
    """Delete a log entry"""
    try:
        log = Log.query.get_or_404(log_id)
        db.session.delete(log)
        db.session.commit()
        
        return jsonify({'message': 'Log deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)