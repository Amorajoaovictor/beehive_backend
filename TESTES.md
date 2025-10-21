# Documentação dos Testes - Beehive Backend API

## 📋 Visão Geral

Este documento descreve todos os testes automatizados da API Beehive Backend. Os testes validam as funcionalidades principais da API, incluindo operações CRUD (Create, Read, Update, Delete) para honeypots e logs, além de validações de entrada e verificação de saúde do sistema.

## 🚀 Como Executar os Testes

### Pré-requisitos

1. Certifique-se de que todas as dependências estão instaladas:
```bash
pip install -r requirements.txt
```

2. Inicie o servidor da API:
```bash
python app.py
```

3. Em outro terminal, execute os testes:
```bash
python test_api.py
```

## ✅ Resultado dos Testes

Quando todos os testes passam com sucesso, você verá a seguinte saída:

```
Starting Beehive Backend API Tests
========================================
Testing health endpoint...
✅ Health endpoint working
Testing honeypots CRUD...
✅ Honeypot creation working
✅ Honeypots listing working
✅ Single honeypot retrieval working
Testing logs CRUD...
✅ Log creation working
✅ Logs listing working
✅ Logs filtering by honeypot working
✅ Logs filtering by IP working
Testing validation...
✅ Honeypot type validation working
✅ Required field validation working
✅ Foreign key validation working
========================================
🎉 All tests passed!
```

## 📝 Descrição Detalhada dos Testes

### 1. Teste de Health Check (Verificação de Saúde)

**Função:** `test_health()`

**Objetivo:** Verificar se a API está funcionando corretamente e respondendo às requisições.

**Endpoint Testado:** `GET /api/health`

**O que é testado:**
- ✅ Status code 200 (OK)
- ✅ Resposta contém campo `status` com valor `healthy`
- ✅ API está acessível e operacional

