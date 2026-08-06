"""Painel visual dos jogos do Poki: busca, notas, avaliações, estúdio, data de lançamento
e histórico de avaliações por jogo.

Rodar com: streamlit run dashboard/app.py
"""
import sqlite3
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ag_grid_locale import AG_GRID_LOCALE_PT_BR

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "poki.db"

st.set_page_config(page_title="Painel de Jogos Poki", layout="wide")


@st.cache_data(ttl=300)
def carregar_jogos():
    conn = sqlite3.connect(DB_PATH)
    query = """
        WITH ranked AS (
            SELECT slug, rating_value, rating_count,
                   ROW_NUMBER() OVER (PARTITION BY slug ORDER BY snapshot_date DESC) AS rn
            FROM snapshots
        )
        SELECT
            g.slug AS "slug",
            g.name AS "Nome",
            g.studio AS "Estúdio",
            g.category AS "Categoria",
            latest.rating_value AS "Nota",
            latest.rating_count AS "Qtd Avaliações",
            (latest.rating_count - previous.rating_count) AS "Novas Avaliações",
            g.published_date AS "Lançamento (declarado)",
            g.first_seen_date AS "Detectado no site em",
            g.last_seen_date AS "Visto pela última vez",
            g.url AS "URL"
        FROM games g
        LEFT JOIN (SELECT slug, rating_value, rating_count FROM ranked WHERE rn = 1) latest
            ON latest.slug = g.slug
        LEFT JOIN (SELECT slug, rating_count FROM ranked WHERE rn = 2) previous
            ON previous.slug = g.slug
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=300)
def carregar_historico(slug):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT snapshot_date AS "Data", rating_value AS "Nota", rating_count AS "Qtd Avaliações"
        FROM snapshots
        WHERE slug = ?
        ORDER BY snapshot_date
        """,
        conn,
        params=(slug,),
    )
    conn.close()
    df["Data"] = pd.to_datetime(df["Data"])
    df["Novas Avaliações"] = df["Qtd Avaliações"].diff()
    return df


def grafico(df, coluna_y, titulo, tipo="linha", eixo_zero=True):
    """Grafico (linha ou barras) com eixo X por dia (sem horas, ja que a coleta e
    diaria) e numeros formatados no padrao brasileiro (ponto de milhar)."""
    label_expr_y = "replace(format(datum.value, ',d'), ',', '.')"
    dados = df.dropna(subset=[coluna_y])

    base = alt.Chart(dados)
    marcador = (
        base.mark_line(point=True, strokeWidth=2, color="#4C78A8")
        if tipo == "linha"
        else base.mark_bar(color="#4C78A8")
    )

    grafico_final = (
        marcador.encode(
            x=alt.X(
                "yearmonthdate(Data):O",
                title="Data",
                axis=alt.Axis(format="%d/%m", labelAngle=0),
            ),
            y=alt.Y(
                f"{coluna_y}:Q",
                title=coluna_y,
                scale=alt.Scale(zero=eixo_zero),
                axis=alt.Axis(labelExpr=label_expr_y),
            ),
            tooltip=[
                alt.Tooltip("Data:T", title="Data", format="%d/%m/%Y"),
                alt.Tooltip(f"{coluna_y}:Q", title=coluna_y, format=",d"),
            ],
        )
        .properties(title=titulo, height=280)
        .configure_axis(gridColor="#eee", domain=False)
        .configure_view(strokeWidth=0)
    )
    return grafico_final


if not DB_PATH.exists():
    st.error(
        "Banco de dados ainda não existe. Rode `python run_daily.py` pelo menos uma vez "
        "antes de abrir o painel."
    )
    st.stop()

df = carregar_jogos()

if df.empty:
    st.warning("O banco de dados existe mas ainda não tem nenhum jogo. Rode `python run_daily.py`.")
    st.stop()

st.title("🎮 Painel de Jogos Poki")

ultima_atualizacao = df["Visto pela última vez"].max()
st.caption(f"{len(df)} jogos monitorados · última atualização: {ultima_atualizacao}")

