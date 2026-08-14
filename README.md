# Job Hunter Bot

Coleta vagas do LinkedIn (últimas 24h) por palavra-chave, filtra por nível
(estágio/júnior/pleno) e localização (remoto ou Vale do Aço/MG), e manda
um resumo por WhatsApp — sem Twilio, usando o CallMeBot (gratuito).

## Fonte de dados: LinkedIn

O scraper usa o endpoint público `jobs-guest` do LinkedIn — o mesmo que o
navegador chama quando você pesquisa vagas sem estar logado, então não
precisa de login nem token.

**Antes de aumentar o volume, vale saber:**
- É um endpoint não-oficial, sem contrato de suporte — pode mudar de
  estrutura ou ficar mais restrito sem aviso.
- Scraping do LinkedIn vai contra os Termos de Uso da plataforma; o risco
  prático (nesse volume baixo, sem login) é o endpoint parar de responder
  ou pedir captcha, não necessariamente bloqueio de conta (você nem usa
  uma conta aqui). Ainda assim, é bom saber que o risco existe.
- O código já inclui delays entre requisições — não remova isso.

## 1. Configurar o WhatsApp (CallMeBot)

O número do bot **muda de tempos em tempos** (o número antigo leva denúncia
de spam e é substituído) — antes de começar, confirme o número atual em
https://www.callmebot.com/blog/free-api-whatsapp-messages/. No momento em
que este README foi escrito, o número era **+34 623 75 84 18**.

1. Salve o número atual do bot nos seus contatos como "CallMeBot".
2. Mande a mensagem: `I allow callmebot to send me messages` pelo WhatsApp
   pra esse contato. Espere até 2 minutos pela resposta com o `apikey`.
3. Você recebe um `apikey` de volta — guarde ele.
4. Copie `.env.example` para `.env` e preencha:
   - `CALLMEBOT_PHONE`: **seu** número, com `+` e DDI, ex: `+5531999999999`
     (tem que ser exatamente o formato que aparece no seu WhatsApp)
   - `CALLMEBOT_APIKEY`: o apikey que você recebeu

**Teste antes de confiar no GitHub Actions:** cole essa URL no navegador
trocando pelos seus dados — se a mensagem chegar no WhatsApp, está tudo
certo:
```
https://api.callmebot.com/whatsapp.php?phone=+5531999999999&text=teste&apikey=SEU_APIKEY
```

## 2. Rodar localmente

```bash
pip install -r requirements.txt
cp .env.example .env  # depois edite com seus dados
python main.py
```

## 3. Rodar de graça 24/7 (GitHub Actions)

Não precisa de VPS. O workflow em `.github/workflows/cron.yml` já roda o
bot a cada hora nos servidores do GitHub.

1. Suba esse projeto pra um repositório no GitHub (pode ser privado).
2. Em **Settings → Secrets and variables → Actions → Secrets**, adicione:
   - `CALLMEBOT_PHONE`
   - `CALLMEBOT_APIKEY`
3. Em **Settings → Secrets and variables → Actions → Variables** (opcional,
   senão usa os valores padrão do código), adicione:
   - `KEYWORDS`, `LEVELS`, `SEARCH_LOCATION`, `LOCATION_TERMS`
4. Pronto — o workflow já roda sozinho a cada hora. Pra testar sem esperar,
   use o botão "Run workflow" na aba Actions.

Repositório **privado**: o plano free do GitHub dá 2.000 minutos/mês de
Actions, de sobra pra rodar isso de hora em hora (cada execução leva
segundos). Repositório **público**: minutos ilimitados.

## Estrutura

```
job-hunter-bot/
├── main.py                  # orquestra tudo
├── scraper/linkedin.py      # coleta via endpoint público do LinkedIn
├── services/notifier.py     # envia resumo via CallMeBot (WhatsApp)
├── utils/filters.py         # filtro de nível/local + cache anti-duplicata
├── data/cache.json          # IDs de vagas já notificadas
└── .github/workflows/cron.yml
```

## Critério de filtro (como o bot decide o que é "júnior" ou "relevante")

**Nível:** em vez de adivinhar pelo título da vaga (o que descartava vaga
boa só por não ter a palavra "júnior" escrita), o bot pede o nível
diretamente pro LinkedIn via parâmetro `f_E` — o mesmo filtro que aparece
como checkbox na busca do site (Estágio / Entry level / Associate). Isso já
vem filtrado na origem. Como segunda checagem, `utils/filters.py` descarta
qualquer título com sinal explícito de vaga sênior/liderança ("sênior",
"especialista", "tech lead", "gerente" etc.) que eventualmente escape do
filtro do LinkedIn — ver `SENIOR_DENYLIST_TERMS`.

**Local:** o bot faz **duas buscas por palavra-chave**, replicando o que
você faria manualmente no site:
1. **Local** — perto de `LOCAL_SEARCH_LOCATION` (Ipatinga por padrão, a
   maior cidade do Vale do Aço), com raio `LOCAL_DISTANCE_MILES` (padrão
   50 milhas ≈ 80km, igual ao filtro "(80 km)" que aparece no seu print).
2. **Remota** — em `SEARCH_LOCATION` (Brasil), usando o filtro nativo de
   trabalho remoto do LinkedIn (`f_WT=2`), não um texto adivinhado depois.

Depois disso ainda passa por um filtro de texto (`LOCATION_TERMS`) como
segunda checagem — ajustável no `.env`.

## Ajustar busca

Edite `.env` (local) ou as *Variables* do GitHub Actions (produção):
- `KEYWORDS`: palavras-chave separadas por vírgula
- `LEVELS`: `estagio,junior,pleno` (convertidos pro `f_E` do LinkedIn)
- `SEARCH_LOCATION`: escopo da busca remota (ex: `Brasil`)
- `LOCAL_SEARCH_LOCATION` / `LOCAL_DISTANCE_MILES`: cidade + raio da busca local
- `LOCATION_TERMS`: termos aceitos no filtro de local pós-coleta

## Diagnóstico

Rode `python debug_scraper.py "palavra-chave"` pra ver exatamente o que o
LinkedIn está devolvendo, sem nenhum filtro. E o log do `main.py` já mostra
o funil completo por execução: quantas vagas cruas, quantas já tinham sido
enviadas, quantas caíram no filtro de nível, de local, e quantas são novas
— com até 5 exemplos de título descartado em cada categoria.
