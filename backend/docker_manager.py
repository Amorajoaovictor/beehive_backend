import random
import time

import docker
from docker.errors import DockerException

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
    """
    Cria um Honeypot Node como container Docker e retorna
    informações úteis (host, porta, container_id, etc.).
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

    ports = {
        container_port: requested_port or None  # None = Docker escolhe porta livre
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
