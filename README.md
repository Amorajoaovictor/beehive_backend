# Beehive Backend

Backend do Beehive, um app de segurança que serve para monitoramento de honeypots SSH, Telnet e HTTP.

## 🚀 Características

- **API REST completa** para gerenciamento de honeypots e logs
- **Suporte a múltiplos tipos** de honeypots: SSH, Telnet e HTTP
- **Sistema de logs robusto** com relacionamento FK para honeypots
- **Filtragem de logs** por honeypot, IP e tipo de evento
- **Validação de entrada** completa
- **CORS habilitado** para integração com frontend
- **Base de dados SQLite** (fácil de configurar e usar)

## 📋 Pré-requisitos

- Python 3.8+
- pip

## 🛠️ Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd beehive_backend
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. (Opcional) Configure variáveis de ambiente:
```bash
cp .env .env
# Edite .env com suas configurações
```

4. Execute a aplicação:
```bash
python app.py
```

A API estará disponível em `http://localhost:5000`

## 📚 Documentação da API (Swagger UI)

A aplicação agora inclui documentação interativa da API através do Flask-RESTX com Swagger UI:

- **Swagger UI**: `http://localhost:5000/docs/` - Interface interativa para visualizar e testar todos os endpoints
- **Raiz do projeto**: `http://localhost:5000/` - Redireciona automaticamente para a documentação

### Funcionalidades do Swagger UI:
- ✅ Visualização completa de todas as rotas da API
- ✅ Documentação detalhada de parâmetros e modelos de dados
- ✅ Interface "Try it out" para criar e executar requisições diretamente no navegador
- ✅ Exemplos de requisições e respostas
- ✅ Geração automática de comandos curl
- ✅ Validação de entrada em tempo real

**Não é mais necessário usar ferramentas externas como Postman** - tudo pode ser testado diretamente na interface web!

## 📊 Estrutura da Base de Dados

### Tabela Honeypots
- `id` (Integer, PK): ID único do honeypot
- `name` (String): Nome do honeypot
- `type` (String): Tipo do honeypot (ssh, telnet, http)
- `host` (String): Host do honeypot (padrão: 0.0.0.0)
- `port` (Integer): Porta do honeypot
- `status` (String): Status do honeypot (active, inactive)
- `created_at` (DateTime): Data de criação

### Tabela Logs
- `id` (Integer, PK): ID único do log
- `honeypot_id` (Integer, FK): Referência ao honeypot
- `ip_address` (String): Endereço IP que gerou o log
- `timestamp` (DateTime): Timestamp do evento
- `event_type` (String): Tipo do evento
- `details` (Text): Detalhes do evento

## 🔌 API Endpoints

### Honeypots

#### GET /api/honeypots
Lista todos os honeypots.

**Resposta:**
```json
[
  {
    "id": 1,
    "name": "SSH Honeypot 1",
    "type": "ssh",
    "host": "0.0.0.0",
    "port": 2222,
    "status": "inactive",
    "created_at": "2024-01-01T12:00:00",
    "logs_count": 5
  }
]
```

#### POST /api/honeypots
Cria um novo honeypot.

**Corpo da requisição:**
```json
{
  "name": "Meu Honeypot SSH",
  "type": "ssh",
  "port": 2222,
  "host": "0.0.0.0",
  "status": "inactive"
}
```

**Campos obrigatórios:** `name`, `type`, `port`
**Tipos válidos:** `ssh`, `telnet`, `http`

#### GET /api/honeypots/{id}
Obtém um honeypot específico.

#### PUT /api/honeypots/{id}
Atualiza um honeypot.

#### DELETE /api/honeypots/{id}
Remove um honeypot e todos os seus logs.

### Logs

#### GET /api/logs
Lista todos os logs com filtros opcionais.

**Parâmetros de consulta:**
- `honeypot_id`: Filtra por ID do honeypot
- `ip_address`: Filtra por endereço IP
- `event_type`: Filtra por tipo de evento

**Exemplo:** `/api/logs?honeypot_id=1&ip_address=192.168.1.100`

#### POST /api/logs
Cria um novo log.

**Corpo da requisição:**
```json
{
  "honeypot_id": 1,
  "ip_address": "192.168.1.100",
  "event_type": "connection_attempt",
  "details": "SSH connection attempt with username admin"
}
```

**Campos obrigatórios:** `honeypot_id`, `ip_address`, `event_type`

#### GET /api/logs/{id}
Obtém um log específico.

#### DELETE /api/logs/{id}
Remove um log.

### Utilidade

#### GET /api/health
Verifica o estado da API.

**Resposta:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00"
}
```

## 🧪 Testes

Execute o script de testes para validar a API:

```bash
# Certifique-se de que a aplicação está rodando
python app.py &

# Em outro terminal, execute os testes
python test_api.py
```

## ⚙️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` baseado no `.env`:

```env
DATABASE_URL=sqlite:///beehive.db
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=True
```

### Base de Dados

A aplicação usa SQLite por padrão, que é criada automaticamente quando a aplicação inicia.

Para usar PostgreSQL ou MySQL, altere a `DATABASE_URL` no arquivo `.env`:

```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/beehive

# MySQL
DATABASE_URL=mysql://user:password@localhost/beehive
```

## 🚀 Deploy em Produção

1. Configure as variáveis de ambiente apropriadas
2. Use um servidor WSGI como Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

3. Configure um proxy reverso (nginx) para servir a aplicação
4. Use uma base de dados mais robusta (PostgreSQL, MySQL)

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.

## 📞 Suporte

Se você encontrar problemas ou tiver dúvidas, abra uma issue no repositório.
