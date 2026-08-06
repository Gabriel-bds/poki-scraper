"""Executa a varredura diaria do Poki: atualiza a lista de jogos, detecta lancamentos
novos e grava um snapshot de nota/avaliacoes de cada jogo no banco SQLite."""
import datetime as dt
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from scraper import db
from scraper.game_page import fetch_game_data
from scraper.sitemap import fetch_game_urls

MAX_WORKERS = 8
SITEMAP_RETRIES = 4
SITEMAP_RETRY_WAIT_S = 60


def fetch_game_urls_with_retry():
    """Tenta buscar o sitemap varias vezes, com espera entre tentativas, antes de desistir."""
    for attempt in range(1, SITEMAP_RETRIES + 1):
        try:
            return fetch_game_urls()
        except Exception as exc:
            if attempt == SITEMAP_RETRIES:
                raise
            print(f"  falha ao buscar sitemap (tentativa {attempt}/{SITEMAP_RETRIES}): {exc}")
            print(f"  tentando novamente em {SITEMAP_RETRY_WAIT_S}s...")
            time.sleep(SITEMAP_RETRY_WAIT_S)


def scrape_one(slug, url):
    try:
        data = fetch_game_data(url)
    except Exception as exc:  # rede instavel, 404, etc. -- nao deve derrubar o job inteiro
        return slug, url, None, str(exc)
    return slug, url, data, None


def main():
    today = dt.date.today().isoformat()
    print(f"[{today}] Buscando lista de jogos no sitemap...")
    games = fetch_game_urls_with_retry()
    print(f"[{today}] {len(games)} jogos encontrados no sitemap.")

    conn = db.get_connection()
    db.init_db(conn)

    new_games = []
    errors = []
    processed = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(scrape_one, slug, url) for slug, url in games]
        for future in as_completed(futures):
            slug, url, data, error = future.result()
            processed += 1

            if error or not data:
                errors.append((slug, error or "sem JSON-LD"))
                continue

            is_new = db.upsert_game(
                conn,
                slug=slug,
                name=data["name"],
                studio=data["studio"],
                category=data["category"],
                url=url,
                published_date=data["published_date"],
                today=today,
            )
            if data["rating_value"] is not None or data["rating_count"] is not None:
                db.insert_snapshot(
                    conn,
                    slug=slug,
                    snapshot_date=today,
                    rating_value=data["rating_value"],
                    rating_count=data["rating_count"],
                )
            if is_new:
                new_games.append((slug, data["name"], data["published_date"]))

            if processed % 100 == 0:
                print(f"  ...{processed}/{len(games)} processados")

    conn.commit()
    conn.close()

    elapsed = time.time() - start
    print(f"\n[{today}] Concluido em {elapsed:.0f}s. {len(games) - len(errors)} jogos atualizados, {len(errors)} falharam.")

    if new_games:
        print(f"\n{len(new_games)} jogo(s) novo(s) detectado(s) hoje ({today}):")
        for slug, name, published_date in new_games:
            print(f"  - {name or slug}  (declarado como lancado em: {published_date or 'desconhecido'})")
    else:
        print("\nNenhum jogo novo detectado hoje.")

    if errors:
        print(f"\n{len(errors)} jogo(s) falharam ao processar (primeiros 10):", file=sys.stderr)
        for slug, error in errors[:10]:
            print(f"  - {slug}: {error}", file=sys.stderr)


if __name__ == "__main__":
    main()
