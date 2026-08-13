"""Filtro por nível (estágio/júnior/pleno) e deduplicação de vagas já enviadas."""

import json
import os
import unicodedata

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cache.json")

# Mapeia nível desejado -> código nativo f_E do LinkedIn.
# 1=Estágio(Internship) 2=Entry level 3=Associate 4=Mid-Senior 5=Director 6=Executive
LEVEL_TO_LINKEDIN_FE = {
    "estagio": "1",
    "junior": "2",
    "pleno": "3",
}

# Denylist: título contendo qualquer um desses termos é descartado, mesmo
# que o LinkedIn já tenha classificado a vaga como júnior/pleno/estágio no
# f_E — serve de segunda checagem contra vaga sênior mal classificada.
# NÃO usamos allowlist (exigir "júnior" no título) porque a maioria das
# vagas reais não escreve o nível no título — só perderíamos vaga boa.
SENIOR_DENYLIST_TERMS = [
    "senior", "sênior", "sr.", "sr ",
    "especialista", "specialist", "staff", "principal",
    "coordenador", "coordinator", "gerente", "manager",
    "head of", "tech lead", "lead ", "arquiteto", "architect",
    "diretor", "director",
]


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def experience_level_codes(levels: list[str]) -> list[str]:
    """Converte níveis desejados (ex: ['estagio','junior']) em códigos f_E."""
    return sorted({LEVEL_TO_LINKEDIN_FE[l] for l in levels if l in LEVEL_TO_LINKEDIN_FE})


def is_senior_title(title: str) -> bool:
    """True se o título contiver sinal claro de vaga sênior/liderança."""
    norm_title = _normalize(title)
    return any(term in norm_title for term in SENIOR_DENYLIST_TERMS)


DEFAULT_LOCATION_TERMS = [
    "remote", "remoto", "home office", "brasil",
    "ipatinga", "coronel fabriciano", "timoteo", "santana do paraiso",
    "vale do aco", "minas gerais", " mg",
]


def matches_location(location: str, terms: list[str] | None = None) -> bool:
    """Filtro simples de local: compara contra uma lista de termos aceitos.

    `terms` normalmente vem do .env (LOCATION_TERMS) via main.py. Se não for
    passado, cai no default acima.
    """
    norm_loc = _normalize(location)
    terms = terms or DEFAULT_LOCATION_TERMS
    return any(_normalize(term) in norm_loc for term in terms)


def load_sent_ids() -> set:
    if not os.path.exists(CACHE_PATH):
        return set()
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()


def save_sent_ids(ids: set) -> None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    # mantém só os últimos 2000 IDs pra não crescer pra sempre
    trimmed = list(ids)[-2000:]
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False, indent=2)
