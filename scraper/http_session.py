"""Sessao HTTP compartilhada com retry automatico para falhas de rede/SSL transitorias."""
import requests
from urllib3.util.retry import Retry

_session = None


def get_session():
    """Retorna uma requests.Session com retry (backoff exponencial) em erros de conexao/SSL."""
    global _session
    if _session is None:
        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _session = session
    return _session
