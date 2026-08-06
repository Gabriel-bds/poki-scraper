"""Busca a lista de jogos do Poki a partir do sitemap oficial."""
import xml.etree.ElementTree as ET

from scraper.http_session import get_session

SITEMAP_URL = "https://poki.com/en/sitemaps/games.xml"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PokiRatingsTracker/1.0)"}


def fetch_game_urls(timeout=30):
    """Retorna uma lista de (slug, url) para todos os jogos listados no sitemap."""
    resp = get_session().get(SITEMAP_URL, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    games = []
    for url_el in root.findall("sm:url", NS):
        loc_el = url_el.find("sm:loc", NS)
        if loc_el is None or not loc_el.text:
            continue
        url = loc_el.text.strip()
        slug = url.rstrip("/").split("/")[-1]
        games.append((slug, url))
    return games
