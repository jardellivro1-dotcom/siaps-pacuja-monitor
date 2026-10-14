# Guia Operacional de Implantação Segura e Rollback Automatizado
**Sistema:** Monitor APS Pacujá — Gestão e Resultados Siaps  
**Município:** Pacujá / Ceará (IBGE 230990)  
**Versão:** 1.0.0 (Release Homologada para Uso Compartilhado)  
**Diretriz Primária:** **NUNCA exponha diretamente à Internet o servidor da aplicação (porta 5000).** O tráfego externo deve transitar exclusivamente através de proxy reverso seguro HTTPS.

---

## 1. Arquitetura de Isolamento de Rede

A topologia operacional obrigatória do sistema é dividida em camadas estanques:

```
[ INTERNET / REDE MUNICIPAL ]
             │
             │ HTTPS (Porta 443 / TLS 1.3 / HSTS / Rate-Limiting)
             ▼
   ┌───────────────────────────────────────────┐
   │  Proxy Reverso Seguro (Nginx ou Caddy)    │
   │  Terminação TLS, Cabeçalhos OWASP, WAF    │
   └─────────────────────┬─────────────────────┘
                         │
                         │ HTTP Local estrito (127.0.0.1:5000 / loopback isolado)
                         ▼
   ┌───────────────────────────────────────────┐
   │  Gunicorn / Flask (Servidor da Aplicação) │
   │  Usuário não-root (siaps:siaps)           │
   │  ProtectSystem=full / PrivateTmp=true     │
   └─────────────────────┬─────────────────────┘
                         │
                         │ Conexão Local WAL Mode (busy_timeout=5000)
                         ▼
   ┌───────────────────────────────────────────┐
   │  Banco Compartilhado SQLite (WAL)         │
   │  data/siaps_monitor.db                    │
   └─────────────────────▲─────────────────────┘
                         │
   ┌─────────────────────┴─────────────────────┐
   │  Agendador Autônomo (Scheduler Daemon)    │
   │  scripts/scheduler_daemon.py              │
   │  Backup externo, Sincronização e LGPD     │
   └───────────────────────────────────────────┘
```

---

## 2. Checklist Pré-Implantação

Antes de iniciar os serviços no servidor municipal de Pacujá:

- [ ] **1. Regras do AGENTS.md e LGPD:** Confirmado que o repositório contém apenas relatórios públicos de Pacujá/CE e nenhum dado pessoal de pacientes.
- [ ] **2. Isolamento de Interface:** Confirmado que o Gunicorn/Flask está configurado para escutar estritamente em `127.0.0.1:5000` (e nunca em `0.0.0.0`).
- [ ] **3. Proxy Reverso HTTPS:** Nginx ou Caddy configurado com certificados válidos e porta 80 redirecionada para 443.
- [ ] **4. Suíte de Testes 100% Verde:**
  ```bash
  .venv/bin/python -m unittest discover -s tests -v
  ```
  *Todos os 49 testes aprovados sem falhas.*
- [ ] **5. Backup Snapshot Inicial:** Realizado snapshot inicial do banco e CSVs brutos:
  ```bash
  .venv/bin/python scripts/backup_external.py
  ```
- [ ] **6. Variáveis de Ambiente Criadas:** Arquivo `/etc/siaps-monitor.env` restrito com permissão `600` ao usuário do sistema.

---

## 3. Passo a Passo de Implantação no Servidor

### 3.1. Criação do Usuário de Serviço sem Privilégios
```bash
sudo useradd -r -s /bin/false -d /opt/siaps-pacuja-monitor siaps
sudo chown -R siaps:siaps /opt/siaps-pacuja-monitor
```

