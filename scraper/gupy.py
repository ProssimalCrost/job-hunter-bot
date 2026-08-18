"""
Coletor de vagas do Gupy - por empresa (subdominio), nao busca ampla.

Cada empresa que usa Gupy tem pagina propria em https://<empresa>.gupy.io/
- confirmado por acesso direto (Usiminas), sem proxy/login necessario.

Nao ha busca entre-empresas confiavel que eu tenha verificado, entao a
lista de empresas e manual (GUPY_COMPANIES no .env). Pra descobrir se uma
empresa usa Gupy: tente abrir https://<nome>.gupy.io/ no navegador.

Limitacoes conhecidas:
- O texto da vaga (titulo/cidade/tipo) vem concatenado sem separador
  confiavel no HTML publico - por isso o campo `title` aqui inclui tudo
  junto. Funciona bem pro filtro de nivel/local/tema (busca de texto),
  mas fica menos "limpo" na mensagem do WhatsApp. O link sempre esta
  correto.
- Nao ha filtro nativo de "ultimas 24h" confirmado - mostra todas as
  vagas abertas no momento, nao so as novas.
"""

import re

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

JOB_LINK_RE = re.compile(r"^/jobs/(\d+)")


def search_jobs(company_subdomain: str) -> list[dict]:
    """Busca todas as vagas abertas de uma empresa no Gupy."""
    url = f"https://{company_subdomain}.gupy.io/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        print(f"[gupy] erro de rede em '{company_subdomain}': {e}")
        return []

    if resp.status_code != 200:
        print(f"[gupy] '{company_subdomain}' respondeu {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []
    seen_ids = set()

    for link in soup.find_all("a", href=JOB_LINK_RE):
        m = JOB_LINK_RE.match(link.get("href", ""))
        job_id = m.group(1)
        if job_id in seen_ids:
            continue
        seen_ids.add(job_id)

        text = link.get_text(" ", strip=True)
        jobs.append({
            "id": job_id,
            "title": text,
            "company": company_subdomain,
            "location": text,
            "link": f"https://{company_subdomain}.gupy.io{link.get('href')}",
        })

    return jobs
