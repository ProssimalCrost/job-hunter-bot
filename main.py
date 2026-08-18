import os
import time
import random

from dotenv import load_dotenv

from scraper.linkedin import search_jobs as search_linkedin
from scraper.catho import search_jobs as search_catho
from scraper.gupy import search_jobs as search_gupy
from utils.filters import (
    experience_level_codes,
    is_senior_title,
    matches_domain,
    matches_location,
    normalize_text,
    load_sent_ids,
    save_sent_ids,
)
from services.notifier import send_whatsapp_digest

load_dotenv()


def env_str(name: str, default: str) -> str:
    """os.getenv, mas tratando string vazia como ausente.

    Necessario porque o GitHub Actions substitui ${{ vars.X }} por string
    VAZIA quando a Variable nao esta definida - o default do os.getenv nao
    entra em acao nesse caso.
    """
    value = os.getenv(name, "")
    return value.strip() if value.strip() else default


def env_list(name: str, default: str) -> list[str]:
    """Le variavel separada por virgula, ignorando itens vazios."""
    return [item.strip() for item in env_str(name, default).split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    """Le variavel numerica, caindo no default se vazia ou invalida."""
    raw = env_str(name, str(default))
    try:
        return int(raw)
    except ValueError:
        print(f"[main] aviso: {name}='{raw}' nao e numero; usando {default}")
        return default


KEYWORDS = env_list(
    "KEYWORDS", "JavaScript,TypeScript,Node.js,Spring Boot,.NET"
)

# Engenharia Eletrica - mesmos niveis (f_E) e mesmas condicoes de local
# (raio local + remoto nacional) das keywords de TI acima.
KEYWORDS_ELETRICA = env_list(
    "KEYWORDS_ELETRICA",
    "Engenharia Eletrica,Engenheiro Eletricista,Automacao Industrial,"
    "Eletrica Industrial,Manutencao Eletrica,Projetos Eletricos"
)

ALL_KEYWORDS = KEYWORDS + KEYWORDS_ELETRICA

LEVELS = [l.lower() for l in env_list("LEVELS", "estagio,junior,pleno")]

SEARCH_LOCATION = env_str("SEARCH_LOCATION", "Brasil")  # escopo da busca remota

# Cidade de referencia pra busca local. Raio reduzido pra ~24km (15mi) -
# cobre Ipatinga + Coronel Fabriciano/Timoteo/Santana do Paraiso (mesma
# conurbacao, a poucos km) mas EXCLUI Itabira (~30km), que estava vazando
# vaga fora da regiao desejada.
LOCAL_SEARCH_LOCATION = env_str("LOCAL_SEARCH_LOCATION", "Ipatinga, Minas Gerais, Brasil")
LOCAL_DISTANCE_MILES = env_int("LOCAL_DISTANCE_MILES", 15)  # ~24km

# Cidade/UF pro Catho (formato diferente do LinkedIn, precisa separado)
LOCAL_CITY = env_str("LOCAL_CITY", "Ipatinga")
LOCAL_STATE_ABBR = env_str("LOCAL_STATE_ABBR", "MG")

# Empresas do Gupy a monitorar (subdominio, ex: "usiminas" de usiminas.gupy.io)
GUPY_COMPANIES = env_list("GUPY_COMPANIES", "usiminas")

LOCATION_TERMS = env_list(
    "LOCATION_TERMS",
    "remote,remoto,home office,brasil,ipatinga,coronel fabriciano,"
    "timoteo,santana do paraiso,vale do aco,minas gerais,mg"
)
FE_CODES = experience_level_codes(LEVELS)  # filtro nativo do LinkedIn


def _area_for(keyword: str) -> str:
    return "Elétrica" if keyword in KEYWORDS_ELETRICA else "TI"


def collect_from_linkedin() -> list[dict]:
    """Coleta vagas cruas do LinkedIn com DUAS buscas por keyword: uma local
    (raio apertado em volta de Ipatinga) e outra remota (Brasil, f_WT=2).
    Marca cada vaga com area (TI/Eletrica) e scope (Local/Remoto).
    """
    raw = []
    seen_ids = set()

    for keyword in ALL_KEYWORDS:
        area = _area_for(keyword)
        local = search_linkedin(
            keyword, LOCAL_SEARCH_LOCATION, hours=24,
            experience_levels=FE_CODES, distance=LOCAL_DISTANCE_MILES,
        )
        local_ids = {j["id"] for j in local}
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
            job["scope"] = "Local" if job["id"] in local_ids else "Remoto"
            job["source"] = "LinkedIn"
            job["area"] = area
            job["id"] = f"linkedin:{job['id']}"  # namespace pra nao colidir com outras fontes
            raw.append(job)

        time.sleep(random.uniform(2, 4))
    return raw


def collect_from_catho() -> list[dict]:
    """Coleta vagas do Catho - so busca local (cidade+estado), o Catho nao
    tem filtro nativo de remoto confirmado. Ver scraper/catho.py.
    """
    raw = []
    for keyword in ALL_KEYWORDS:
        area = _area_for(keyword)
        results = search_catho(keyword, LOCAL_CITY, LOCAL_STATE_ABBR)
        print(
            f"[main] Catho / [{area}] '{keyword}': {len(results)} vaga(s) "
            f"(hoje, {LOCAL_CITY}-{LOCAL_STATE_ABBR})"
        )
        for job in results:
            job["source"] = "Catho"
            job["area"] = area
            job["scope"] = "Local"
            job["id"] = f"catho:{job['id']}"
            raw.append(job)
        time.sleep(random.uniform(2, 4))
    return raw


def collect_from_gupy() -> list[dict]:
    """Coleta vagas do Gupy por empresa (lista todas as vagas abertas da
    empresa). Se o título bater com alguma keyword de TI/Elétrica, marca a
    área certa; senão, marca "TI" como área provisória — o filtro de
    assunto em run() decide se vira Diversas ou é descartada (mesma regra
    das outras fontes). Sem filtro nativo de 24h — ver scraper/gupy.py.
    """
    raw = []
    for company in GUPY_COMPANIES:
        results = search_gupy(company)
        print(f"[main] Gupy / '{company}': {len(results)} vaga(s) aberta(s) no total")
        for job in results:
            title_norm = normalize_text(job["title"])
            matched_kw = next(
                (kw for kw in ALL_KEYWORDS if normalize_text(kw) in title_norm), None
            )
            job["source"] = "Gupy"
            job["area"] = _area_for(matched_kw) if matched_kw else "TI"
            job["scope"] = "Local"  # Gupy aqui é por empresa da região
            job["id"] = f"gupy:{job['id']}"
            raw.append(job)
        time.sleep(random.uniform(2, 4))
    return raw


# Lista de coletores ativos + rótulo de exibição. Pra adicionar uma nova
# fonte, escreva um scraper/<fonte>.py com uma função search_jobs() e um
# collect_from_<fonte>() aqui do mesmo jeito, e adicione ele nesta lista.
COLLECTORS = [
    ("LinkedIn", collect_from_linkedin),
    ("Catho", collect_from_catho),
    ("Gupy", collect_from_gupy),
]


def run() -> None:
    sent_ids = load_sent_ids()
    new_jobs = []
    stats = {"cru": 0, "ja_enviada": 0, "nivel": 0, "tema": 0, "diversas": 0, "local": 0, "nova": 0}
    examples = {"nivel": [], "tema": [], "local": []}  # amostra do descartado, pra debug
    fonte_counts = {}  # pra confirmar que cada fonte está entrando na pesquisa

    for fonte, collector in COLLECTORS:
        raw_jobs = collector()
        stats["cru"] += len(raw_jobs)
        fonte_counts[fonte] = len(raw_jobs)

        for job in raw_jobs:
            if job["id"] in sent_ids:
                stats["ja_enviada"] += 1
                continue
            # nivel ja veio filtrado (f_E no LinkedIn); aqui so barramos
            # sinal explicito de senioridade que tenha escapado (denylist)
            if is_senior_title(job["title"]):
                stats["nivel"] += 1
                if len(examples["nivel"]) < 5:
                    examples["nivel"].append(f"{job['title']} - {job['location']}")
                continue
            # relevancia de assunto: vaga local sem nada a ver com TI/Eletrica
            # (ex: sites devolvendo "parecido" quando nao acham exato numa
            # regiao pequena - foi o que aconteceu com "Atendente de Balcao")
            # nao e descartada, vira "Diversas" — voce pediu pra ver essas
            # tambem, desde que sejam da sua regiao. Vaga REMOTA fora do
            # assunto continua descartada (nao faz sentido pra "diversas
            # da regiao").
            if not matches_domain(job["title"], job.get("area", "TI")):
                if job.get("scope") == "Local":
                    job["area"] = "Diversas"
                    stats["diversas"] += 1
                else:
                    stats["tema"] += 1
                    if len(examples["tema"]) < 5:
                        examples["tema"].append(f"{job['title']} - {job['location']}")
                    continue
            if not matches_location(job["location"], LOCATION_TERMS):
                stats["local"] += 1
                if len(examples["local"]) < 5:
                    examples["local"].append(f"{job['title']} - {job['location']}")
                continue

            new_jobs.append(job)
            sent_ids.add(job["id"])
            stats["nova"] += 1

    print(
        "[main] vagas cruas por fonte: "
        + " | ".join(f"{fonte}={n}" for fonte, n in fonte_counts.items())
    )
    fontes_zeradas = [fonte for fonte, n in fonte_counts.items() if n == 0]
    if fontes_zeradas:
        print(
            f"[main] ⚠️  fonte(s) sem nenhuma vaga crua nesta execução: "
            f"{', '.join(fontes_zeradas)} — pode ser dia parado, ou a fonte "
            f"pode estar bloqueando/mudando estrutura. Vale rodar "
            f"debug_scraper.py ou checar manualmente se voltar zerado por "
            f"várias execuções seguidas."
        )
    print(
        f"[main] resumo: {stats['cru']} coletada(s) | "
        f"{stats['ja_enviada']} ja enviada(s) antes | "
        f"{stats['nivel']} descartada(s) por nivel | "
        f"{stats['tema']} descartada(s) por assunto (remoto fora do tema) | "
        f"{stats['diversas']} reclassificada(s) como Diversas | "
        f"{stats['local']} descartada(s) por local | "
        f"{stats['nova']} nova(s)"
    )
    rotulos = {
        "nivel": "nivel (denylist senior)",
        "tema": "assunto (remoto fora do tema, descartado)",
        "local": "local",
    }
    for categoria, rotulo in rotulos.items():
        if examples[categoria]:
            print(f"[main] exemplos descartados por {rotulo}:")
            for ex in examples[categoria]:
                print(f"    - {ex}")

    if new_jobs:
        send_whatsapp_digest(new_jobs)

    save_sent_ids(sent_ids)


if __name__ == "__main__":
    run()
