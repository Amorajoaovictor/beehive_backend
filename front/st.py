import streamlit as st
import pandas as pd
import requests
from requests.exceptions import RequestException
from datetime import datetime
import os

MOCK_IPS = pd.DataFrame([
    {"IP": "192.168.0.55", "Origem": "Brasil", "Ataque": "SSH Brute Force", "Honeypot": "Honeypot-SSH-01", "Data/Hora": "16/09/2025 14:32"},
    {"IP": "10.10.10.45", "Origem": "EUA", "Ataque": "SQL Injection", "Honeypot": "Honeypot-HTTP-01", "Data/Hora": "16/09/2025 14:35"},
    {"IP": "172.20.5.77", "Origem": "Rússia", "Ataque": "Port Scan", "Honeypot": "Honeypot-DB-01", "Data/Hora": "16/09/2025 14:40"}
])

MOCK_HONEYPOTS = pd.DataFrame([
    {"id": 1, "name": "Honeypot-SSH-01", "type": "ssh", "status": "Online", "host": "0.0.0.0", "port": 22},
    {"id": 2, "name": "Honeypot-HTTP-01", "type": "http", "status": "Offline", "host": "0.0.0.0", "port": 80},
    {"id": 3, "name": "Honeypot-DB-01", "type": "mysql", "status": "Online", "host": "0.0.0.0", "port": 3306}
])

MOCK_LOGS = {
    "Honeypot-SSH-01": [
        "[14:32] Tentativa de login malicioso no IP 192.168.0.55",
        "[14:33] Honeypot SSH respondeu a conexão suspeita"
    ],
    "Honeypot-HTTP-01": [
        "[14:35] IP 10.10.10.45 tentou SQL Injection e foi bloqueado automaticamente"
    ],
    "Honeypot-DB-01": [
        "[14:40] Scanner detectado no IP 172.20.5.77"
    ]
}

# URL base da API (padrão configurável via variável de ambiente)
DEFAULT_API_BASE = os.getenv("API_BASE_URL", "http://localhost:5000/api")

def fetch_honeypots(api_base: str):
    """Tenta obter a lista de honeypots da API. Retorna lista de dicts ou None."""
    try:
        resp = requests.get(f"{api_base}/honeypots", timeout=4)
        resp.raise_for_status()
        return resp.json()
    except RequestException as e:
        st.sidebar.warning(f"Não foi possível buscar honeypots da API: {e}")
        return None


def fetch_logs(api_base: str):
    """Tenta obter os logs da API. Retorna lista de dicts ou None."""
    try:
        resp = requests.get(f"{api_base}/logs", timeout=4)
        resp.raise_for_status()
        return resp.json()
    except RequestException as e:
        st.sidebar.warning(f"Não foi possível buscar logs da API: {e}")
        return None

# ================================
# Layout da Aplicação
# ================================
st.set_page_config(page_title="Painel de Segurança", layout="wide")
st.sidebar.title("📌 Navegação")
menu = st.sidebar.radio("Escolha a seção:", ["Conexoes", "Logs", "Honeypots", "Criar Beehive Node com Honeypot"])
st.sidebar.markdown("---")
# Configuração da API (padrão pode ser alterado via variável de ambiente API_BASE_URL)
api_base = st.sidebar.text_input("API Base URL", value=DEFAULT_API_BASE)
use_api = st.sidebar.checkbox("Usar API (se disponível)", value=True)

# Página: IPs Maliciosos
if menu == "Conexoes":
    st.title("🚨 Conexoes Detectadas")

    honeypots_list = fetch_honeypots(api_base) if use_api else None
    logs_list = fetch_logs(api_base) if use_api else None

    if honeypots_list is not None and logs_list is not None and len(logs_list) > 0:
        hp_df = pd.DataFrame(honeypots_list)
        logs_df = pd.DataFrame(logs_list)

        # Normaliza timestamps
        logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])

        # Mapeia honeypot_id -> nome
        hp_map = {hp['id']: hp.get('name') for hp in honeypots_list}
        logs_df['honeypot_name'] = logs_df['honeypot_id'].map(lambda x: hp_map.get(x, f"Honeypot-{x}"))

        # Agrupa por IP e monta o DataFrame de exibição
        rows = []
        for ip, group in logs_df.groupby('ip_address'):
            attacks = ', '.join(sorted(set(group['event_type'].dropna().astype(str))))
            honeypots_str = ', '.join(sorted(set(group['honeypot_name'].dropna().astype(str))))
            details = '; '.join([d for d in group['details'].astype(str).unique() if d and d.lower() != 'none'])
            last_ts = group['timestamp'].max()
            rows.append({
                'IP': ip,
                'Origem': 'N/D',
                'Ataque': attacks if attacks else (details or 'N/D'),
                'Honeypot': honeypots_str,
                'Data/Hora': last_ts.strftime('%d/%m/%Y %H:%M'),
                'Detalhes': details
            })

        ips_df = pd.DataFrame(rows)
        if ips_df.empty:
            st.info("Nenhum IP registrado nos logs.")
        else:
            st.dataframe(ips_df[['IP', 'Origem', 'Ataque', 'Honeypot', 'Data/Hora']], width='stretch')
    else:
        st.warning("API indisponível ou sem logs — exibindo dados de exemplo (mock).")
        st.dataframe(MOCK_IPS, width='stretch')

