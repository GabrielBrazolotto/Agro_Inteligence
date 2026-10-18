# Diagnóstico de integração — 15/10/2026

## Atualização: correção validada com Gemini 3.5 Flash

Após os testes iniciais descritos abaixo, `gemini-3.5-flash` respondeu com sucesso
em um teste mínimo de streaming. O modelo foi configurado explicitamente no `.env`,
no `.env.example` e no padrão do código. A chave do `.env` foi preservada, e o
campo de chave no `.env.example` foi limpo.

Também foi validado o fluxo real completo para a pergunta sobre a política de
descontos e a aprovação do gerente: índice, embedding da consulta, recuperação,
contexto DuckDB e geração via `GeminiGateway.stream`. A política foi recuperada,
a resposta citou `politica_comercial.md` e mencionou gerente e os limites 5% e 8%.
O conteúdo da resposta e a chave não foram registrados. Esse teste comprova o
funcionamento do fluxo com Gemini 3.5 Flash naquele momento, sem garantir
disponibilidade futura nem acesso com uma chave substituída.

As conclusões de indisponibilidade abaixo referem-se aos modelos testados
anteriormente; a falha 404 do Gemini 2.5 Flash não foi resolvida no provedor.

## Causa observada

A geração real com `gemini-2.5-flash` retornou **HTTP 404**, tanto em
`generate_content_stream` quanto em `generate_content`. Essa é a falha comprovada
que impede a resposta. O tratamento anterior escondia a etapa e o código HTTP.
Não foi comprovado que a chave seja inválida, que a cota esteja esgotada ou que
o modelo tenha sido descontinuado. O modelo aparece na lista retornada pela API
com suporte anunciado a `generateContent`, apesar do 404 na execução.

## Evidências verificadas sem divulgar segredos

- `.env` existe na raiz, `GEMINI_API_KEY` está preenchida e coincide com a chave
  efetiva. O valor não foi impresso nem salvo neste relatório.
- SDK instalado: `google-genai==1.75.0`. Modelo configurado:
  `gemini-2.5-flash`; embeddings: `gemini-embedding-001`.
- Base efetiva do SDK corresponde ao serviço oficial
  `https://generativelanguage.googleapis.com`; sem configuração explícita de proxy,
  base alternativa ou Vertex AI identificada no processo de diagnóstico.
- O ChromaDB abriu o índice persistente com três trechos já indexados.
- A consulta real de embeddings e a recuperação para “Qual é a política de
  descontos?” funcionaram: três resultados, incluindo `politica_comercial.md`.
  Não foi necessário reindexar documentos nesta verificação real.
- Teste mínimo independente de geração: 404 com `gemini-2.5-flash`, com e sem
  streaming. Nenhuma conversa do usuário ou dados comerciais foram enviados nesses
  testes mínimos; somente uma solicitação de resposta “OK”.
- Comparações sem alterar a configuração: `gemini-2.5-flash-lite` também retornou
  404; `gemini-3.8-flash` retornou 503. Nenhuma geração real teve sucesso.
- O ambiente de execução restrito bloqueou inicialmente a rede. Os resultados HTTP
  acima foram obtidos após executar o diagnóstico com acesso autorizado à rede.
  Esse bloqueio inicial não foi confundido com o erro da API.

## Correções implementadas

Mensagens amigáveis e logs por etapa: configuração, abertura do índice, sincronização,
recuperação, contexto comercial e geração. Classificação de 400, 401, 403, 404,
429 e 500, além de indisponibilidade 502/503/504, timeout, conexão e resposta vazia.
Os logs incluem somente etapa, referência aleatória, categoria, código HTTP e
contagens/flags permitidos. Não incluem exceções brutas, tracebacks, headers, URLs
de requisições, chave, texto recuperado ou mensagens do usuário.

Uma falha durante streaming descarta o texto parcial e não salva a tentativa no
histórico. Se a recuperação funcionou e a geração falhou, a interface ainda permite
consultar os trechos recuperados. A configuração agora relê o `.env` a cada chamada,
aceita BOM do Windows, preserva a precedência de variáveis explícitas do processo
e oculta a chave no `repr` de Settings.

O SDK usa explicitamente Gemini Developer API (`vertexai=False`), timeout de 30
segundos e uma tentativa por requisição. Não há fallback silencioso nem repetição
automática que possa multiplicar consumo de cota. O cliente é fechado ao final.

## Testes e limites

30 testes locais aprovados, incluindo simulações dos códigos HTTP solicitados nas
etapas de recuperação e geração, timeout/conexão, resposta vazia, falha no meio do
streaming, ausência de vazamento nos logs/mensagens, releitura de configuração,
histórico/limpeza, integridade comercial e persistência/recuperação ChromaDB.

O funcionamento da geração real **não está validado**. O código de diagnóstico
permite repetir uma verificação controlada quando o acesso ao modelo estiver
disponível. A listagem de modelos não garante que a execução esteja disponível.
O 404 sozinho não comprova a causa interna do provedor. Verifique o acesso no
Google AI Studio ou com o suporte do Google antes de trocar modelos/configurações.

Referências oficiais:
[tratamento de erros](https://ai.google.dev/gemini-api/docs/troubleshooting),
[ciclo de vida dos modelos](https://ai.google.dev/gemini-api/docs/deprecations).
