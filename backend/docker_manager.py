import random
import time
import socket
import docker
from docker.errors import DockerException, NotFound
from elasticsearch import logger


def check_docker_available(timeout_sec: int = 3) -> bool:
    try:
        client = docker.from_env(timeout=timeout_sec)
        client.version()
        return True
    except DockerException:
        return False

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
    """Retorna o cliente Docker configurado a partir do ambiente."""
    try:
        return docker.from_env()
    except DockerException as e:
        raise DockerException(f"Docker client not available: {e}")


def create_node(node_type: str, requested_port: int | None = 0) -> dict:
    if node_type not in HONEYPOT_CONFIG:
        raise ValueError(f"Node type '{node_type}' not supported")

    cfg = HONEYPOT_CONFIG[node_type]
    image = cfg["image"]
    container_port = cfg["container_port"]
    extra_env = cfg.get("extra_env", {})

    name = f"{node_type}-node-{random.randint(1000, 9999)}"

    env = {}
    env.update(extra_env)

    ports = {
        container_port: requested_port or None
    }

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
    except DockerException as e:
        raise e

    host_port = None
    for _ in range(10):
        container.reload()
        ports_info = container.attrs.get("NetworkSettings", {}).get("Ports", {})
        mapping = ports_info.get(container_port)
        if mapping:
            host_port = int(mapping[0]["HostPort"])
            break
        time.sleep(0.2)

    return {
        "container_id": container.id,
        "container_name": container.name,
        "type": node_type,
        "host": "0.0.0.0",
        "port": host_port or requested_port,
        "status": container.status,
    }

def remove_node(container_id: str, timeout: int = 5) -> bool:
    """
    Para e remove um container pelo container_id.
    Retorna True se removido com sucesso, False caso contrário.
    Não lança exceções (tratadas internamente).
    """
    try:
        client = docker.from_env()
    except DockerException as e:
        logger.error("Docker client not available when trying to remove container: %s", e)
        return False

    try:
        container = client.containers.get(container_id)
    except NotFound:
        logger.info("Container %s not found (already removed).", container_id)
        return True
    except DockerException as e:
        logger.error("Erro ao obter container %s: %s", container_id, e)
        return False

    try:
        # tentar parar o container graciosamente
        try:
            container.stop(timeout=timeout)
        except Exception:
            # ignora falha ao parar, passaremos a remover
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