"""Filtro por nível (estágio/júnior/pleno) e deduplicação de vagas já enviadas."""

import json
import os
import unicodedata

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cache.json")

# Termos (em pt-BR e en) que indicam cada nível no título da vaga
LEVEL_TERMS = {
    "estagio": ["estagio", "estagiario", "intern", "internship", "trainee"],
    "junior": ["junior", "jr", "entry level", "graduate"],
    "pleno": ["pleno", "mid-level", "mid level", "intermediate"],
}


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def matches_level(title: str, levels: list[str]) -> bool:
    """True se o título da vaga bater com algum dos níveis desejados."""
    norm_title = _normalize(title)
    for level in levels:
        for term in LEVEL_TERMS.get(level, [level]):
            if term in norm_title:
                return True
    return False


def matches_location(location: str, allow_remote_only_terms: list[str] | None = None) -> bool:
    """Filtro simples de local: remoto OU cidades do Vale do Aço (MG)."""
    norm_loc = _normalize(location)
    terms = allow_remote_only_terms or [
        "remote", "remoto", "home office",
        "ipatinga", "coronel fabriciano", "timoteo", "santana do paraiso",
        "vale do aco", "minas gerais", " mg",
    ]
    return any(term in norm_loc for term in terms)


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
