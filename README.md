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

1. Salve **+34 644 59 71 67** nos seus contatos como "CallMeBot".
2. Mande a mensagem: `I allow callmebot to send me messages` pelo WhatsApp.
3. Você recebe um `apikey` de volta — guarde ele.
4. Copie `.env.example` para `.env` e preencha `CALLMEBOT_PHONE` (seu número,
   com DDI, ex: `5531999999999`) e `CALLMEBOT_APIKEY`.

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
   - `KEYWORDS`, `LEVELS`, `SEARCH_LOCATION`
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

## Ajustar busca

Edite `.env` (local) ou as *Variables* do GitHub Actions (produção):
- `KEYWORDS`: palavras-chave separadas por vírgula
- `LEVELS`: `estagio,junior,pleno`
- `SEARCH_LOCATION`: termo enviado ao LinkedIn (ex: `Brasil`)

O filtro de "Vale do Aço" (Ipatinga, Coronel Fabriciano, Timóteo, etc.) e
"remoto" acontece depois, em `utils/filters.py`, comparando com o texto de
localização de cada vaga — ajuste a lista `allow_remote_only_terms` lá se
quiser incluir outras cidades.
