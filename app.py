from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np

from src.charts import (
    plot_evolucao_receita_barras,
    plot_distribuicao_setorial_barras,
    plot_quadrantes_roe_margem,
    plot_boxplot_margem_ebit_setor,
    plot_solvencia_divida_liquidez,
)

st.set_page_config(
    page_title="BI Fundamentalista CVM | Linha 1",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilizacao Dark Minimalista (Preto Obsidiana com detalhes em Azul Cobalto/Aco de saturacao controlada)
st.markdown(
    """
    <style>
        /* Fundo principal e tipografia limpa */
        .stApp {
            background-color: #0b0f17;
            color: #e2e8f0;
        }
        [data-testid="stSidebar"] {
            background-color: #0e1420;
            border-right: 1px solid #1e293b;
        }
        /* Cartoes de KPI (st.metric) com detalhe lateral azul sobrio */
        [data-testid="stMetric"] {
            background-color: #111827;
            border: 1px solid #1e293b;
            border-left: 3px solid #3b82f6;
            border-radius: 8px;
            padding: 14px 18px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        }
        [data-testid="stMetricLabel"] {
            color: #94a3b8 !important;
            font-size: 0.82rem !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        [data-testid="stMetricValue"] {
            color: #f8fafc !important;
            font-variant-numeric: tabular-nums;
            font-weight: 600 !important;
        }
        /* Abas (st.tabs) com destaque azul minimalista */
        [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 1px solid #1e293b;
        }
        [data-baseweb="tab"] {
            background-color: transparent !important;
            color: #94a3b8 !important;
            border-radius: 6px 6px 0 0;
            padding: 10px 18px !important;
            font-weight: 500;
        }
        [aria-selected="true"][data-baseweb="tab"] {
            color: #60a5fa !important;
            border-bottom: 2px solid #3b82f6 !important;
            background-color: rgba(59, 130, 246, 0.08) !important;
        }
        /* Quadro executivo da Piramide Invertida */
        .piramide-card {
            background-color: #111827;
            border: 1px solid #1e293b;
            border-left: 3px solid #2563eb;
            border-radius: 8px;
            padding: 14px 18px;
            margin-bottom: 16px;
            font-size: 0.93rem;
            line-height: 1.55;
            color: #cbd5e1;
        }
        .piramide-titulo {
            color: #60a5fa;
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 8px;
        }
        .tag-etapa {
            color: #93c5fd;
            font-weight: 600;
        }
        hr {
            border-color: #1e293b !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent
CSV_TRATADO_PATH = BASE_DIR / "data" / "processed" / "cvm_indicadores_linha1_tratado.csv"
CSV_PADRAO_PATH = BASE_DIR / "data" / "processed" / "cvm_indicadores_linha1_2021_2023.csv"


@st.cache_data(ttl=3600, show_spinner="Carregando demonstracoes financeiras padronizadas (CVM)...")
def carregar_dados_resiliente() -> tuple[pd.DataFrame, str]:
    try:
        if "connections" in st.secrets and "postgresql" in st.secrets["connections"]:
            conn = st.connection("postgresql", type="sql")
            query = "SELECT * FROM cvm_indicadores_linha1 ORDER BY ticker, ano;"
            df_sql = conn.query(query, ttl=3600)
            if not df_sql.empty:
                df_sql.columns = [c.upper() for c in df_sql.columns]
                return df_sql, "PostgreSQL Cloud (Supabase)"
    except Exception:
        pass

    try:
        if CSV_TRATADO_PATH.exists():
            df_local = pd.read_csv(CSV_TRATADO_PATH)
            return df_local, f"Contingencia Local CSV ({CSV_TRATADO_PATH.name})"
        elif CSV_PADRAO_PATH.exists():
            df_local = pd.read_csv(CSV_PADRAO_PATH)
            return df_local, f"Contingencia Local CSV ({CSV_PADRAO_PATH.name})"
        else:
            st.error(
                "Arquivo de dados processados nao encontrado em `data/processed/`. "
                "Execute primeiro: `python notebooks/eda_cvm_linha1.py` e `python src/etl_cleaning.py`."
            )
            st.stop()
    except Exception as e:
        st.error(f"Erro critico ao carregar base de dados em contingencia: {e}")
        st.stop()


df_base, origem_dados = carregar_dados_resiliente()

LISTA_ANOS = sorted(df_base["ANO"].dropna().unique().astype(int).tolist())
LISTA_SETORES = sorted(df_base["SETOR"].dropna().unique().tolist())
LISTA_TICKERS = sorted(df_base["TICKER"].dropna().unique().tolist())


def inicializar_session_state():
    if "filtro_anos" not in st.session_state:
        st.session_state.filtro_anos = LISTA_ANOS
    if "filtro_setores" not in st.session_state:
        st.session_state.filtro_setores = LISTA_SETORES
    if "filtro_tickers" not in st.session_state:
        st.session_state.filtro_tickers = LISTA_TICKERS
    if "usar_winsorization" not in st.session_state:
        st.session_state.usar_winsorization = True
    if "modo_vis_setorial" not in st.session_state:
        st.session_state.modo_vis_setorial = "Barras Horizontais (Ranking & %)"


def atualizar_tickers_por_setor():
    setores_ativos = st.session_state.filtro_setores
    tickers_permitidos = sorted(
        df_base[df_base["SETOR"].isin(setores_ativos)]["TICKER"].unique().tolist()
    )
    atuais = [t for t in st.session_state.filtro_tickers if t in tickers_permitidos]
    st.session_state.filtro_tickers = atuais if atuais else tickers_permitidos


def resetar_filtros():
    st.session_state.filtro_anos = LISTA_ANOS
    st.session_state.filtro_setores = LISTA_SETORES
    st.session_state.filtro_tickers = LISTA_TICKERS
    st.session_state.usar_winsorization = True
    st.session_state.modo_vis_setorial = "Barras Horizontais (Ranking & %)"


inicializar_session_state()

with st.sidebar:
    st.markdown("### :material/tune: Painel de Controle")
    st.caption(f":material/database: **Fonte Ativa:** {origem_dados}")
    st.button(
        "Resetar Filtros",
        icon=":material/restart_alt:",
        on_click=resetar_filtros,
        use_container_width=True,
        type="primary",
        help="Restaura imediatamente todos os filtros para a selecao completa original."
    )
    st.divider()

    anos_selecionados = st.multiselect(
        ":material/calendar_today: Exercicios Fiscais (DFP)",
        options=LISTA_ANOS,
        key="filtro_anos",
        help="Selecione os anos de referencia (2021 a 2023) das demonstracoes contabeis."
    )

    setores_selecionados = st.multiselect(
        ":material/category: Setores Economicos",
        options=LISTA_SETORES,
        key="filtro_setores",
        on_change=atualizar_tickers_por_setor,
        help="Filtre setores especificos para comparacao de pares."
    )

    tickers_disponiveis = sorted(
        df_base[df_base["SETOR"].isin(setores_selecionados)]["TICKER"].unique().tolist()
    ) if setores_selecionados else LISTA_TICKERS

    tickers_selecionados = st.multiselect(
        ":material/domain: Companhias Listadas (Tickers)",
        options=tickers_disponiveis,
        key="filtro_tickers",
        help="Selecione uma ou mais companhias abertas do universo de 12 empresas."
    )

    usar_clip = st.toggle(
        "Suavizar Outliers (Winsorization IQR)",
        key="usar_winsorization",
        help="Ajusta visualmente valores extremos nos limites interquartis (IQR) no grafico de quadrantes."
    )

if not anos_selecionados or not setores_selecionados or not tickers_selecionados:
    st.warning("Selecione pelo menos um Exercicio Fiscal, um Setor e uma Companhia na barra lateral.", icon=":material/info:")
    st.stop()

df_filtrado = df_base[
    (df_base["ANO"].isin(anos_selecionados))
    & (df_base["SETOR"].isin(setores_selecionados))
    & (df_base["TICKER"].isin(tickers_selecionados))
].copy()

ano_mais_recente = int(max(anos_selecionados))
ano_anterior = ano_mais_recente - 1

st.markdown("## :material/analytics: Inteligencia Fundamentalista & Contabilidade Corporativa (CVM / DFP)")
st.markdown(
    "<span style='color:#94a3b8; font-size:0.95rem;'>"
    "<b>Linha Tematica 1</b> &nbsp;|&nbsp; Avaliacao da saude economico-financeira, rentabilidade operacional, "
    "retorno aos acionistas (ROE) e estrutura de liquidez/endividamento de 12 companhias abertas brasileiras (2021–2023)."
    "</span>",
    unsafe_allow_html=True,
)

df_foco = df_filtrado[df_filtrado["ANO"] == ano_mais_recente]
df_ant = df_base[
    (df_base["ANO"] == ano_anterior)
    & (df_base["SETOR"].isin(setores_selecionados))
    & (df_base["TICKER"].isin(tickers_selecionados))
]

receita_atual = df_foco["RECEITA_LIQUIDA_MM"].sum()
receita_ant = df_ant["RECEITA_LIQUIDA_MM"].sum() if not df_ant.empty else np.nan
delta_receita = ((receita_atual / receita_ant) - 1) * 100 if (pd.notna(receita_ant) and receita_ant > 0) else None

lucro_atual = df_foco["LUCRO_LIQUIDO_MM"].sum()
lucro_ant = df_ant["LUCRO_LIQUIDO_MM"].sum() if not df_ant.empty else np.nan
delta_lucro = ((lucro_atual / lucro_ant) - 1) * 100 if (pd.notna(lucro_ant) and lucro_ant != 0) else None

roe_medio_atual = df_foco["ROE_PCT"].mean()
roe_medio_ant = df_ant["ROE_PCT"].mean() if not df_ant.empty else np.nan
delta_roe = (roe_medio_atual - roe_medio_ant) if pd.notna(roe_medio_ant) else None

liq_media_atual = df_foco["LIQUIDEZ_CORRENTE"].mean()
liq_media_ant = df_ant["LIQUIDEZ_CORRENTE"].mean() if not df_ant.empty else np.nan
delta_liq = (liq_media_atual - liq_media_ant) if pd.notna(liq_media_ant) else None

st.markdown(f"#### :material/monitoring: Indicadores Chave de Desempenho Consolidados ({ano_mais_recente})")
col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

with col_kpi1:
    st.metric(
        label=f"Receita Liquida Total ({ano_mais_recente})",
        value=f"R$ {receita_atual:,.0f} MM",
        delta=f"{delta_receita:+.2f}% vs. {ano_anterior}" if delta_receita is not None else "Sem base anterior",
    )

with col_kpi2:
    st.metric(
        label=f"Lucro Liquido Consolidado ({ano_mais_recente})",
        value=f"R$ {lucro_atual:,.0f} MM",
        delta=f"{delta_lucro:+.2f}% vs. {ano_anterior}" if delta_lucro is not None else "Sem base anterior",
    )

with col_kpi3:
    st.metric(
        label=f"ROE Medio da Carteira ({ano_mais_recente})",
        value=f"{roe_medio_atual:.2f}%" if pd.notna(roe_medio_atual) else "N/D",
        delta=f"{delta_roe:+.2f} p.p. vs. {ano_anterior}" if delta_roe is not None else "Sem base anterior",
    )

with col_kpi4:
    st.metric(
        label=f"Liquidez Corrente Media ({ano_mais_recente})",
        value=f"{liq_media_atual:.2f}x" if pd.notna(liq_media_atual) else "N/D",
        delta=f"{delta_liq:+.2f}x vs. {ano_anterior}" if delta_liq is not None else "Sem base anterior",
    )

st.divider()

aba_receita, aba_rentabilidade, aba_solvencia, aba_dados = st.tabs([
    ":material/bar_chart: 1. Crescimento & Concentracao Setorial",
    ":material/scatter_plot: 2. Eficiencia Operacional & Retorno (ROE)",
    ":material/account_balance: 3. Solvencia, Liquidez & Alavancagem",
    ":material/table_view: 4. Base Analitica, Limitacoes & Exportacao"
])

with aba_receita:
    st.markdown(
        """
        <div class="piramide-card">
            <div class="piramide-titulo">◈ SINTESE EXECUTIVA — PIRAMIDE INVERTIDA (CONTEXTO ➔ INSIGHT ➔ ACAO)</div>
            <div><span class="tag-etapa">▸ Contexto:</span> Entre 2021 e 2023, as companhias brasileiras atravessaram a normalizacao dos precos internacionais de <i>commodities</i> e a desaceleracao do consumo domestico sob juros elevados.</div>
            <div><span class="tag-etapa">▸ Insight:</span> Enquanto empresas industriais de bens de capital (<code>WEGE3</code>) e aviacao (<code>EMBJ3</code>) expandiram consistentemente seu faturamento no trienio, exportadoras de <i>commodities</i> metalicas e petroliferas (<code>VALE3</code>, <code>GGBR4</code>, <code>PETR4</code>) apresentaram acomodacao de receita nominal em 2023 apos o pico historico de 2022.</div>
            <div><span class="tag-etapa">▸ Acao Recomendada:</span> Diversificar a exposicao setorial da carteira para mitigar a alta concentracao de receita em <i>commodities</i> ciclicas.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    escolha_vis = st.radio(
        ":material/view_column: Modo de visualizacao da Participacao Setorial (Grafico 2):",
        options=["Barras Horizontais (Ranking & %)", "Mapa de Arvore (Treemap Setor ➔ Companhia)"],
        horizontal=True,
        key="modo_vis_setorial",
    )
    modo_grafico_2 = "treemap" if "Treemap" in escolha_vis else "barras_horizontais"

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.plotly_chart(plot_evolucao_receita_barras(df_filtrado), use_container_width=True)
    with c2:
        st.plotly_chart(
            plot_distribuicao_setorial_barras(df_filtrado, ano_foco=ano_mais_recente, modo=modo_grafico_2),
            use_container_width=True,
        )

with aba_rentabilidade:
    st.markdown(
        """
        <div class="piramide-card">
            <div class="piramide-titulo">◈ SINTESE EXECUTIVA — PIRAMIDE INVERTIDA (CONTEXTO ➔ INSIGHT ➔ ACAO)</div>
            <div><span class="tag-etapa">▸ Contexto:</span> A conversao de receita em resultado operacional (EBIT) e retorno sobre o capital proprio (ROE) reflete o poder de precificacao e a estrutura de custos de cada setor.</div>
            <div><span class="tag-etapa">▸ Insight:</span> Companhias posicionadas no quadrante superior direito (alta Margem Liquida e alto ROE, como <code>WEGE3</code>, <code>EGIE3</code> e <code>PETR4</code>) demonstram superioridade na remuneracao ao acionista, ao passo que setores intensivos em capital de giro e proteina animal (<code>JBSS3</code>) ou varejo (<code>LREN3</code>) operam com margens operacionais estruturalmente mais estreitas.</div>
            <div><span class="tag-etapa">▸ Acao Recomendada:</span> Priorizar na triagem fundamentalista empresas com Margem EBIT acima da mediana do seu respectivo setor e baixa dispersao interanual.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(plot_quadrantes_roe_margem(df_filtrado, usar_clip=usar_clip), use_container_width=True)
    st.plotly_chart(plot_boxplot_margem_ebit_setor(df_filtrado), use_container_width=True)

with aba_solvencia:
    st.markdown(
        """
        <div class="piramide-card">
            <div class="piramide-titulo">◈ SINTESE EXECUTIVA — PIRAMIDE INVERTIDA (CONTEXTO ➔ INSIGHT ➔ ACAO)</div>
            <div><span class="tag-etapa">▸ Contexto:</span> Em cenarios de aperto monetario (Selic elevada), o monitoramento da Divida Liquida e do indice de Liquidez Corrente (AC / PC) e essencial para prevenir estresse de refinanciamento no curto prazo.</div>
            <div><span class="tag-etapa">▸ Insight:</span> O grafico destaca o limiar prudencial de <b>Liquidez Corrente &lt; 1,5x</b>. Empresas abaixo dessa faixa possuem menor folga financeira de curto prazo para cobrir seus passivos circulantes, enquanto barras verdes representam posicao de <b>Caixa Liquido</b> (disponibilidades superiores a divida bruta, como observado em <code>WEGE3</code> e <code>ABEV3</code>).</div>
            <div><span class="tag-etapa">▸ Acao Recomendada:</span> Monitorar trimestralmente o cronograma de amortizacao das companhias com Liquidez Corrente inferior a <code>1,5x</code> e elevada Divida Liquida nominal.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(plot_solvencia_divida_liquidez(df_filtrado, ano_foco=ano_mais_recente), use_container_width=True)

    st.markdown(f"#### :material/radar: Radar de Atencao: Companhias com Liquidez Corrente < 1,5x ({ano_mais_recente})")
    df_alerta = df_foco[df_foco["LIQUIDEZ_CORRENTE"] < 1.5][
        ["TICKER", "EMPRESA", "SETOR", "LIQUIDEZ_CORRENTE", "DIVIDA_LIQUIDA_MM", "ROE_PCT"]
    ].sort_values("LIQUIDEZ_CORRENTE", ascending=True)

    if not df_alerta.empty:
        st.dataframe(df_alerta, use_container_width=True, hide_index=True)
    else:
        st.success(f"Nenhuma companhia selecionada apresentou Liquidez Corrente abaixo de 1,5x em {ano_mais_recente}.", icon=":material/check_circle:")

with aba_dados:
    st.markdown("#### :material/database: Inspecao e Exportacao da Base Analitica Filtrada")
    col_info, col_dl = st.columns([3, 1])
    with col_info:
        st.caption(f"Exibindo **{len(df_filtrado)} registros** correspondentes aos filtros aplicados na barra lateral.")
    with col_dl:
        csv_bytes = df_filtrado.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="Exportar Dados Filtrados (.CSV)",
            icon=":material/download:",
            data=csv_bytes,
            file_name=f"cvm_indicadores_filtrados_{ano_mais_recente}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary"
        )

    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown(
        """
        #### :material/balance: Rigor Metodologico, Governanca e Limitacoes da Analise
        * **Ausencia de Causalidade Direta:** As relacoes visuais observadas entre porte de receita, estrutura setorial, alavancagem e rentabilidade (ROE) representam **associacoes contabeis e correlacoes empiricas** no recorte de 2021 a 2023. Nao se deve inferir causalidade direta sem modelagem econometrica adicional.
        * **Particularidade Contabil do Setor Bancario (`ITUB4`):** Instituicoes financeiras reportam demonstracoes padronizadas sob o plano de contas COSIF/BACEN, cuja estrutura patrimonial nao segrega Ativo e Passivo Circulante nos mesmos codigos (`1.01` e `2.01`) aplicaveis as companhias industriais.
        """
    )
