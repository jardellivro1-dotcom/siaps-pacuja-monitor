# Guia de Implantação e Publicação Controlada

Este documento define os requisitos e procedimentos para implantação segura, configuração de ambientes, esteira de testes pré-publicação e processo de reversão (*rollback*) do **Monitor APS Pacujá**.

---

## 1. Separação de Ambientes

O sistema prevê três ambientes com isolamento estrito de configurações e credenciais:

| Ambiente | Propósito | Configuração Principal |
|---|---|---|
| **Desenvolvimento (`development`)** | Construção local de novas funcionalidades e depuração | `FLASK_ENV=development`, `SIAPS_SECRET_KEY=dev-only-change-me`, banco local SQLite em `data/siaps_monitor.db` |
| **Homologação (`staging`)** | Validação conjunta com a Coordenação da APS de Pacujá | `FLASK_ENV=staging`, chave administrativa de teste `SIAPS_ADMIN_KEY`, cópia dos CSVs oficiais reais |
| **Produção (`production`)** | Uso gerencial contínuo pela Secretaria de Saúde de Pacujá | `FLASK_ENV=production`, `SIAPS_SECRET_KEY` aleatório de 64 caracteres, `SIAPS_ADMIN_KEY` seguro e restrito à gestão, HTTPS obrigatório |

---

## 2. Variáveis de Ambiente

As configurações devem ser fornecidas via variáveis de ambiente do sistema operacional ou arquivo `.env` seguro (nunca versionado no Git):

```bash
# Ambiente de execução: development, staging ou production
FLASK_ENV=production

# Chave secreta de sessão da aplicação Flask (gerar com: python -c "import secrets; print(secrets.token_hex(32))")
SIAPS_SECRET_KEY=substitua_por_uma_chave_criptografica_forte_de_64_caracteres

# Chave administrativa para operações de escrita (sincronização e planos de ação)
SIAPS_ADMIN_KEY=pacuja_chave_administrativa_segura_2026

# Caminhos personalizados para banco de dados e arquivos (opcional)
DATABASE_PATH=data/siaps_monitor.db
RAW_DATA_DIR=data/raw
```

---

## 3. Checklist Obrigatório Pré-Implantação

Antes de disponibilizar qualquer nova versão em homologação ou produção:

1. [ ] **Verificação de Regras do AGENTS.md:** Confirmar que nenhum dado de paciente, credencial ou caminho de acesso restrito foi adicionado.
2. [ ] **Execução Completa da Suíte de Testes:**
   ```bash
   .venv\Scripts\python.exe -m unittest discover -s tests -v
   ```
   *Todos os 38 testes devem passar com 100% de sucesso.*
3. [ ] **Verificação de Cabeçalhos de Segurança:**
   Confirmar presença de CSP, X-Frame-Options: DENY, X-Content-Type-Options: nosniff e HSTS.
4. [ ] **Verificação de Permissões de Arquivo:**
   Garantir que o processo do servidor web tenha privilégios mínimos de leitura/escrita apenas nas pastas `data/` e `data/raw/`.
5. [ ] **Verificação de Dependências:**
   Confirmar que o `requirements.txt` contém versões fixadas e auditadas sem pacotes desnecessários.

---

## 4. Procedimento de Reversão (Rollback)

Caso uma nova versão apresente comportamento inesperado em produção:

1. **Reversão do Código:**
   Retorne para a tag ou commit anterior estável no Git:
   ```bash
   git checkout tags/v1.0.0
   ```
2. **Reversão da Base de Dados:**
   Caso a atualização tenha envolvido migrações no banco SQLite, restaure a cópia de segurança realizada no checklist pré-deploy:
   ```bash
   copy /Y data\siaps_monitor.db.bak data\siaps_monitor.db
   ```
3. **Reinicialização do Serviço:**
   Reinicie o processo web e valide o endpoint `GET /healthz`.
