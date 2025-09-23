from flask import Flask, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restx import Api, Resource, fields
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

# Initialize Flask-RESTX
api = Api(
    app,
    version='1.0',
    title='Beehive Backend API',
    description='API para monitoramento de honeypots SSH, Telnet e HTTP',
    doc='/docs/',  # Swagger UI will be available at /docs/
    prefix='/api'
)

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

# Flask-RESTX models for documentation
honeypot_model = api.model('Honeypot', {
    'id': fields.Integer(readonly=True, description='ID único do honeypot'),
    'name': fields.String(required=True, description='Nome do honeypot'),
    'type': fields.String(required=True, description='Tipo do honeypot', enum=['ssh', 'telnet', 'http']),
    'host': fields.String(description='Host do honeypot', default='0.0.0.0'),
    'port': fields.Integer(required=True, description='Porta do honeypot'),
    'status': fields.String(description='Status do honeypot', enum=['active', 'inactive'], default='inactive'),
    'created_at': fields.DateTime(readonly=True, description='Data de criação'),
    'logs_count': fields.Integer(readonly=True, description='Número de logs associados')
})

honeypot_input_model = api.model('HoneypotInput', {
    'name': fields.String(required=True, description='Nome do honeypot'),
    'type': fields.String(required=True, description='Tipo do honeypot', enum=['ssh', 'telnet', 'http']),
    'host': fields.String(description='Host do honeypot', default='0.0.0.0'),
    'port': fields.Integer(required=True, description='Porta do honeypot'),
    'status': fields.String(description='Status do honeypot', enum=['active', 'inactive'], default='inactive')
})

log_model = api.model('Log', {
    'id': fields.Integer(readonly=True, description='ID único do log'),
    'honeypot_id': fields.Integer(required=True, description='ID do honeypot associado'),
    'ip_address': fields.String(required=True, description='Endereço IP que gerou o log'),
    'timestamp': fields.DateTime(readonly=True, description='Timestamp do evento'),
    'event_type': fields.String(required=True, description='Tipo do evento'),
    'details': fields.String(description='Detalhes do evento')
})

log_input_model = api.model('LogInput', {
    'honeypot_id': fields.Integer(required=True, description='ID do honeypot associado'),
    'ip_address': fields.String(required=True, description='Endereço IP que gerou o log'),
    'event_type': fields.String(required=True, description='Tipo do evento'),
    'details': fields.String(description='Detalhes do evento')
})

# Namespaces
honeypots_ns = api.namespace('honeypots', description='Operações relacionadas aos honeypots')
logs_ns = api.namespace('logs', description='Operações relacionadas aos logs')
health_ns = api.namespace('health', description='Verificação de saúde da API')

# Add root route after api initialization
@app.route('/')
def index():
    """Redirect to API documentation"""
    return redirect('/docs/')

# Flask-RESTX Resources

@honeypots_ns.route('/')
class HoneypotList(Resource):
    @honeypots_ns.doc('list_honeypots')
    @honeypots_ns.marshal_list_with(honeypot_model)
    def get(self):
        """Lista todos os honeypots"""
        honeypots = Honeypot.query.all()
        return [honeypot.to_dict() for honeypot in honeypots]
    
    @honeypots_ns.doc('create_honeypot')
    @honeypots_ns.expect(honeypot_input_model)
    @honeypots_ns.marshal_with(honeypot_model, code=201)
    def post(self):
        """Cria um novo honeypot"""
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'type', 'port']
        for field in required_fields:
            if field not in data:
                api.abort(400, f'Missing required field: {field}')
        
        # Validate honeypot type
        valid_types = ['ssh', 'telnet', 'http']
        if data['type'] not in valid_types:
            api.abort(400, f'Invalid type. Must be one of: {valid_types}')
        
        try:
            honeypot = Honeypot(
                name=data['name'],
                type=data['type'],
                host=data.get('host', '0.0.0.0'),
                port=data['port'],
                status=data.get('status', 'inactive')
            )
            
            db.session.add(honeypot)
            db.session.commit()
            
            return honeypot.to_dict(), 201
        
        except Exception as e:
            db.session.rollback()
            api.abort(500, f'Error creating honeypot: {str(e)}')

