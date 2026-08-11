import os
import time
import random

from dotenv import load_dotenv

from scraper.linkedin import search_jobs
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


def run() -> None:
    sent_ids = load_sent_ids()
    new_jobs = []

    for keyword in KEYWORDS:
        print(f"[main] buscando: {keyword}")
        results = search_jobs(keyword, SEARCH_LOCATION, hours=24)

        for job in results:
            if job["id"] in sent_ids:
                continue
            if not matches_level(job["title"], LEVELS):
                continue
            if not matches_location(job["location"]):
                continue

            new_jobs.append(job)
            sent_ids.add(job["id"])

        time.sleep(random.uniform(2, 4))  # respiro entre keywords

    print(f"[main] {len(new_jobs)} vaga(s) nova(s) após filtro")

    if new_jobs:
        send_whatsapp_digest(new_jobs)

    save_sent_ids(sent_ids)


if __name__ == "__main__":
    run()