# Página: Logs por Honeypot (GRID com 2 por linha)
elif menu == "Logs":
    st.title("📜 Logs de Atividade por Honeypot")

    honeypots_list = fetch_honeypots(api_base) if use_api else None
    logs_list = fetch_logs(api_base) if use_api else None

    if honeypots_list is not None and logs_list is not None:
        hp_map = {hp['id']: hp.get('name') for hp in honeypots_list}
        hp_logs = {}
        for log in logs_list:
            hp_name = hp_map.get(log['honeypot_id'], f"Honeypot-{log['honeypot_id']}")
            t = pd.to_datetime(log['timestamp'])
            details = (log.get('details') or '').strip()
            entry = f"[{t.strftime('%H:%M')}] {details or log.get('event_type')}"
            hp_logs.setdefault(hp_name, []).append(entry)
        hp_items = list(hp_logs.items())
    else:
        hp_items = list(MOCK_LOGS.items())

    cols_per_row = 2

    for i in range(0, len(hp_items), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(hp_items):
                honeypot_name, entries = hp_items[idx]
                with col:
                    st.subheader(f"🔹 {honeypot_name} ({len(entries)} eventos)")
                    processed_lines = []
                    for line in entries:
                        l = line
                        low = line.lower()
                        if "sql" in low or "injection" in low:
                            l = l.replace("SQL Injection", "SQL Injection 🚨").replace("bloqueado", "bloqueado 🔒")
                        elif "brute force" in low or "login malicioso" in low or "login" in low:
                            l = l + " ⚠️"
                        elif "scanner" in low or "port scan" in low or "scan" in low:
                            l = l + " 🔍"
                        processed_lines.append(l)
                    log_text = "  ".join(processed_lines) if len(processed_lines) == 1 else "\n".join(processed_lines)
                    st.code(log_text, language="bash")
                    st.write("")

# Página: Honeypots
elif menu == "Honeypots":
    st.title("🛡️ Gerenciamento de Honeypots")

    honeypots_list = fetch_honeypots(api_base) if use_api else None
    if honeypots_list is not None:
        hp_df = pd.DataFrame(honeypots_list)
        if 'created_at' in hp_df.columns:
            hp_df['created_at'] = pd.to_datetime(hp_df['created_at']).dt.strftime('%d/%m/%Y %H:%M')
        display_cols = [c for c in ['id', 'name', 'type', 'host', 'port', 'status', 'created_at'] if c in hp_df.columns]
        st.dataframe(hp_df[display_cols], width='stretch')
    else:
        st.warning("API indisponível — exibindo honeypots de exemplo (mock).")
        st.dataframe(MOCK_HONEYPOTS, width='stretch')

# Página: Criar VM com Honeypot
elif menu == "Criar Beehive Node com Honeypot":
    st.title("🆕 Criar Nova Beehive Node com Honeypot")
    if "new_vm" not in st.session_state:
        st.session_state.new_vm = False
    if not st.session_state.new_vm:
        if st.button("Criar Nova Beehive Node com Honeypot"):
            st.session_state.new_vm = True
    if st.session_state.new_vm:
        tipo_honeypot = st.selectbox("Selecione o tipo de Honeypot", ["SSH", "HTTP", "Telnet"])
        nome_vm = st.text_input("Nome da Beehive Node", value=f"{tipo_honeypot}-node")
        default_ports = {"SSH": 22, "HTTP": 80, "Telnet": 23}
        port = st.number_input("Porta", min_value=1, max_value=65535, value=default_ports.get(tipo_honeypot, 22))
        if st.button("Confirmar Criação"):
            payload = {"name": nome_vm, "type": tipo_honeypot.lower(), "port": int(port)}
            if use_api:
                try:
                    resp = requests.post(f"{api_base}/honeypots", json=payload, timeout=6)
                    if resp.status_code in (200, 201):
                        created = resp.json()
                        st.success(f"Beehive Node {created.get('name', nome_vm)} com Honeypot {created.get('type', tipo_honeypot.lower())} criada com sucesso!")
                        st.session_state.new_vm = False
                        st.rerun()
                    else:
                        st.error(f"Erro ao criar honeypot: {resp.status_code} - {resp.text}")
                except RequestException as e:
                    st.error(f"Falha ao conectar na API: {e}")
            else:
                st.info("Modo offline: criação simulada.")
                st.success(f"Beehive Node {nome_vm} com Honeypot {tipo_honeypot} (mock) criada!")
                st.session_state.new_vm = False