### 3.2. Configuração do Arquivo de Ambiente Seguro
Crie o arquivo `/etc/siaps-monitor.env`:
```ini
FLASK_ENV=production
SIAPS_SECRET_KEY=gerar_chave_aleatoria_64_chars_hex
SIAPS_REQUIRE_AUTH=1
SIAPS_ADMIN_PASSWORD=SenhaForteAdmin2026!
SIAPS_COORD_PASSWORD=SenhaForteCoord2026!
SIAPS_EQUIPE_PASSWORD=SenhaForteEquipe2026!
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/SEU/WEBHOOK/AQUI
```
Proteja o arquivo de credenciais:
```bash
sudo chown root:siaps /etc/siaps-monitor.env
sudo chmod 640 /etc/siaps-monitor.env
```

### 3.3. Instalação e Ativação dos Serviços Systemd

1. **Serviço da Aplicação Web:**
   Copie o arquivo de unidade hardened:
   ```bash
   sudo cp deploy/systemd/siaps-monitor.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now siaps-monitor.service
   ```

2. **Serviço do Agendador Autônomo:**
   Copie a unidade do agendador independente:
   ```bash
   sudo cp deploy/systemd/siaps-scheduler.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now siaps-scheduler.service
   ```

### 3.4. Ativação do Proxy Reverso (Nginx ou Caddy)

* **Opção A (Nginx):**
  ```bash
  sudo cp deploy/nginx/nginx.conf /etc/nginx/sites-available/siaps.pacuja.ce.gov.br
  sudo ln -s /etc/nginx/sites-available/siaps.pacuja.ce.gov.br /etc/nginx/sites-enabled/
  sudo nginx -t && sudo systemctl reload nginx
  ```
* **Opção B (Caddy com TLS Automático):**
  ```bash
  sudo cp deploy/caddy/Caddyfile /etc/caddy/Caddyfile
  sudo systemctl reload caddy
  ```

### 3.5. Verificação Pós-Deploy
Execute a chamada de saúde no loopback interno:
```bash
curl -f http://127.0.0.1:5000/healthz
```
Resposta esperada:
```json
{
  "application": "Monitor APS Pacujá",
  "database": "connected",
  "status": "ok",
  "version": "1.0.0"
}
```

---

## 4. Plano de Rollback e Recuperação de Emergência

Caso seja identificada anomalia grave em produção (inconsistência de cálculo, erro de regressão ou indisponibilidade crítica), siga o protocolo de reversão imediata:

### 4.1. Passo 1 — Interromper os Serviços de Escrita
```bash
sudo systemctl stop siaps-scheduler.service
sudo systemctl stop siaps-monitor.service
```

### 4.2. Passo 2 — Restaurar Código para a Tag Estável Anterior
```bash
cd /opt/siaps-pacuja-monitor
git fetch --tags
git checkout tags/v1.0.0  # ou commit estável precedente
```

### 4.3. Passo 3 — Restauração do Snapshot Íntegro de Banco e CSVs
Localize o último backup comprovado no diretório de segurança:
```bash
# Identifica o último backup e sua assinatura SHA-256
LATEST_BACKUP=$(ls -t data/backups/backup_siaps_pacuja_*.tar.gz | head -n 1)
LATEST_SHA=$(ls -t data/backups/backup_siaps_pacuja_*.sha256 | head -n 1)

# Verifica integridade criptográfica antes de restaurar
sha256sum -c "$LATEST_SHA"

# Se o hash for válido, descompacta no diretório operacional
tar -xzvf "$LATEST_BACKUP" -C data/
```

### 4.4. Passo 4 — Verificação de Integridade do Banco Restaurado
```bash
.venv/bin/python -c "import sqlite3; conn = sqlite3.connect('data/siaps_monitor.db'); print(conn.execute('PRAGMA integrity_check').fetchall())"
```
Saída obrigatória: `[('ok',)]`.

### 4.5. Passo 5 — Reinicialização dos Serviços e Notificação
```bash
sudo systemctl start siaps-monitor.service
sudo systemctl start siaps-scheduler.service
```

Valide imediatamente a saúde da aplicação:
```bash
curl -I https://siaps.pacuja.ce.gov.br/healthz
```

O tempo estimado para conclusão de um rollback completo é de **menos de 3 minutos**, garantindo RTO (Recovery Time Objective) e RPO (Recovery Point Objective) compatíveis com a criticidade da gestão municipal.