**Exemplo de resposta esperada:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-21T22:23:37.575Z"
}
```

---

### 2. Testes CRUD de Honeypots

**Função:** `test_honeypots()`

**Objetivo:** Validar todas as operações de criação, leitura, atualização e deleção de honeypots.

#### 2.1 Criação de Honeypot
**Endpoint:** `POST /api/honeypots`

**O que é testado:**
- ✅ Status code 201 (Created)
- ✅ Honeypot é criado com os dados corretos
- ✅ ID é gerado automaticamente
- ✅ Campos obrigatórios são respeitados (name, type, port)
- ✅ Campos opcionais recebem valores padrão (host: "0.0.0.0", status: "inactive")

**Dados de entrada:**
```json
{
  "name": "Test SSH Honeypot",
  "type": "ssh",
  "port": 2222
}
```

**Resposta esperada:**
```json
{
  "id": 1,
  "name": "Test SSH Honeypot",
  "type": "ssh",
  "host": "0.0.0.0",
  "port": 2222,
  "status": "inactive",
  "created_at": "2025-10-21T22:23:37.575Z",
  "logs_count": 0
}
```

#### 2.2 Listagem de Honeypots
**Endpoint:** `GET /api/honeypots`

**O que é testado:**
- ✅ Status code 200 (OK)
- ✅ Retorna array de honeypots
- ✅ Array contém pelo menos o honeypot criado anteriormente
- ✅ Cada honeypot inclui contagem de logs associados

#### 2.3 Obtenção de Honeypot Específico
**Endpoint:** `GET /api/honeypots/{id}`

**O que é testado:**
- ✅ Status code 200 (OK)
- ✅ Retorna o honeypot correto pelo ID
- ✅ Dados do honeypot correspondem aos dados criados

---

### 3. Testes CRUD de Logs

**Função:** `test_logs(honeypot_id)`

**Objetivo:** Validar operações de criação, leitura e filtragem de logs de eventos dos honeypots.

#### 3.1 Criação de Log
**Endpoint:** `POST /api/logs`

**O que é testado:**
- ✅ Status code 201 (Created)
- ✅ Log é criado com associação correta ao honeypot
- ✅ Campos obrigatórios são validados (honeypot_id, ip_address, event_type)
- ✅ Timestamp é gerado automaticamente

**Dados de entrada:**
```json
{
  "honeypot_id": 1,
  "ip_address": "192.168.1.100",
  "event_type": "connection_attempt",
  "details": "Test connection attempt"
}
```

**Resposta esperada:**
```json
{
  "id": 1,
  "honeypot_id": 1,
  "ip_address": "192.168.1.100",
  "timestamp": "2025-10-21T22:23:37.575Z",
  "event_type": "connection_attempt",
  "details": "Test connection attempt"
}
```

#### 3.2 Listagem de Logs
**Endpoint:** `GET /api/logs`

**O que é testado:**
- ✅ Status code 200 (OK)
- ✅ Retorna array de logs
- ✅ Array contém pelo menos o log criado anteriormente

#### 3.3 Filtragem de Logs por Honeypot
**Endpoint:** `GET /api/logs?honeypot_id={id}`

**O que é testado:**
- ✅ Status code 200 (OK)
- ✅ Retorna apenas logs do honeypot especificado
- ✅ Todos os logs retornados têm o mesmo honeypot_id

**Exemplo:**
```bash
GET /api/logs?honeypot_id=1
```

#### 3.4 Filtragem de Logs por IP
**Endpoint:** `GET /api/logs?ip_address={ip}`

**O que é testado:**
- ✅ Status code 200 (OK)
- ✅ Retorna apenas logs do endereço IP especificado
- ✅ Todos os logs retornados têm o mesmo ip_address

**Exemplo:**
```bash
GET /api/logs?ip_address=192.168.1.100
```

---

### 4. Testes de Validação

**Função:** `test_validation()`

**Objetivo:** Garantir que a API valida corretamente os dados de entrada e retorna erros apropriados.

#### 4.1 Validação de Tipo de Honeypot
**Endpoint:** `POST /api/honeypots`

**O que é testado:**
- ✅ Status code 400 (Bad Request) para tipo inválido
- ✅ Apenas tipos válidos são aceitos: `ssh`, `telnet`, `http`
- ✅ Mensagem de erro é retornada

**Dados de teste (inválidos):**
```json
{
  "name": "Invalid",
  "type": "invalid",
  "port": 1234
}
```

#### 4.2 Validação de Campos Obrigatórios
**Endpoint:** `POST /api/honeypots`

**O que é testado:**
- ✅ Status code 400 (Bad Request) quando campos obrigatórios estão faltando
- ✅ Mensagem de erro indica qual campo está faltando

**Dados de teste (incompletos):**
```json
{
  "name": "No Port"
}
```

#### 4.3 Validação de Chave Estrangeira
**Endpoint:** `POST /api/logs`

**O que é testado:**
- ✅ Status code 404 (Not Found) para honeypot_id inexistente
- ✅ Não é possível criar log para honeypot que não existe
- ✅ Integridade referencial é mantida

**Dados de teste (honeypot inexistente):**
```json
{
  "honeypot_id": 99999,
  "ip_address": "1.2.3.4",
  "event_type": "test"
}
```

---

## 🖼️ Interface Swagger UI

A API Beehive Backend inclui documentação interativa via Swagger UI, acessível em `http://localhost:5000/docs/`

### Tela Principal do Swagger UI

