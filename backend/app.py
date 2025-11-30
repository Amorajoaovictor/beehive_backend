import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from docker.errors import DockerException

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

try:
    from docker_manager import create_node, is_port_free, remove_node
except Exception:
    try:
        from backend.docker_manager import create_node, is_port_free, remove_node
    except Exception as e:
        raise ImportError(
            f"Nao foi possivel importar docker_manager: {e}\n"
            "Execute o backend via:\n"
            "    python -m backend.app\n"
            "ou ajuste PYTHONPATH."
        )



default_db = f"sqlite:///{os.path.join(PROJECT_ROOT, 'instance', 'beehive.db')}"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', default_db)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    
    container_id = db.Column(db.String(128), nullable=True)
    container_name = db.Column(db.String(128), nullable=True)
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
        data = request.get_json()
        required_fields = ['name', 'type', 'port']
        for field in required_fields:
            if field not in data:
                api.abort(400, f'Missing required field: {field}')

        valid_types = ['ssh', 'telnet', 'http']
        hp_type = data['type']
        if hp_type not in valid_types:
            api.abort(400, f'Invalid type. Must be one of: {valid_types}')

        host = data.get('host', '0.0.0.0')
        port = data['port']
        status = data.get('status', 'inactive')

        if not is_port_free(port):
            api.abort(409, f"Port {port} already in use on host.")

        # 1) criar o container primeiro
        try:
            node_info = create_node(hp_type, requested_port=port)
            # node_info deve conter: container_id, container_name, host, port, status
        except DockerException as e:
            api.abort(500, f'Error creating honeypot node in Docker: {str(e)}')
        except Exception as e:
            api.abort(500, f'Unexpected error creating honeypot node: {str(e)}')

        container_id = node_info.get('container_id')
        container_name = node_info.get('container_name')
        host = node_info.get('host', host)
        port = node_info.get('port', port)
        status = node_info.get('status', 'active')

        try:
            honeypot = Honeypot(
                name=data['name'],
                type=hp_type,
                host=host,
                port=port,
                status=status,
                container_id=container_id,
                container_name=container_name
            )
            db.session.add(honeypot)
            db.session.commit()
            return honeypot.to_dict(), 201

        except Exception as e:
            # se falhar ao persistir, remover container criado para cleanup
            db.session.rollback()
            removed = False
            try:
                removed = remove_node(container_id)
            except Exception:
                removed = False
            # log opcional: registrar que removemos (ou não) o container
            if removed:
                api.abort(500, f'Error creating honeypot DB entry; container removed. DB error: {str(e)}')
            else:
                api.abort(500, f'Error creating honeypot DB entry; failed to remove container {container_id}. DB error: {str(e)}')



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
        """Remove um honeypot, seu container Docker (se existir) e todos os seus logs"""
        try:
            honeypot = Honeypot.query.get_or_404(honeypot_id)
            container_id = getattr(honeypot, 'container_id', None)

            container_removed = False
            removal_message = ""
            if container_id:
                try:
                    # remove_node deve retornar True/False
                    from .docker_manager import remove_node as _remove_node
                except Exception:
                    # fallback import (robusto)
                    try:
                        from backend.docker_manager import remove_node as _remove_node
                    except Exception:
                        _remove_node = None

                if _remove_node:
                    try:
                        container_removed = _remove_node(container_id)
                        removal_message = "container_removed" if container_removed else "container_not_removed"
                    except Exception as e:
                        container_removed = False
                        removal_message = f"container_remove_error: {str(e)}"
                else:
                    removal_message = "no_remove_node_available"
            else:
                removal_message = "no_container_id"

            # remover o registro do DB (logs em cascade)
            db.session.delete(honeypot)
            db.session.commit()

            return {
                'message': 'Honeypot deleted successfully',
                'container_status': removal_message
            }, 200

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