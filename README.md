# Monitor APS Pacujá · Gestão e Resultados Siaps

[![CI](https://github.com/jardellivro1-dotcom/siaps-pacuja-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/jardellivro1-dotcom/siaps-pacuja-monitor/actions/workflows/ci.yml)
[![Rotina Mensal](https://github.com/jardellivro1-dotcom/siaps-pacuja-monitor/actions/workflows/monthly_update.yml/badge.svg)](https://github.com/jardellivro1-dotcom/siaps-pacuja-monitor/actions/workflows/monthly_update.yml)
[![Metodologia](https://img.shields.io/badge/Metodologia-Nota%20T%C3%A9cnica%20n%C2%BA%208%2F2026-blue)](docs/metodologia.md)
[![Segurança](https://img.shields.io/badge/Seguran%C3%A7a-OWASP%20ASVS%20v4.0.3-green)](docs/seguranca_asvs.md)
[![Acessibilidade](https://img.shields.io/badge/Acessibilidade-WCAG%202.2%20AA-teal)](static/css/app.css)

Aplicação web institucional e painel gerencial de alto desempenho para monitoramento, auditoria e planejamento do cofinanciamento federal da Atenção Primária à Saúde (APS) em **Pacujá, Ceará (IBGE 230990)**, com base exclusiva nos relatórios públicos do **Siaps / Ministério da Saúde** e nas diretrizes da **Nota Técnica nº 8/2026-DEAPS/SAPS/MS**.

---

## 🚀 Hospedagem Gratuita na Nuvem (1-Clique)

O aplicativo foi configurado para implantação gratuita e contínua em múltiplos provedores de nuvem:

| Plataforma | Tipo de Hospedagem | Deploy em 1-Clique |
|---|---|---|
| **Render** | Serviço Web Python / Gunicorn com SSL Grátis | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/jardellivro1-dotcom/siaps-pacuja-monitor) |
| **Vercel** | Serverless Python com CDN global e zero latência | [![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/jardellivro1-dotcom/siaps-pacuja-monitor) |
| **Docker / VPS** | Container universal (`docker-compose up -d`) | Veja instruções abaixo |

---

## 🌟 Funcionalidades Principais

1. **Painel Gerencial e KPIs Oficiais:**
   - Acompanhamento do **Componente II** (Vínculo e Acompanhamento Territorial - CVAT) e **Componente III** (Qualidade do Cuidado).
   - Metodologia rigorosamente versionada e testada da **Nota Técnica nº 8/2026**.
   - Identificação precoce de indicadores que merecem atenção da coordenação.
2. **Geração de Relatório Executivo Oficial (`/relatorio`):**
   - Relatório institucional formatado para tomada de decisão pela Secretaria Municipal de Saúde.
   - Layout otimizado para impressão A4 e exportação em PDF (`window.print()`).
   - Quadro de liderança, detalhamento por indicador, ações requeridas, trilha de hashes SHA-256 e espaço para despacho e assinaturas formais.
3. **Rotina de Acompanhamento Mês a Mês:**
   - Rotina automatizada que consulta o catálogo público do Siaps todo dia 5 às 06:00 UTC.
   - Botão no painel para verificação manual sob demanda a qualquer instante.
   - Histórico longitudinal de checagens, identificando novas competências e reprocessamentos de dados sem duplicar registros (idempotência).
4. **Plano de Ações de Melhoria da APS:**
   - Gestão de metas operacionais da coordenação vinculadas a equipes e indicadores.
   - **Salvaguarda LGPD ativa:** interceptador automatizado que bloqueia qualquer inclusão de CPF ou número do Cartão SUS (CNS) em campos de texto livre.
5. **Auditoria Criptográfica de Arquivos Brutos:**
   - Registro imutável de URL pública de origem, timestamp ISO em UTC, tamanho em bytes e hash SHA-256 de cada relatório original do Ministério da Saúde.

---

## 🛠️ Execução Local

### Pré-requisitos
- Python 3.11 ou 3.12
- Git

### Passo a passo no Windows (PowerShell):
```powershell
# 1. Clonar o repositório
git clone https://github.com/jardellivro1-dotcom/siaps-pacuja-monitor.git
cd siaps-pacuja-monitor

# 2. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Instalar dependências fixadas
pip install -r requirements.txt

# 4. Executar a aplicação
python app.py
```
Acesse no navegador: **`http://127.0.0.1:5000/`** ou o relatório em **`http://127.0.0.1:5000/relatorio`**.

### Executar a Suíte Completa de Testes:
```powershell
python -m unittest discover -s tests -v
```
*40 testes automatizados cobrindo cálculos, segurança OWASP ASVS, validadores, concorrência e endpoints.*

---

## 🐳 Execução via Docker / Docker Compose

Para executar em qualquer servidor Linux ou VPS:
```bash
docker-compose up -d
```
Acesse `http://localhost:5000/healthz` para checar a saúde do container.

---

## 📚 Documentação Técnica e Normativa

- [**Escopo e Regras do Produto**](docs/escopo.md): Delimitação territorial, usuários e fontes permitidas.
- [**Critérios de Aceitação**](docs/criterios_aceitacao.md): Comportamento esperado para todas as funcionalidades e falhas.
- [**Metodologia Oficial NT 8/2026**](docs/metodologia.md): Fórmulas, pesos, conceitos e faixas oficiais.
- [**Arquitetura do Sistema**](docs/arquitetura.md): Separação de camadas e fluxo de dados.
- [**Segurança e Controles OWASP ASVS**](docs/seguranca_asvs.md): Mapeamento contra ameaças cibernéticas.
- [**Governança de Privacidade e LGPD**](docs/privacidade_lgpd.md): Conformidade com as normas da ANPD.
- [**Manual do Usuário**](docs/manual_usuario.md): Guia prático de interpretação dos indicadores.
- [**Operação, Backup e Recuperação**](docs/operacao_backup.md): Monitoramento contínuo e plano de desastre.
- [**Guia de Implantação e Ambientes**](docs/implantacao.md): Checklist pré-deploy e rollback.
- [**Changelog de Versões**](docs/changelog.md): Histórico SemVer de lançamentos.

---

## 📜 Licença e Transparência Pública

Este projeto foi desenvolvido com código aberto sob a licença MIT em conformidade com as diretrizes de transparência do Sistema Único de Saúde (SUS).
