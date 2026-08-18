# Job Hunter Bot

Coleta vagas de TI e Engenharia Elétrica (últimas 24h, quando a fonte
permite) por palavra-chave, filtra por nível (estágio/júnior/pleno),
assunto e localização (remoto ou Vale do Aço/MG), e manda um resumo por
WhatsApp — sem Twilio, usando o CallMeBot (gratuito).

## Fontes de dados

| Fonte | Como funciona | Anti-bot? |
|---|---|---|
| LinkedIn | Endpoint público `jobs-guest`, sem login | Não, scraping leve funciona |
| Catho | Busca por URL (`/vagas/{keyword}/{cidade-uf}`), sem login | Não, testado direto |
| Gupy | Página de carreira por empresa (`<empresa>.gupy.io`), sem login | Não, testado direto |
| Indeed / Glassdoor | — | **Sim, pesado (Cloudflare/DataDome)** — não implementado de propósito, ver abaixo |

**Indeed e Glassdoor não têm API pública e bloqueiam scraping leve** — só
cedem com proxy residencial + navegador automatizado disfarçado + contorno
de captcha, que é ativamente furar um sistema de segurança, não uma
diferença de dificuldade técnica. Por isso essas duas não foram
implementadas.

**Sobre scraping em geral:** são endpoints não-oficiais, sem contrato de
suporte — podem mudar de estrutura ou ficar mais restritos sem aviso. O
código já inclui delays entre requisições — não remova isso.

### Gupy é por empresa, não busca ampla

Diferente do LinkedIn/Catho, não existe uma busca confiável entre todas as
empresas do Gupy ao mesmo tempo — por isso a lista de empresas é manual
(`GUPY_COMPANIES` no `.env`, já vem com `usiminas`). Pra adicionar outra
empresa, tente abrir `https://<nome>.gupy.io/` no navegador; se carregar,
adicione o nome à lista.

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
   - `KEYWORDS`, `KEYWORDS_ELETRICA`, `LEVELS`, `SEARCH_LOCATION`,
     `LOCAL_SEARCH_LOCATION`, `LOCAL_DISTANCE_MILES`, `LOCAL_CITY`,
     `LOCAL_STATE_ABBR`, `GUPY_COMPANIES`, `LOCATION_TERMS`
4. Pronto — o workflow já roda sozinho a cada hora. Pra testar sem esperar,
   use o botão "Run workflow" na aba Actions.

Repositório **privado**: o plano free do GitHub dá 2.000 minutos/mês de
Actions, de sobra pra rodar isso de hora em hora. Repositório **público**:
minutos ilimitados.

## Estrutura

```
job-hunter-bot/
├── main.py                  # orquestra tudo
├── scraper/linkedin.py      # coleta via endpoint público do LinkedIn
├── scraper/catho.py         # coleta via busca por URL do Catho
├── scraper/gupy.py          # coleta por empresa no Gupy
├── services/notifier.py     # envia resumo via CallMeBot (WhatsApp)
├── utils/filters.py         # filtros de nível/assunto/local + cache
├── data/cache.json          # IDs de vagas já notificadas
└── .github/workflows/cron.yml
```

## Critério de filtro

**Nível:** no LinkedIn, o bot pede o nível diretamente via parâmetro nativo
`f_E` (o mesmo filtro checkbox do site: Estágio/Entry level/Associate) — já
vem filtrado na origem. Catho e Gupy não têm equivalente confirmado, então
passam só pela checagem abaixo.

**Segunda checagem (todas as fontes):** `utils/filters.py` descarta
qualquer título com sinal explícito de vaga sênior/liderança ("sênior",
"especialista", "tech lead", "gerente" etc. — `SENIOR_DENYLIST_TERMS`).

**Assunto (TI/Elétrica):** filtro adicionado depois que o bot mandou vaga
de "Atendente de Balcão" e "Fonoaudiólogo" — o LinkedIn (e provavelmente
outros sites) tem um comportamento de "não achei exato, aqui vai vaga
parecida" quando a região é pequena, e isso vale pra API também, não só
pra tela do site. `matches_domain()` exige que o título tenha alguma
relação plausível com TI ou Elétrica (`TI_ALLOWLIST_TERMS` /
`ELETRICA_ALLOWLIST_TERMS`) antes de aceitar a vaga — mesmo que a fonte já
tenha "confirmado" que era relevante.

**Local:** o bot faz até duas buscas por palavra-chave no LinkedIn (raio
local + remoto nacional via `f_WT=2`); Catho e Gupy só fazem busca local.
Depois disso tudo passa por um filtro de texto (`LOCATION_TERMS`) como
segunda checagem.

O raio local padrão é `LOCAL_DISTANCE_MILES=15` (~24km) em volta de
Ipatinga — cobre Coronel Fabriciano/Timóteo/Santana do Paraíso (mesma
conurbação) mas exclui cidades mais distantes como Itabira (~30km). Ajuste
pra menos se quiser só Ipatinga mesmo, ou pra mais se quiser abranger mais
cidades da região.

## Mensagem do WhatsApp

Agrupada por **área** (TI / Elétrica) **e** por **escopo** (Local /
Remoto), nessa ordem: TI·Local, TI·Remoto, Elétrica·Local, Elétrica·Remoto.
Cada vaga mostra também a fonte (`[LinkedIn]`, `[Catho]`, `[Gupy]`).

## Ajustar busca

Edite `.env` (local) ou as *Variables* do GitHub Actions (produção):
- `KEYWORDS` / `KEYWORDS_ELETRICA`: palavras-chave, separadas por vírgula
- `LEVELS`: `estagio,junior,pleno` (convertidos pro `f_E` do LinkedIn)
- `SEARCH_LOCATION`: escopo da busca remota no LinkedIn (ex: `Brasil`)
- `LOCAL_SEARCH_LOCATION` / `LOCAL_DISTANCE_MILES`: cidade + raio da busca
  local no LinkedIn
- `LOCAL_CITY` / `LOCAL_STATE_ABBR`: cidade + UF da busca local no Catho
  (formato diferente do LinkedIn)
- `GUPY_COMPANIES`: empresas do Gupy a monitorar
- `LOCATION_TERMS`: termos aceitos no filtro de local pós-coleta

⚠️ **Cuidado com o volume:** com LinkedIn (2 buscas/keyword) + Catho (1
busca/keyword) + Gupy (1 busca/empresa), 11 keywords geram bastante
requisição por execução, de hora em hora. Se começar a receber resposta
vazia ou erro de alguma fonte, corte keywords ou rode de 2 em 2 horas
(troque o cron pra `0 */2 * * *` no workflow).

## Diagnóstico

Rode `python debug_scraper.py "palavra-chave"` pra ver o que o LinkedIn
está devolvendo, sem filtro nenhum. O log do `main.py` mostra o funil
completo por execução: quantas vagas cruas, quantas já enviadas antes,
quantas caíram em cada filtro (nível/assunto/local), e quantas são
novas — com até 5 exemplos de título descartado por categoria.
