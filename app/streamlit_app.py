from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from datetime import datetime

import pandas as pd
import streamlit as st

from price_crawler.config import settings
from price_crawler.service import PriceSearchService
from price_crawler.storage import SQLiteRepository

st.set_page_config(
    page_title="price-crawler",
    page_icon="💸",
    layout="wide",
)

_EXPORT_COLUMNS = [
    "queried_at",
    "product_query",
    "product_title",
    "store",
    "price",
    "url",
    "source",
]


@st.cache_resource
def get_repository() -> SQLiteRepository:
    return SQLiteRepository(settings.db_path)


def _on_history_change() -> None:
    if st.session_state.get("history_selectbox", "—") != "—":
        st.session_state.active_view = "Histórico de preços"


def _go_to_history(query: str) -> None:
    st.session_state.history_selectbox = query
    st.session_state.active_view = "Histórico de preços"


def main() -> None:
    repository = get_repository()

    if "active_view" not in st.session_state:
        st.session_state.active_view = "Resultados"
    if "last_results" not in st.session_state:
        st.session_state.last_results = None
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""

    st.title("💸 price-crawler")
    st.caption(
        "Consolidação de ofertas dos comparadores brasileiros (Zoom e Buscapé) "
        "numa base histórica local."
    )

    # ------------------------------------------------------------------ Sidebar
    with st.sidebar:
        st.header("Buscar produto")
        product_name = st.text_input("Produto", placeholder="ex.: iphone 15 128gb")
        max_results = st.slider("Máx. produtos por comparador", 1, 10, 5)
        resolve_redirect = st.checkbox(
            "Resolver redirect até a loja final",
            value=settings.resolve_store_url,
            help="Mais lento, mas garante o link direto ao e-commerce em vez do tracking.",
        )
        run_search = st.button("🔍 Buscar", type="primary", width="stretch")

        st.divider()
        st.header("Histórico")
        previous_queries = repository.list_queries()
        history_query = st.selectbox(
            "Produto já consultado",
            options=["—"] + previous_queries,
            help="Selecione um produto já buscado para ver a evolução de preços.",
            key="history_selectbox",
            on_change=_on_history_change,
        )

    # ------------------------------------------------------------------ Search
    if run_search and product_name.strip():
        service = PriceSearchService(
            repository=repository,
            max_results_per_item=max_results,
            resolve_store_url=resolve_redirect,
        )
        with st.spinner(f"Buscando '{product_name}'... pode levar 1-2 minutos."):
            results = service.search_one(product_name.strip())
        st.session_state.last_results = results
        st.session_state.last_query = product_name.strip()
        st.session_state.active_view = "Resultados"
    elif run_search:
        st.warning("Digite o nome de um produto.")

    view = st.radio(
        "Visualização",
        options=["Resultados", "Histórico de preços"],
        horizontal=True,
        key="active_view",
        label_visibility="collapsed",
    )

    if view == "Resultados":
        _render_results(
            st.session_state.last_results,
            st.session_state.last_query,
            attempted_search=run_search,
            repository=repository,
        )
    else:
        _render_history(repository, history_query)


def _render_results(
    results,
    product_name: str,
    attempted_search: bool,
    repository: SQLiteRepository,
) -> None:
    if results is None:
        if not attempted_search:
            st.info("Digite um produto na sidebar e clique em **Buscar**.")
        return

    if not results:
        history_count = len(repository.query_history(product_name)) if product_name else 0
        if history_count:
            st.warning(
                f"A busca atual não retornou ofertas (possível bloqueio anti-bot "
                f"ou timeout dos comparadores). Mas existem **{history_count} "
                f"registro(s)** anteriores de **{product_name}** no histórico."
            )
            st.button(
                "📈 Ver histórico de preços",
                on_click=_go_to_history,
                args=(product_name,),
            )
        else:
            st.warning("Nenhuma oferta encontrada. Tente reformular a busca.")
        return

    df = pd.DataFrame(
        [
            {
                "Loja": r.store,
                "Preço (R$)": r.price,
                "Fonte": r.source,
                "Produto": r.product_title,
                "Link": r.url,
            }
            for r in results
        ]
    ).sort_values("Preço (R$)")

    lowest = df.iloc[0]
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Menor preço", f"R$ {lowest['Preço (R$)']:.2f}", lowest["Loja"])
    col_b.metric("Ofertas encontradas", len(df))
    col_c.metric("Fontes", df["Fonte"].nunique())

    st.dataframe(
        df,
        column_config={
            "Preço (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Link": st.column_config.LinkColumn("Link"),
        },
        hide_index=True,
        width="stretch",
    )

    _render_export_buttons(results, product_name)


def _render_history(repository: SQLiteRepository, history_query: str) -> None:
    if not history_query or history_query == "—":
        st.info("Selecione um produto na sidebar para ver o histórico.")
        return

    history = repository.query_history(history_query)
    if not history:
        st.info("Sem histórico ainda para este produto.")
        return

    df_hist = pd.DataFrame(history)
    df_hist["queried_at"] = pd.to_datetime(df_hist["queried_at"])

    st.subheader(f"Evolução de preços — {history_query}")
    pivot = df_hist.pivot_table(
        index="queried_at", columns="store", values="price", aggfunc="min"
    )
    st.line_chart(pivot)

    st.subheader("Última cotação por loja")
    latest = pd.DataFrame(repository.latest_per_store(history_query))
    if not latest.empty:
        st.dataframe(
            latest,
            column_config={
                "price": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
                "url": st.column_config.LinkColumn("Link"),
            },
            hide_index=True,
            width="stretch",
        )


def _results_to_csv_str(results) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EXPORT_COLUMNS)
    writer.writeheader()
    for r in results:
        row = asdict(r)
        row["queried_at"] = r.queried_at.isoformat(timespec="seconds")
        writer.writerow(row)
    return buf.getvalue()


def _results_to_json_str(results) -> str:
    payload = []
    for r in results:
        row = asdict(r)
        row["queried_at"] = r.queried_at.isoformat(timespec="seconds")
        payload.append(row)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_export_buttons(results, product_name: str) -> None:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = (product_name or "resultado").replace(" ", "_").lower()

    col1, col2 = st.columns(2)
    col1.download_button(
        "⬇️ Exportar CSV",
        data=_results_to_csv_str(results),
        file_name=f"{safe_name}_{timestamp}.csv",
        mime="text/csv",
        width="stretch",
    )
    col2.download_button(
        "⬇️ Exportar JSON",
        data=_results_to_json_str(results),
        file_name=f"{safe_name}_{timestamp}.json",
        mime="application/json",
        width="stretch",
    )


if __name__ == "__main__":
    main()
