import streamlit as st
import pandas as pd
import requests
from requests.exceptions import RequestException
from datetime import datetime
import os

# ================================
# Dados / Integração com API
# ================================
# Fallbacks (mocks) para quando a API não estiver disponível
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
menu = st.sidebar.radio("Escolha a seção:", ["IPs Maliciosos", "Logs", "Honeypots", "Criar VM com Honeypot", "Chat de Criação de VMs"])
st.sidebar.markdown("---")
# Configuração da API (padrão pode ser alterado via variável de ambiente API_BASE_URL)
api_base = st.sidebar.text_input("API Base URL", value=DEFAULT_API_BASE)
use_api = st.sidebar.checkbox("Usar API (se disponível)", value=True)

# Página: IPs Maliciosos
if menu == "IPs Maliciosos":
    st.title("🚨 IPs Maliciosos Detectados")

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
            st.dataframe(ips_df[['IP', 'Origem', 'Ataque', 'Honeypot', 'Data/Hora']], use_container_width=True)
    else:
        st.warning("API indisponível ou sem logs — exibindo dados de exemplo (mock).")
        st.dataframe(MOCK_IPS, use_container_width=True)

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
        # Mostra colunas relevantes (fallback para todas as colunas se alguma não existir)
        display_cols = [c for c in ['id', 'name', 'type', 'host', 'port', 'status', 'created_at'] if c in hp_df.columns]
        st.dataframe(hp_df[display_cols], use_container_width=True)
    else:
        st.warning("API indisponível — exibindo honeypots de exemplo (mock).")
        st.dataframe(MOCK_HONEYPOTS, use_container_width=True)

# Página: Criar VM com Honeypot
elif menu == "Criar VM com Honeypot":
    st.title("🆕 Criar Nova VM com Honeypot")
    if "new_vm" not in st.session_state:
        st.session_state.new_vm = False
    if not st.session_state.new_vm:
        if st.button("Criar Nova VM com Honeypot"):
            st.session_state.new_vm = True
    if st.session_state.new_vm:
        tipo_honeypot = st.selectbox("Selecione o tipo de Honeypot", ["SSH", "HTTP", "Telnet"])
        nome_vm = st.text_input("Nome da VM", value=f"{tipo_honeypot}-vm")
        default_ports = {"SSH": 22, "HTTP": 80, "Telnet": 23}
        port = st.number_input("Porta", min_value=1, max_value=65535, value=default_ports.get(tipo_honeypot, 22))
        if st.button("Confirmar Criação"):
            payload = {"name": nome_vm, "type": tipo_honeypot.lower(), "port": int(port)}
            if use_api:
                try:
                    resp = requests.post(f"{api_base}/honeypots", json=payload, timeout=6)
                    if resp.status_code in (200, 201):
                        created = resp.json()
                        st.success(f"VM {created.get('name', nome_vm)} com Honeypot {created.get('type', tipo_honeypot.lower())} criada com sucesso!")
                        st.session_state.new_vm = False
                        st.experimental_rerun()
                    else:
                        st.error(f"Erro ao criar honeypot: {resp.status_code} - {resp.text}")
                except RequestException as e:
                    st.error(f"Falha ao conectar na API: {e}")
            else:
                st.info("Modo offline: criação simulada.")
                st.success(f"VM {nome_vm} com Honeypot {tipo_honeypot} (mock) criada!")
                st.session_state.new_vm = False

# Página: Chat de Criação de VMs
elif menu == "Chat de Criação de VMs":
    st.title("💬 Chat de Criação de VMs")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    prompt = st.chat_input("Digite sua solicitação...")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        # Checa se a mensagem solicita criação de VM com Honeypot
        lower = prompt.lower()
        if "criar vm" in lower and "honeypot" in lower:
            # Parse simples do tipo pedido
            def _parse_type(text: str):
                t = text.lower()
                if 'ssh' in t:
                    return 'ssh'
                if 'http' in t:
                    return 'http'
                if 'telnet' in t:
                    return 'telnet'
                return None

            tipo = _parse_type(prompt)
            if tipo is None:
                response = "Especifique o tipo de Honeypot (SSH, HTTP ou Telnet)."
                st.chat_message("assistant").write(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            else:
                nome = f"vm-{tipo}-{int(datetime.utcnow().timestamp())}"
                payload = {"name": nome, "type": tipo, "port": 22 if tipo == 'ssh' else (80 if tipo == 'http' else 23)}
                if use_api:
                    try:
                        resp = requests.post(f"{api_base}/honeypots", json=payload, timeout=6)
                        if resp.status_code in (200, 201):
                            created = resp.json()
                            response = f"VM com Honeypot {created.get('type')} criada: {created.get('name')} (id={created.get('id')})."
                        else:
                            response = f"Erro ao criar honeypot: {resp.status_code} - {resp.text}"
                    except RequestException as e:
                        response = f"Falha ao conectar na API para criar honeypot: {e}"
                else:
                    response = f"(mock) VM {nome} com Honeypot {tipo} criada com sucesso (modo offline)."

                st.chat_message("assistant").write(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
        else:
            response = "Por favor, especifique 'Criar VM com Honeypot' e o tipo desejado (ex.: SSH)."
            st.chat_message("assistant").write(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})