import os
import time
import random

from dotenv import load_dotenv

from scraper.linkedin import search_jobs as search_linkedin
from utils.filters import (
    matches_level,
    matches_location,
    load_sent_ids,
    save_sent_ids,
)
from services.notifier import send_whatsapp_digest

load_dotenv()

KEYWORDS = [k.strip() for k in os.getenv(
    "KEYWORDS", "JavaScript,TypeScript,Node.js,Spring Boot,.NET"
).split(",")]

LEVELS = [l.strip().lower() for l in os.getenv(
    "LEVELS", "estagio,junior,pleno"
).split(",")]

SEARCH_LOCATION = os.getenv("SEARCH_LOCATION", "Brasil")


def collect_from_linkedin() -> list[dict]:
    """Coleta vagas cruas do LinkedIn (sem filtro de nível/local)."""
    raw = []
    for keyword in KEYWORDS:
        results = search_linkedin(keyword, SEARCH_LOCATION, hours=24)
        print(f"[main] LinkedIn / '{keyword}': {len(results)} vaga(s) crua(s)")
        for job in results:
            job["source"] = "LinkedIn"
            job["id"] = f"linkedin:{job['id']}"  # namespace pra não colidir com outras fontes
        raw.extend(results)
        time.sleep(random.uniform(2, 4))
    return raw


# Lista de coletores ativos. Pra adicionar uma nova fonte (Gupy, etc.),
# escreva um scraper/<fonte>.py com uma função search_jobs() no mesmo
# formato de scraper/linkedin.py, crie um collect_from_<fonte>() aqui do
# mesmo jeito, e adicione ele nesta lista.
COLLECTORS = [collect_from_linkedin]


def run() -> None:
    sent_ids = load_sent_ids()
    new_jobs = []
    stats = {"cru": 0, "ja_enviada": 0, "nivel": 0, "local": 0, "nova": 0}

    for collector in COLLECTORS:
        raw_jobs = collector()
        stats["cru"] += len(raw_jobs)

        for job in raw_jobs:
            if job["id"] in sent_ids:
                stats["ja_enviada"] += 1
                continue
            if not matches_level(job["title"], LEVELS):
                stats["nivel"] += 1
                continue
            if not matches_location(job["location"]):
                stats["local"] += 1
                continue

            new_jobs.append(job)
            sent_ids.add(job["id"])
            stats["nova"] += 1

    print(
        f"[main] resumo: {stats['cru']} coletada(s) | "
        f"{stats['ja_enviada']} já enviada(s) antes | "
        f"{stats['nivel']} descartada(s) por nível | "
        f"{stats['local']} descartada(s) por local | "
        f"{stats['nova']} nova(s)"
    )

    if new_jobs:
        send_whatsapp_digest(new_jobs)

    save_sent_ids(sent_ids)


if __name__ == "__main__":
    run()
