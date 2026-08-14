import os
import time
import random

from dotenv import load_dotenv

from scraper.linkedin import search_jobs as search_linkedin
from utils.filters import (
    experience_level_codes,
    is_senior_title,
    matches_location,
    load_sent_ids,
    save_sent_ids,
)
from services.notifier import send_whatsapp_digest

load_dotenv()


def env_str(name: str, default: str) -> str:
    """os.getenv, mas tratando string vazia como ausente.

    Necessário porque o GitHub Actions substitui `${{ vars.X }}` por string
    VAZIA quando a Variable não está definida — o default do os.getenv não
    entra em ação nesse caso.
    """
    value = os.getenv(name, "")
    return value.strip() if value.strip() else default


def env_list(name: str, default: str) -> list[str]:
    """Lê variável separada por vírgula, ignorando itens vazios."""
    return [item.strip() for item in env_str(name, default).split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    """Lê variável numérica, caindo no default se vazia ou inválida."""
    raw = env_str(name, str(default))
    try:
        return int(raw)
    except ValueError:
        print(f"[main] aviso: {name}='{raw}' não é número; usando {default}")
        return default

KEYWORDS = env_list(
    "KEYWORDS", "JavaScript,TypeScript,Node.js,Spring Boot,.NET"
)

# Engenharia Elétrica — mesmos níveis (f_E) e mesmas condições de local
# (raio local + remoto nacional) das keywords de TI acima.
KEYWORDS_ELETRICA = env_list(
    "KEYWORDS_ELETRICA",
    "Engenharia Elétrica,Engenheiro Eletricista,Automação Industrial,"
    "Elétrica Industrial,Manutenção Elétrica,Projetos Elétricos"
)

ALL_KEYWORDS = KEYWORDS + KEYWORDS_ELETRICA

LEVELS = [l.lower() for l in env_list("LEVELS", "estagio,junior,pleno")]

SEARCH_LOCATION = env_str("SEARCH_LOCATION", "Brasil")  # escopo da busca remota

# Cidade de referência pra busca local com raio (Ipatinga é a maior cidade
# do Vale do Aço, colada em Timóteo — ajuste se quiser outra referência).
LOCAL_SEARCH_LOCATION = env_str("LOCAL_SEARCH_LOCATION", "Ipatinga, Minas Gerais, Brasil")
LOCAL_DISTANCE_MILES = env_int("LOCAL_DISTANCE_MILES", 50)  # ~80km

LOCATION_TERMS = env_list(
    "LOCATION_TERMS",
    "remote,remoto,home office,brasil,ipatinga,coronel fabriciano,"
    "timoteo,santana do paraiso,vale do aco,minas gerais,mg"
)
FE_CODES = experience_level_codes(LEVELS)  # filtro nativo do LinkedIn


def collect_from_linkedin() -> list[dict]:
    """Coleta vagas cruas do LinkedIn com DUAS buscas por keyword, iguais ao
    que você faria manualmente: uma local (perto de Timóteo, com raio) e
    outra remota (em qualquer lugar do Brasil, via filtro nativo f_WT=2).
    """
    raw = []
    seen_ids = set()

    for keyword in ALL_KEYWORDS:
        area = "Elétrica" if keyword in KEYWORDS_ELETRICA else "TI"
        local = search_linkedin(
            keyword, LOCAL_SEARCH_LOCATION, hours=24,
            experience_levels=FE_CODES, distance=LOCAL_DISTANCE_MILES,
        )
        time.sleep(random.uniform(1.5, 2.5))
        remote = search_linkedin(
            keyword, SEARCH_LOCATION, hours=24,
            experience_levels=FE_CODES, workplace_types=["2"],
        )
        print(
            f"[main] LinkedIn / [{area}] '{keyword}': {len(local)} local(is) "
            f"(raio {LOCAL_DISTANCE_MILES}mi de {LOCAL_SEARCH_LOCATION}) + "
            f"{len(remote)} remoto(s) nacional"
        )

        for job in local + remote:
            if job["id"] in seen_ids:
                continue  # pode repetir entre as duas buscas
            seen_ids.add(job["id"])
            job["source"] = "LinkedIn"
            job["area"] = area
            job["id"] = f"linkedin:{job['id']}"  # namespace pra não colidir com outras fontes
            raw.append(job)

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
    examples = {"nivel": [], "local": []}  # amostra do que foi descartado, pra debug

    for collector in COLLECTORS:
        raw_jobs = collector()
        stats["cru"] += len(raw_jobs)

        for job in raw_jobs:
            if job["id"] in sent_ids:
                stats["ja_enviada"] += 1
                continue
            # nível já veio filtrado pelo f_E do LinkedIn; aqui só barramos
            # sinal explícito de senioridade que tenha escapado (denylist)
            if is_senior_title(job["title"]):
                stats["nivel"] += 1
                if len(examples["nivel"]) < 5:
                    examples["nivel"].append(f"{job['title']} — {job['location']}")
                continue
            if not matches_location(job["location"], LOCATION_TERMS):
                stats["local"] += 1
                if len(examples["local"]) < 5:
                    examples["local"].append(f"{job['title']} — {job['location']}")
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
    if examples["nivel"]:
        print("[main] exemplos descartados por nível (denylist sênior):")
        for ex in examples["nivel"]:
            print(f"    - {ex}")
    if examples["local"]:
        print("[main] exemplos descartados por local:")
        for ex in examples["local"]:
            print(f"    - {ex}")

    if new_jobs:
        send_whatsapp_digest(new_jobs)

    save_sent_ids(sent_ids)


if __name__ == "__main__":
    run()
