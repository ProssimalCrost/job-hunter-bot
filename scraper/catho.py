"""
Coletor de vagas do Catho.

Confirmado por acesso direto: o Catho NAO tem protecao anti-bot pesada
(sem Cloudflare/DataDome bloqueando) - scraping leve funciona, sem proxy.

Limitacoes conhecidas:
- Nao achei parametro de URL confirmado pra ordenar por "Mais Recentes"
  nem pra filtrar remoto/nivel nativamente. O Catho ordena por
  relevancia por padrao, entao cobrimos so as primeiras MAX_PAGES.
- Filtro de "ultimas 24h" e aproximado: aceita so vagas cujo texto
  contem "hoje" (ex: "Atualizada Hoje"). Vaga de ontem a noite pode
  ficar de fora.
- Nome da empresa nao vem limpo (sem ver a estrutura real do HTML) -
  o campo `company` fica como texto bruto ao redor do link.
"""

import re
import time
import random
import unicodedata

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.catho.com.br/vagas"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

REQUEST_DELAY_SECONDS = (2, 4)
MAX_PAGES = 3

JOB_LINK_RE = re.compile(r"^/vagas/[a-z0-9-]+/(\d+)/?$")


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def search_jobs(keyword: str, city: str, state_abbr: str) -> list[dict]:
    """Busca vagas no Catho pra uma cidade+estado especificos.

    Ex: search_jobs("desenvolvedor junior", "Ipatinga", "MG")
    """
    keyword_slug = _slugify(keyword)
    location_slug = f"{_slugify(city)}-{state_abbr.lower()}"

    jobs = []
    seen_ids = set()

    for page in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}/{keyword_slug}/{location_slug}"
        if page > 1:
            url += f"?page={page}"

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
        except requests.RequestException as e:
            print(f"[catho] erro de rede em '{keyword}' pag {page}: {e}")
            break

        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.find_all("a", href=JOB_LINK_RE)
        if not links:
            break

        new_in_page = 0
        for link in links:
            m = JOB_LINK_RE.match(link.get("href", ""))
            if not m:
                continue
            job_id = m.group(1)
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            new_in_page += 1

            title = link.get("title") or link.get_text(strip=True)
            container = link.find_parent("li") or link.find_parent("div") or link
            context_text = container.get_text(" ", strip=True)

            if "hoje" not in context_text.lower():
                continue  # fora da janela aproximada de 24h

            jobs.append({
                "id": job_id,
                "title": title,
                "company": context_text[:120],
                "location": f"{city}, {state_abbr}",
                "link": f"https://www.catho.com.br{link.get('href')}",
            })

        if new_in_page == 0:
            break

        time.sleep(random.uniform(*REQUEST_DELAY_SECONDS))

    return jobs
