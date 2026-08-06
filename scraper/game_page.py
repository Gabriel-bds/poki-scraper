"""Extrai os dados de um jogo (nome, estudio, categoria, nota, avaliacoes, data de lancamento)
a partir do bloco JSON-LD embutido na pagina do jogo -- nao precisa de navegador/JS."""
import json
import re

from scraper.http_session import get_session

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PokiRatingsTracker/1.0)"}
JSON_LD_RE = re.compile(
    r'<script type="application/ld\+json" id="game-json-ld">(.*?)</script>', re.S
)


def _find_first(obj, key):
    """Busca recursivamente a primeira ocorrencia de `key` em um dict/list aninhado."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = _find_first(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_first(item, key)
            if found is not None:
                return found
    return None


def parse_game_html(html):
    """Recebe o HTML da pagina do jogo e retorna um dict com os campos extraidos, ou None."""
    match = JSON_LD_RE.search(html)
    if not match:
        return None

    data = json.loads(match.group(1))
    main_entity = _find_first(data, "mainEntity") or {}
    aggregate_rating = _find_first(main_entity, "aggregateRating") or {}
    # breadcrumb fica no nivel da ItemPage, nao dentro de mainEntity
    breadcrumb_items = _find_first(data, "itemListElement") or []
    author = _find_first(main_entity, "author") or {}

    category = None
    if breadcrumb_items:
        last_crumb = breadcrumb_items[-1]
        category = (last_crumb.get("item") or {}).get("name")

    return {
        "name": main_entity.get("name"),
        "studio": author.get("name"),
        "category": category,
        "published_date": main_entity.get("datePublished"),
        "rating_value": aggregate_rating.get("ratingValue"),
        "rating_count": aggregate_rating.get("ratingCount"),
    }


def fetch_game_data(url, timeout=20):
    """Baixa a pagina do jogo e retorna os dados extraidos (ou None se nao encontrar o JSON-LD)."""
    resp = get_session().get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return parse_game_html(resp.text)
