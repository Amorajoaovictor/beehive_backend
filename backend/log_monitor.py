import threading
import json
import logging
from datetime import datetime
from backend.docker_manager import get_client

from backend.app import app, db, Log

logger = logging.getLogger("beehive.log_monitor")


def parse_and_save_log(line_bytes, honeypot_id):
    line_str = line_bytes.decode('utf-8', errors='ignore').strip()
    if not line_str:
        return

    data = {}
    event_type = "unknown"
    details = line_str
    ip_address = "0.0.0.0"

    # Tenta decodificar JSON (padrao Cowrie)
    try:
        data = json.loads(line_str)
        event_type = data.get("eventid", "generic_event")
        ip_address = data.get("src_ip", "0.0.0.0")
        details = json.dumps(data)  # Salva o JSON completo nos detalhes
    except json.JSONDecodeError:
        # Se nao for JSON (ex: Dionaea raw), salva como texto
        event_type = "raw_output"

    # Criar registro no banco
    # Eh necessario usar app.app_context() pois estamos em uma thread
    with app.app_context():
        try:
            new_log = Log(
                honeypot_id=honeypot_id,
                ip_address=ip_address,
                event_type=event_type,
                details=details,
                timestamp=datetime.utcnow()
            )
            db.session.add(new_log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar log no DB: {e}")
            db.session.rollback()


def _monitor_loop(container_id, honeypot_id):
    """Loop infinito que fica lendo o stream do container."""
    try:
        client = get_client()
        container = client.containers.get(container_id)

        # stream=True e follow=True mantem a conexao aberta recebendo logs em tempo real
        for line in container.logs(stream=True, follow=True, tail=0):
            parse_and_save_log(line, honeypot_id)

    except Exception as e:
        logger.error(f"Monitoramento do container {container_id} parou: {e}")


def attach_log_forwarder(container_id, honeypot_id):
    """Inicia uma thread para monitorar o container especificado."""
    if not container_id:
        return

    t = threading.Thread(
        target=_monitor_loop,
        args=(container_id, honeypot_id),
        daemon=True  # daemon=True mata a thread se o app principal cair
    )
    t.start()
    logger.info(f"Monitor de logs iniciado para container {container_id}")