"""
Coletor de vagas do LinkedIn via endpoint público 'jobs-guest'.

Esse endpoint é o mesmo que o navegador chama quando você pesquisa vagas
no LinkedIn SEM estar logado — por isso não precisa de login/token.

Importante (leia antes de aumentar o volume):
- É um endpoint não-oficial e pode mudar de estrutura a qualquer momento.
- Mantenha os delays entre requisições (variável REQUEST_DELAY_SECONDS).
- Isso foi pensado para uso pessoal e baixo volume (1x/hora, poucas
  keywords). Não é uma solução para coleta em escala.
"""

import time
import random
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

REQUEST_DELAY_SECONDS = (2, 4)  # intervalo aleatório entre páginas/keywords
RESULTS_PER_PAGE = 25
MAX_PAGES_PER_KEYWORD = 4  # 4 * 25 = até 100 vagas por keyword por execução


def _parse_job_card(card) -> dict | None:
    try:
        urn = card.get("data-entity-urn", "")
        job_id = urn.split(":")[-1] if urn else None

        title_el = card.select_one("h3.base-search-card__title")
        company_el = card.select_one("h4.base-search-card__subtitle a")
        location_el = card.select_one("span.job-search-card__location")
        link_el = card.select_one("a.base-card__full-link")
        time_el = card.select_one("time.job-search-card__listdate")

        if not (job_id and title_el and link_el):
            return None

        return {
            "id": job_id,
            "title": title_el.get_text(strip=True),
            "company": company_el.get_text(strip=True) if company_el else "N/A",
            "location": location_el.get_text(strip=True) if location_el else "N/A",
            "link": link_el.get("href", "").split("?")[0],
            "posted_at": time_el.get("datetime", "") if time_el else "",
        }
    except Exception:
        # Um card mal formado não deve derrubar a coleta inteira
        return None


def search_jobs(
    keyword: str,
    location: str,
    hours: int = 24,
    experience_levels: list[str] | None = None,
    workplace_types: list[str] | None = None,
    distance: int | None = None,
) -> list[dict]:
    """Busca vagas do LinkedIn publicadas nas últimas `hours` horas.

    experience_levels: códigos nativos do LinkedIn (f_E), ex: ["1","2","3"]
    para Estágio/Entry level/Associate.
    workplace_types: códigos nativos do LinkedIn (f_WT): "1"=Presencial,
    "2"=Remoto, "3"=Híbrido. Ex: ["2"] pra só vaga remota.
    distance: raio de busca em milhas em torno de `location` (ignorado se
    `location` for um país inteiro).
    """
    jobs = []
    seen_ids = set()

    for page in range(MAX_PAGES_PER_KEYWORD):
        params = {
            "keywords": keyword,
            "location": location,
            "f_TPR": f"r{hours * 3600}",  # janela de tempo em segundos
            "start": page * RESULTS_PER_PAGE,
        }
        if experience_levels:
            params["f_E"] = ",".join(experience_levels)
        if workplace_types:
            params["f_WT"] = ",".join(workplace_types)
        if distance:
            params["distance"] = str(distance)
        url = f"{BASE_URL}?{urlencode(params)}"

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
        except requests.RequestException as e:
            print(f"[scraper] erro de rede em '{keyword}' pág {page}: {e}")
            break

        if resp.status_code != 200 or not resp.text.strip():
            # Página vazia ou LinkedIn devolveu algo diferente de 200:
            # paramos essa keyword em vez de insistir.
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("li div.base-card")
        if not cards:
            break

        new_in_page = 0
        for card in cards:
            job = _parse_job_card(card)
            if job and job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                jobs.append(job)
                new_in_page += 1

        if new_in_page == 0:
            break

        time.sleep(random.uniform(*REQUEST_DELAY_SECONDS))

    return jobs
