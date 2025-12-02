# backend/docker_manager.py
import random
import time
import socket
import logging
from typing import Optional

logger = logging.getLogger("beehive.docker_manager")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def check_docker_available(timeout_sec: int = 3) -> bool:
    try:
        client = get_client()
        client.version(timeout=timeout_sec)
        return True
    except Exception:
        return False

# NOTE: use "tcp" protocol consistently
HONEYPOT_CONFIG = {
    "ssh": {
        "image": "cowrie/cowrie:latest",
        "container_port": "2222/tcp",
        "extra_env": {},
    },
    "telnet": {
        "image": "cowrie/cowrie:latest",
        "container_port": "2223/tcp",
        "extra_env": {
            "COWRIE_TELNET_ENABLED": "yes",
        },
    },
    "http": {
        "image": "dinotools/dionaea:latest",
        "container_port": "80/tcp",
        "extra_env": {},
    },
}


def get_client():
    """
    Lazy import and resilient creation of Docker client.
    Tries docker.from_env() and falls back to DockerClient(base_url=unix://...).
    Raises RuntimeError when Docker SDK/daemon unavailable.
    """
    try:
        import docker
    except Exception as e:
        raise RuntimeError(
            "Docker SDK (python package 'docker') não disponível no ambiente. "
            "Instale via 'pip install docker' no virtualenv."
        ) from e

    try:
        return docker.from_env()
    except TypeError as te:
        msg = str(te)
        # known signature mismatch in some environments: try fallback
        if "config_dict" in msg or "unexpected keyword argument" in msg:
            try:
                return docker.DockerClient(base_url="unix://var/run/docker.sock")
            except Exception as e:
                raise RuntimeError(f"Failed to create Docker client via fallback: {e}") from e
        raise
    except Exception as e:
        raise RuntimeError(f"Erro ao conectar ao daemon Docker: {e}") from e


def create_node(node_type: str, requested_port: Optional[int] = None) -> dict:
    """
    Create and start a container for the given honeypot type.
    requested_port: host port (int) or None for random assignment.
    Returns a dict with container metadata.
    """
    if node_type not in HONEYPOT_CONFIG:
        raise ValueError(f"Node type '{node_type}' not supported")

    cfg = HONEYPOT_CONFIG[node_type]
    image = cfg["image"]
    container_port = cfg["container_port"]
    extra_env = cfg.get("extra_env", {})

    name = f"{node_type}-node-{random.randint(1000, 9999)}"

    env = {}
    env.update(extra_env)

    # docker-py accepts port mapping like {"2222/tcp": host_port}
    ports = {container_port: (requested_port if requested_port else None)}

    client = get_client()

    try:
        container = client.containers.run(
            image=image,
            detach=True,
            name=name,
            environment=env,
            ports=ports,
            restart_policy={"Name": "unless-stopped"},
            labels={
                "project": "beehive",
                "node_type": node_type,
            },
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            mem_limit="512m",
            cpu_shares=256,
        )
    except Exception as e:
        logger.error("Failed to run container for %s: %s", node_type, e)
        raise

    host_port = None
    # wait for the host port to appear in the container's NetworkSettings
    for i in range(20):  # ~4s max (20 * 0.2)
        try:
            container.reload()
            ports_info = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            mapping = ports_info.get(container_port)
            if mapping and isinstance(mapping, list) and len(mapping) > 0:
                try:
                    host_port = int(mapping[0].get("HostPort"))
                except Exception:
                    host_port = None
                break
        except Exception as e:
            logger.debug("Waiting for container port mapping: %s", e)
        time.sleep(0.2)

    return {
        "container_id": getattr(container, "id", None),
        "container_name": getattr(container, "name", None),
        "type": node_type,
        "host": "0.0.0.0",
        "port": host_port or requested_port,
        "status": getattr(container, "status", None),
    }


def remove_node(container_id: str, timeout: int = 5) -> bool:
    """
    Stop and remove a container by id. Returns True if removed (or missing), False otherwise.
    """
    try:
        client = get_client()
    except Exception as e:
        logger.error("Docker client not available when trying to remove container: %s", e)
        return False

    try:
        from docker.errors import NotFound
        container = client.containers.get(container_id)
    except NotFound:
        logger.info("Container %s not found (already removed).", container_id)
        return True
    except Exception as e:
        logger.error("Erro ao obter container %s: %s", container_id, e)
        return False

    try:
        try:
            container.stop(timeout=timeout)
        except Exception:
            logger.debug("Falha ao parar container %s; tentando remover direto", container_id)
        container.remove(force=True)
        logger.info("Container %s removido com sucesso.", container_id)
        return True
    except Exception as e:
        logger.error("Erro ao remover container %s: %s", container_id, e)
        return False


def is_port_free(port: int, host: str = "0.0.0.0") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False
