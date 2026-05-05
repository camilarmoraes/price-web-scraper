from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from price_crawler.config import settings
from price_crawler.service import PriceSearchService
from price_crawler.storage import SQLiteRepository, to_csv, to_json

st.set_page_config(
    page_title="price-crawler",
    page_icon="💸",
    layout="wide",
)


@st.cache_resource
def get_repository() -> SQLiteRepository:
    return SQLiteRepository(settings.db_path)


def main() -> None:
    repository = get_repository()

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
        run_search = st.button("🔍 Buscar", type="primary", width='stretch')

        st.divider()
        st.header("Histórico")
        previous_queries = repository.list_queries()
        history_query = st.selectbox(
            "Produto já consultado",
            options=["—"] + previous_queries,
            help="Selecione um produto já buscado para ver a evolução de preços.",
        )

    tab_results, tab_history = st.tabs(["Resultados", "Histórico de preços"])

    # ------------------------------------------------------------------ Search
    with tab_results:
        if run_search and product_name.strip():
            service = PriceSearchService(
                repository=repository,
                max_results_per_item=max_results,
                resolve_store_url=resolve_redirect,
            )
            with st.spinner(f"Buscando '{product_name}'... pode levar 1-2 minutos."):
                results = service.search_one(product_name.strip())

            if not results:
                st.warning("Nenhuma oferta encontrada. Tente reformular a busca.")
            else:
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
                    width='stretch',
                )

                _render_export_buttons(results, product_name)
        elif run_search:
            st.warning("Digite o nome de um produto.")
        else:
            st.info("Digite um produto na sidebar e clique em **Buscar**.")

    # ------------------------------------------------------------------ History
    with tab_history:
        if history_query and history_query != "—":
            history = repository.query_history(history_query)
            if not history:
                st.info("Sem histórico ainda para este produto.")
            else:
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
                        width='stretch',
                    )
        else:
            st.info("Selecione um produto na sidebar para ver o histórico.")


def _render_export_buttons(results, product_name: str) -> None:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = product_name.replace(" ", "_").lower()
    exports_dir = Path("exports")

    col1, col2 = st.columns(2)
    if col1.button("⬇️ Exportar CSV"):
        path = to_csv(results, exports_dir / f"{safe_name}_{timestamp}.csv")
        st.success(f"CSV salvo em `{path}`")
    if col2.button("⬇️ Exportar JSON"):
        path = to_json(results, exports_dir / f"{safe_name}_{timestamp}.json")
        st.success(f"JSON salvo em `{path}`")


if __name__ == "__main__":
    main()
