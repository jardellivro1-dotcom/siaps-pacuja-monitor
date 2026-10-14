# Metodologia oficial para o painel

## Documento de referência

Nota Técnica nº 8/2026-DEAPS/SAPS/MS, publicada pelo Ministério da Saúde em 02/10/2026. A nota revoga a Nota Técnica nº 6/2025 e aplica-se à metodologia dos Componentes II e III para eSF, eAP, eSB e eMulti.

## Componente II — Vínculo e Acompanhamento Territorial

- O resultado quadrimestral é avaliado pela média dos valores mensais das dimensões Cadastro e Acompanhamento.
- A janela máxima indicada pela Figura 1 é de 24 meses para Cadastro e 12 meses para Acompanhamento.
- O bônus de Satisfação do Usuário considera a maior nota obtida entre os meses do quadrimestre; a Figura 1 indica monitoramento dos últimos 30 dias.
- Faixas da nota final: Ótimo `> 8,5`; Bom `>= 7 e <= 8,5`; Suficiente `>= 5 e < 7`; Regular `< 5`.

O app deve conservar as medidas que o Siaps publica e implementar somente a regra cujo campo e denominador estejam identificados no CSV. Se a estrutura não trouxer os elementos necessários para reconstruir a nota, o painel exibirá a classificação/nota oficial disponível e marcará a reconstituição local como indisponível, em vez de deduzir uma fórmula.

## Componente III — Qualidade do Cuidado

- O resultado quadrimestral de cada indicador é a média dos meses monitorados.
- Quando houver suspensão de pagamento, a média considera somente os meses válidos para pagamento.
- Para C2 (desenvolvimento infantil) e C3 (gestação e puerpério), entram apenas meses com crianças completando dois anos ou gestações que atingiram o 42º dia de puerpério no período avaliado.
- O sinal “-” em C2/C3 pode representar inexistência de evento elegível, não desempenho zero.
- Para a nota final, cada conceito de indicador recebe: Regular `0,25`, Suficiente `0,50`, Bom `0,75` e Ótimo `1,00`; multiplica-se pelo peso oficial do indicador e somam-se os pontos.

### Indicadores e pesos para eSF/eAP

| Código | Indicador | Peso | Janela máxima da Figura 2 |
|---|---|---:|---|
| C1 | Mais acesso à APS | 1 | Últimos 30 dias |
| C2 | Cuidado no desenvolvimento infantil | 2 | Últimos 24 meses |
| C3 | Cuidado na gestação e puerpério | 2 | Últimos 12 meses |
| C4 | Cuidado da pessoa com diabetes | 1 | Últimos 12 meses |
| C5 | Cuidado da pessoa com hipertensão | 1 | Últimos 12 meses |
| C6 | Cuidado da pessoa idosa | 1 | Últimos 12 meses |
| C7 | Cuidado da mulher na prevenção do câncer | 2 | Últimos 60 meses |

### Indicadores e pesos para eSB

| Código | Indicador | Peso | Janela máxima da Figura 2 |
|---|---|---:|---|
| B1 | Primeira consulta odontológica programada | 2 | Últimos 30 dias |
| B2 | Tratamento concluído | 2 | Últimos 30 dias |
| B3 | Taxa de exodontias | 2 | Últimos 30 dias |
| B4 | Escovação supervisionada em faixa etária escolar | 1 | Últimos 30 dias |
| B5 | Procedimentos odontológicos individuais preventivos | 2 | Últimos 30 dias |
| B6 | Tratamento restaurador atraumático | 1 | Últimos 30 dias |

### Indicadores e pesos para eMulti

| Código | Indicador | Peso | Janela máxima da Figura 2 |
|---|---|---:|---|
| M1 | Média de atendimentos da eMulti por pessoa | 6 | Últimos 4 meses |
| M2 | Ações interprofissionais da eMulti | 4 | Últimos 4 meses |

### Faixas da nota final do Componente III

- Ótimo: `> 7,5`
- Bom: `>= 5 e <= 7,5`
- Suficiente: `> 2,5 e < 5`
- Regular: `<= 2,5`

## Regras de apresentação

- Mostrar a classificação oficial publicada e, em separado, o cálculo local reproduzível.
- Registrar meses incluídos e excluídos da média e a razão da exclusão, quando presente nos dados.
- Distinguir `não publicado`, `não aplicável`, `suspenso`, `zero publicado` e `erro de importação`.
- Não calcular média se houver informação indispensável ausente.
- Exibir o documento metodológico, a data de vigência e a versão do parser junto ao cálculo.

## Nota sobre tipos de equipe

A Nota Técnica nº 8/2026 trata eSF, eAP, eSB e eMulti. O Siaps lista notas separadas para eAPP, eCR e eSFR; esses tipos ficam fora do escopo deste projeto até uma decisão explícita de ampliação e implementação das metodologias correspondentes.
