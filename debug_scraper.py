"""
Script de diagnóstico: testa o scraper do LinkedIn ISOLADO, sem filtro de
nível/local e sem enviar WhatsApp. Rode isso localmente pra confirmar que a
coleta em si está funcionando antes de desconfiar do resto do pipeline.

Uso:
    python debug_scraper.py "Node.js"
    python debug_scraper.py            # usa a primeira keyword do .env
"""
import sys
import os
from dotenv import load_dotenv

from scraper.linkedin import search_jobs
from utils.filters import experience_level_codes

load_dotenv()


def main():
    keyword = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.getenv("KEYWORDS", "Node.js").split(",")[0].strip()
    )
    location = os.getenv("SEARCH_LOCATION", "Brasil")
    levels = [l.strip().lower() for l in os.getenv("LEVELS", "estagio,junior,pleno").split(",")]
    fe_codes = experience_level_codes(levels)

    print(f"Buscando '{keyword}' em '{location}' (últimas 24h, f_E={fe_codes})...\n")
    jobs = search_jobs(keyword, location, hours=24, experience_levels=fe_codes)

    print(f"Total bruto (sem nenhum filtro): {len(jobs)} vaga(s)\n")
    for job in jobs[:15]:
        print(f"- {job['title']} | {job['company']} | {job['location']}")
        print(f"  {job['link']}\n")

    if len(jobs) > 15:
        print(f"... e mais {len(jobs) - 15} vaga(s)")

    if not jobs:
        print(
            "Nenhuma vaga voltou. Possíveis causas:\n"
            "  1. Genuinamente não há vaga nova pra essa keyword nas últimas 24h.\n"
            "  2. O LinkedIn mudou a estrutura do HTML (classes CSS diferentes) —\n"
            "     nesse caso o parsing em scraper/linkedin.py precisa de ajuste.\n"
            "  3. O request está sendo bloqueado (status != 200) — rode com\n"
            "     mais detalhe: adicione um print(resp.status_code) temporário\n"
            "     dentro de search_jobs() pra confirmar."
        )


if __name__ == "__main__":
    main()