@honeypots_ns.route('/<int:honeypot_id>')
@honeypots_ns.param('honeypot_id', 'ID único do honeypot')
class HoneypotResource(Resource):
    @honeypots_ns.doc('get_honeypot')
    @honeypots_ns.marshal_with(honeypot_model)
    def get(self, honeypot_id):
        """Obtém um honeypot específico"""
        honeypot = Honeypot.query.get_or_404(honeypot_id)
        return honeypot.to_dict()
    
    @honeypots_ns.doc('update_honeypot')
    @honeypots_ns.expect(honeypot_input_model)
    @honeypots_ns.marshal_with(honeypot_model)
    def put(self, honeypot_id):
        """Atualiza um honeypot"""
        honeypot = Honeypot.query.get_or_404(honeypot_id)
        data = request.get_json()
        
        # Validate honeypot type if provided
        if 'type' in data:
            valid_types = ['ssh', 'telnet', 'http']
            if data['type'] not in valid_types:
                api.abort(400, f'Invalid type. Must be one of: {valid_types}')
        
        try:
            # Update fields
            honeypot.name = data.get('name', honeypot.name)
            honeypot.type = data.get('type', honeypot.type)
            honeypot.host = data.get('host', honeypot.host)
            honeypot.port = data.get('port', honeypot.port)
            honeypot.status = data.get('status', honeypot.status)
            
            db.session.commit()
            
            return honeypot.to_dict()
        
        except Exception as e:
            db.session.rollback()
            api.abort(500, f'Error updating honeypot: {str(e)}')
    
    @honeypots_ns.doc('delete_honeypot')
    def delete(self, honeypot_id):
        """Remove um honeypot e todos os seus logs"""
        try:
            honeypot = Honeypot.query.get_or_404(honeypot_id)
            db.session.delete(honeypot)
            db.session.commit()
            
            return {'message': 'Honeypot deleted successfully'}, 200
        
        except Exception as e:
            db.session.rollback()
            api.abort(500, f'Error deleting honeypot: {str(e)}')

@logs_ns.route('/')
class LogList(Resource):
    @logs_ns.doc('list_logs')
    @logs_ns.marshal_list_with(log_model)
    @logs_ns.param('honeypot_id', 'Filtra por ID do honeypot', type='integer', required=False)
    @logs_ns.param('ip_address', 'Filtra por endereço IP', required=False)
    @logs_ns.param('event_type', 'Filtra por tipo de evento', required=False)
    def get(self):
        """Lista todos os logs com filtros opcionais"""
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
        return [log.to_dict() for log in logs]
    
    @logs_ns.doc('create_log')
    @logs_ns.expect(log_input_model)
    @logs_ns.marshal_with(log_model, code=201)
    def post(self):
        """Cria um novo log"""
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['honeypot_id', 'ip_address', 'event_type']
        for field in required_fields:
            if field not in data:
                api.abort(400, f'Missing required field: {field}')
        
        # Validate honeypot exists
        honeypot = Honeypot.query.get(data['honeypot_id'])
        if not honeypot:
            api.abort(404, 'Honeypot not found')
        
        try:
            log = Log(
                honeypot_id=data['honeypot_id'],
                ip_address=data['ip_address'],
                event_type=data['event_type'],
                details=data.get('details', '')
            )
            
            db.session.add(log)
            db.session.commit()
            
            return log.to_dict(), 201
        
        except Exception as e:
            db.session.rollback()
            api.abort(500, f'Error creating log: {str(e)}')

@logs_ns.route('/<int:log_id>')
@logs_ns.param('log_id', 'ID único do log')
class LogResource(Resource):
    @logs_ns.doc('get_log')
    @logs_ns.marshal_with(log_model)
    def get(self, log_id):
        """Obtém um log específico"""
        log = Log.query.get_or_404(log_id)
        return log.to_dict()
    
    @logs_ns.doc('delete_log')
    def delete(self, log_id):
        """Remove um log"""
        try:
            log = Log.query.get_or_404(log_id)
            db.session.delete(log)
            db.session.commit()
            
            return {'message': 'Log deleted successfully'}, 200
        
        except Exception as e:
            db.session.rollback()
            api.abort(500, f'Error deleting log: {str(e)}')

@health_ns.route('/')
class HealthCheck(Resource):
    @health_ns.doc('health_check')
    def get(self):
        """Verifica o estado da API"""
        return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)