# --- Novidades recentes ---
data_mais_recente = df["Detectado no site em"].max()
lancamentos_recentes = df[df["Detectado no site em"] == data_mais_recente]
if len(lancamentos_recentes) < len(df):
    with st.expander(
        f"🆕 Jogos detectados pela primeira vez em {data_mais_recente} ({len(lancamentos_recentes)})",
        expanded=True,
    ):
        st.table(
            lancamentos_recentes[["Nome", "Estúdio", "Lançamento (declarado)"]].reset_index(drop=True)
        )
else:
    st.info(
        "Todos os jogos foram detectados na mesma data — isso é esperado na primeira "
        "execução do scraper. A partir da segunda coleta diária, esta seção vai mostrar "
        "só os lançamentos realmente novos."
    )

st.divider()

# --- Busca e tabela geral ---
busca = st.text_input("🔍 Buscar por nome ou estúdio", "")

filtrado = df
if busca:
    filtro = (
        df["Nome"].str.contains(busca, case=False, na=False)
        | df["Estúdio"].str.contains(busca, case=False, na=False)
    )
    filtrado = df[filtro]

filtrado = filtrado.sort_values("Qtd Avaliações", ascending=False, na_position="last").reset_index(drop=True)
filtrado["Lançamento (declarado)"] = filtrado["Lançamento (declarado)"].fillna("")

st.caption("Clique em um jogo na tabela para ver o histórico de nota e avaliações dele.")

colunas_exibidas = [
    "Nome",
    "Estúdio",
    "Categoria",
    "Nota",
    "Qtd Avaliações",
    "Novas Avaliações",
    "Lançamento (declarado)",
    "Detectado no site em",
]

construtor_opcoes = GridOptionsBuilder.from_dataframe(filtrado[["slug"] + colunas_exibidas])
construtor_opcoes.configure_default_column(resizable=True, sortable=True, filter=True)
construtor_opcoes.configure_column("Nota", type=["numericColumn"])
construtor_opcoes.configure_column("Qtd Avaliações", type=["numericColumn"], sort="desc")
construtor_opcoes.configure_column("Novas Avaliações", type=["numericColumn"])
construtor_opcoes.configure_column("slug", hide=True)
construtor_opcoes.configure_selection(selection_mode="single", use_checkbox=False)
opcoes_grade = construtor_opcoes.build()
opcoes_grade["localeText"] = AG_GRID_LOCALE_PT_BR

resposta = AgGrid(
    filtrado[["slug"] + colunas_exibidas],
    gridOptions=opcoes_grade,
    height=600,
    theme="streamlit",
    show_toolbar=False,
    show_search=False,
    show_download_button=False,
    fit_columns_on_grid_load=True,
)

st.caption(f"Mostrando {len(filtrado)} de {len(df)} jogos.")

# --- Histórico do jogo selecionado ---
linhas_selecionadas = resposta.selected_rows

st.divider()

if linhas_selecionadas is None or len(linhas_selecionadas) == 0:
    st.info("Selecione um jogo na tabela acima para ver a evolução histórica dele.")
else:
    jogo = linhas_selecionadas.iloc[0] if isinstance(linhas_selecionadas, pd.DataFrame) else linhas_selecionadas[0]
    st.subheader(f"📈 Histórico — {jogo['Nome']}")
    st.caption(f"Estúdio: {jogo['Estúdio'] or 'desconhecido'}")

    historico = carregar_historico(jogo["slug"])

    if len(historico) < 2:
        st.info(
            "Ainda existe apenas uma coleta registrada para este jogo. A partir da "
            "segunda execução diária do scraper, esta seção vai mostrar a evolução "
            "de avaliações ao longo do tempo."
        )
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.altair_chart(
                grafico(historico, "Qtd Avaliações", "Total de avaliações ao longo do tempo", tipo="linha", eixo_zero=False),
                width="stretch",
            )
        with col2:
            st.altair_chart(
                grafico(historico, "Novas Avaliações", "Novas avaliações por dia", tipo="barras", eixo_zero=True),
                width="stretch",
            )