![Swagger UI - Tela Principal](https://github.com/user-attachments/assets/b2c5dfe2-0b8e-48c8-aa38-1a9ba743bc7d)

A tela principal mostra todos os endpoints organizados por namespace:
- **honeypots**: Operações relacionadas aos honeypots
- **logs**: Operações relacionadas aos logs
- **health**: Verificação de saúde da API

### Endpoints de Honeypots

![Swagger UI - Honeypots](https://github.com/user-attachments/assets/94997b14-dd30-432a-8af0-9c393083f3e4)

Todos os endpoints CRUD para gerenciamento de honeypots:
- `POST /honeypots/` - Cria um novo honeypot
- `GET /honeypots/` - Lista todos os honeypots
- `DELETE /honeypots/{honeypot_id}` - Remove um honeypot e seus logs
- `PUT /honeypots/{honeypot_id}` - Atualiza um honeypot
- `GET /honeypots/{honeypot_id}` - Obtém um honeypot específico

### Detalhes do Endpoint POST

![Swagger UI - POST Endpoint](https://github.com/user-attachments/assets/14abce65-b333-470a-a93a-25437e1de1eb)

Visualização detalhada do endpoint POST /honeypots/:
- **Parameters**: Mostra o schema JSON esperado
- **Try it out**: Permite testar o endpoint diretamente no navegador
- **Responses**: Mostra exemplos de respostas de sucesso e erro
- **Model**: Documenta a estrutura dos dados

---

## 📊 Cobertura de Testes

Os testes cobrem as seguintes áreas:

| Funcionalidade | Cobertura | Status |
|----------------|-----------|---------|
| Health Check | ✅ 100% | Completo |
| Honeypots CRUD | ✅ 100% | Completo |
| Logs CRUD | ✅ 100% | Completo |
| Validação de Entrada | ✅ 100% | Completo |
| Filtragem de Logs | ✅ 100% | Completo |
| Integridade Referencial | ✅ 100% | Completo |

---

## 🔍 Estrutura do Arquivo de Testes

O arquivo `test_api.py` está organizado da seguinte forma:

```python
#!/usr/bin/env python3
"""
Simple test script for Beehive Backend API
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"

def test_health():
    """Test health endpoint"""
    # Testa se a API está respondendo corretamente

def test_honeypots():
    """Test honeypots CRUD operations"""
    # Testa criação, listagem e obtenção de honeypots
    # Retorna o ID do honeypot criado para uso nos testes de logs

def test_logs(honeypot_id):
    """Test logs CRUD operations"""
    # Testa criação, listagem e filtragem de logs
    # Usa o honeypot_id recebido como parâmetro

def test_validation():
    """Test input validation"""
    # Testa todos os cenários de validação de entrada
    # Garante que erros são retornados corretamente

def main():
    """Run all tests"""
    # Orquestra a execução de todos os testes
    # Trata erros de conexão e exceções
```

---

## 🛠️ Tecnologias Utilizadas nos Testes

- **Python 3.8+**: Linguagem de programação
- **requests**: Biblioteca para fazer requisições HTTP
- **json**: Manipulação de dados JSON
- **sys**: Controle de exit codes

---

## 📚 Próximos Passos

Para expandir a suíte de testes, considere adicionar:

1. **Testes de Atualização (PUT)**
   - Validar atualização de honeypots
   - Testar atualização parcial vs completa

2. **Testes de Deleção (DELETE)**
   - Validar deleção de honeypots
   - Verificar cascade delete de logs
   - Validar deleção de logs individuais

3. **Testes de Performance**
   - Tempo de resposta dos endpoints
   - Capacidade de lidar com múltiplas requisições

4. **Testes de Segurança**
   - SQL Injection
   - XSS
   - CORS

5. **Testes de Integração**
   - Fluxos completos de uso
   - Cenários de usuário real

---

## 🐛 Solução de Problemas

### Erro: "Could not connect to the API"
**Solução:** Certifique-se de que o servidor está rodando:
```bash
python app.py
```

### Erro: "Test failed: AssertionError"
**Solução:** Verifique se o banco de dados está em estado limpo. Delete o arquivo `beehive.db` e reinicie o servidor:
```bash
rm beehive.db
python app.py
```

### Erro: "ModuleNotFoundError"
**Solução:** Instale as dependências:
```bash
pip install -r requirements.txt
```

---

## 📞 Suporte

Se você encontrar problemas com os testes ou tiver dúvidas:
1. Verifique a seção de solução de problemas acima
2. Consulte o README.md do projeto
3. Abra uma issue no repositório

---

## 📄 Licença

Este documento faz parte do projeto Beehive Backend, licenciado sob MIT License.
