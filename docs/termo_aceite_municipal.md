# Termo de Homologação, Aceite Técnico e Autorização Operacional
**Secretaria Municipal de Saúde de Pacujá — Ceará**  
**Código do Município (IBGE):** 230990 | **UF:** CE  
**Sistema:** Monitor APS Pacujá — Gestão e Resultados Siaps  
**Versão Homologada:** 1.0.0 (Release de Produção e Uso Compartilhado)  

---

## 1. Identificação das Partes

1. **Órgão Responsável:** Secretaria Municipal de Saúde de Pacujá / Prefeitura Municipal de Pacujá.
2. **Área Técnica Demandante:** Coordenação da Atenção Primária à Saúde (APS / eSF / eSB / eMulti).
3. **Área de Governança Digital e TI:** Setor de Informática em Saúde e Tecnologia Municipal.
4. **Aplicação Avaliada:** Monitor Gerencial de Desempenho e Cofinanciamento da Atenção Primária com base na Nota Técnica nº 8/2026 do Ministério da Saúde.

---

## 2. Objeto e Escopo Homologado

Constitui objeto deste Termo a **homologação formal técnica, metodológica e de segurança** do software **Monitor APS Pacujá**, destinado ao acompanhamento executivo dos indicadores de desempenho do Componente II (Vínculo e Acompanhamento Territorial) e Componente III (Qualidade e Acesso às Ações Estratégicas).

### 2.1. Delimitação Territorial e Institucional Estrita
* **Território:** Exclusivamente o município de **Pacujá / CE** (Código IBGE 230990).
* **Equipes Abrangidas:** As 8 (oito) equipes municipais cadastradas no SCNES:
  * 04 Equipes de Saúde da Família (eSF): PSF 01 Bico da Arara, PSF 02 Centro, PSF 03 Bom Gosto, PSF 04 Toquieis.
  * 03 Equipes de Saúde Bucal (eSB): SB 01 Bico da Arara, SB 02 Centro, SB 03 Bom Gosto.
  * 01 Equipe Multiprofissional (eMulti): Equipe Multi Pacujá.
* **Tipos de Equipes Excluídos:** Conforme a Nota Técnica nº 8/2026, equipes dos tipos eAPP, eCR ou eSFR estão expressamente excluídas do cálculo e monitoramento municipal.

---

## 3. Cláusulas de Auditoria e Conformidade

### Cláusula 1ª — Fonte Exclusivamente Pública e Idempotente
A aplicação consome exclusivamente os relatórios e endpoints públicos oficiais disponibilizados pelo Ministério da Saúde (`apisiaps.saude.gov.br`). Fica atestado que:
* Em nenhuma hipótese o software automatiza, consulta ou busca caminhos no módulo de "Acesso Restrito" do Siaps.
* Cada arquivo CSV original é armazenado de forma imutável, com carimbo de data, URL de origem e hash criptográfico SHA-256 verificado.
* A rotina de ingestão é rigorosamente idempotente: arquivos com o mesmo hash não geram duplicações ou alterações espúrias.

### Cláusula 2ª — Metodologia Fiel à Nota Técnica nº 8/2026
A memória de cálculo reproduz com exatidão as regras oficiais:
* Indicadores ausentes ou dados incompletos são exibidos como **"Incompleto / Aguardando Dados"**, sendo vedada a imputação arbitrária de valores zero ou estimativas inventadas.
* Os limites inferiores, limites superiores e ponderações dos Componentes II e III foram conferidos por teste automatizado independente contra a tabela oficial de pesos e metas.
* Fica registrado que os indicadores medem agregação de desempenho das equipes, **não constituindo prontuário clínico individual de pacientes**.

### Cláusula 3ª — Conformidade com a Lei Geral de Proteção de Dados (LGPD)
O sistema foi auditado quanto à privacidade:
* Nenhum dado nominal, prontuário, CPF, Cartão Nacional de Saúde (CNS) ou endereço de cidadãos é coletado, armazenado ou exibido.
* O sistema possui scanner automatizado periódico (`siaps/privacy.py`) que varre as tabelas em busca de dados pessoais acidentais, permitindo expurgo imediato.

### Cláusula 4ª — Segurança Operacional e Isolamento de Rede
Em cumprimento às normas de segurança da informação e OWASP ASVS:
* **Proibição de Exposição Direta:** A aplicação nunca deve ser exposta diretamente à Internet na porta 5000 do Flask/Gunicorn.
* **Proxy Reverso Obrigatório:** O tráfego externo passa obrigatoriamente por proxy reverso seguro (Nginx ou Caddy) com terminação TLS 1.3/1.2, cabeçalhos HSTS, Content-Security-Policy e controle de taxa de requisições (*rate-limiting*).
* **Controle de Acesso RBAC:** Operações de gestão (cadastro de ações de melhoria e sincronização forçada) exigem autenticação prévia com perfis autorizados (`admin`, `coordenador_aps`, `equipe_saude`).

### Cláusula 5ª — Resiliência, Backup e Rollback
* O banco de dados opera em modo WAL com timeout de concorrência, suportando mais de 220 requisições simultâneas por segundo conforme benchmark homologado.
* Existe rotina diária autônoma de backup externo (`scripts/backup_external.py`), com empacotamento atômico, hash SHA-256 e rotação de retenção.
* Procedimento de rollback e contingência testado e validado em menos de 3 minutos.

---

## 4. Declaração de Aceite e Homologação

Os signatários abaixo, no uso de suas atribuições institucionais, declaram que o software **Monitor APS Pacujá (v1.0.0)** foi satisfatoriamente testado, validado e atende a todos os critérios de qualidade, segurança e governança estabelecidos pela Secretaria Municipal de Saúde de Pacujá/CE.

Autoriza-se, a partir desta data, a sua **implantação em ambiente compartilhado da rede municipal**, sob proxy reverso seguro.

Pacujá — Ceará, 14 de Outubro de 2026.

---

### Assinaturas Institucionais:

___________________________________________________________  
**Secretário(a) Municipal de Saúde**  
Secretaria Municipal de Saúde de Pacujá / CE  
CNES Municipal / Gabinete da SMS  

___________________________________________________________  
**Coordenação da Atenção Primária à Saúde (APS)**  
Responsável Técnico pelos Programas eSF, eSB e eMulti  

___________________________________________________________  
**Responsável Técnico de Informática em Saúde / TI**  
Setor de Tecnologia da Informação e Segurança de Dados  
Prefeitura Municipal de Pacujá  
