# Regras para agentes de programação

1. Trabalhe apenas com os relatórios públicos selecionados no Siaps para Ceará e Pacujá.
2. Nunca abra, use, automatize ou tente descobrir caminhos do Acesso Restrito.
3. Nunca introduza dados de pacientes, credenciais, tokens ou chaves no repositório.
4. Não invente valores, classificações, meses elegíveis ou equipes. Mantenha ausências como ausências.
5. Preserve cada CSV original sem alteração. Registre URL pública de origem, data de captura, período, equipe, componente, tamanho e SHA-256.
6. A importação deve ser idempotente: mesmo hash não cria cópia lógica; hash diferente cria nova versão auditável.
7. Não calcule nota quando faltarem os dados ou regras necessárias. Exiba “incompleto” e explique o motivo.
8. Use a Nota Técnica nº 8/2026 para eSF, eAP, eSB e eMulti. Não aplique essa nota a eAPP, eCR ou eSFR.
9. Antes de alterar parser ou cálculo, atualize testes com exemplos oficiais e faça uma revisão independente dos limites.
10. Não interprete o resultado como avaliação clínica nem recomende conduta para pacientes. Sugestões futuras devem ser ações de gestão revisadas por profissionais.
