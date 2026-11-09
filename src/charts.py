import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Paleta corporativa de saturacao controlada para fundo escuro (foco em legibilidade e contraste harmonico)
MAPA_CORES_SETOR = {
    "Energia Eletrica": "#eab308",          # Ouro suave
    "Petroleo e Gas": "#38bdf8",            # Azul celeste acinzentado
    "Mineracao": "#d97706",                 # Ambar terroso
    "Papel e Celulose": "#34d399",          # Esmeralda suave
    "Consumo / Bebidas": "#f87171",         # Coral suave
    "Siderurgia e Metalurgia": "#94a3b8",   # Prata / Aco
    "Bens Industriais": "#60a5fa",          # Azul cobalto claro
    "Financeiro / Bancos": "#fb923c",       # Laranja ocre
    "Varejo": "#a78bfa",                    # Lavanda suave
    "Consumo / Alimentos": "#2dd4bf",       # Turquesa sobrio
    "Bens Industriais / Aviacao": "#f472b6" # Rosa antigo suave
}

PALETA_CORPORATIVA = list(MAPA_CORES_SETOR.values())

LAYOUT_DARK_BASE = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(17, 24, 39, 0.45)",
    font=dict(family="Inter, Segoe UI, sans-serif", color="#cbd5e1", size=12),
    title_font=dict(family="Inter, Segoe UI, sans-serif", color="#f8fafc", size=15),
)


def _aplicar_estilo_eixos(fig: go.Figure):
    fig.update_xaxes(
        gridcolor="rgba(148, 163, 184, 0.10)",
        zerolinecolor="rgba(148, 163, 184, 0.20)",
        linecolor="rgba(148, 163, 184, 0.20)",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#94a3b8"),
    )
    fig.update_yaxes(
        gridcolor="rgba(148, 163, 184, 0.10)",
        zerolinecolor="rgba(148, 163, 184, 0.20)",
        linecolor="rgba(148, 163, 184, 0.20)",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#94a3b8"),
    )


def plot_evolucao_receita_barras(df: pd.DataFrame) -> go.Figure:
    df_plot = df.copy()
    df_plot["ANO_STR"] = df_plot["ANO"].astype(str)

    ordem_empresas = (
        df_plot.groupby("TICKER")["RECEITA_LIQUIDA_MM"]
        .mean()
        .sort_values(ascending=False)
        .index.tolist()
    )

    fig = px.bar(
        df_plot,
        x="TICKER",
        y="RECEITA_LIQUIDA_MM",
        color="ANO_STR",
        barmode="group",
        category_orders={"TICKER": ordem_empresas, "ANO_STR": ["2021", "2022", "2023"]},
        color_discrete_sequence=["#334155", "#2563eb", "#60a5fa"],
        hover_data={"EMPRESA": True, "SETOR": True, "RECEITA_LIQUIDA_MM": ":,.2f"},
        labels={
            "TICKER": "Companhia (Ticker)",
            "RECEITA_LIQUIDA_MM": "Receita Liquida (R$ Milhoes)",
            "ANO_STR": "Exercicio Fiscal"
        },
        title="<b>1. Evolucao Anual da Receita Liquida por Companhia (2021-2023)</b><br>"
              "<sup>Progressao historica em R$ Milhoes ordenada pelo porte medio de faturamento</sup>"
    )

    fig.update_traces(marker_line_width=0)
    fig.update_layout(
        **LAYOUT_DARK_BASE,
        legend=dict(
            title_text="Exercicio",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        yaxis_tickprefix="R$ ",
        yaxis_ticksuffix=" MM",
        hovermode="x unified",
        margin=dict(t=75, b=40, l=60, r=20)
    )
    _aplicar_estilo_eixos(fig)
    return fig


def plot_distribuicao_setorial_barras(
    df: pd.DataFrame,
    ano_foco: int = None,
    modo: str = "barras_horizontais",
) -> go.Figure:
    df_plot = df.copy()
    if ano_foco is None:
        ano_foco = int(df_plot["ANO"].max())

    df_ano = df_plot[df_plot["ANO"] == ano_foco].copy()
    total_receita = df_ano["RECEITA_LIQUIDA_MM"].sum()

    if modo == "treemap":
        df_ano["PARTICIPACAO_PCT"] = (
            (df_ano["RECEITA_LIQUIDA_MM"] / total_receita * 100) if total_receita > 0 else 0.0
        )
        fig = px.treemap(
            df_ano,
            path=[px.Constant(f"Carteira Consolidada ({ano_foco})"), "SETOR", "TICKER"],
            values="RECEITA_LIQUIDA_MM",
            color="SETOR",
            color_discrete_map=MAPA_CORES_SETOR,
            custom_data=["EMPRESA", "PARTICIPACAO_PCT"],
            title=f"<b>2. Participacao Setorial e por Companhia na Receita Liquida ({ano_foco})</b><br>"
                  "<sup>Mapa de Arvore Hierarquico (Setor ➔ Companhia) proporcional ao faturamento</sup>",
        )
        fig.update_traces(
            textinfo="label+percent root",
            marker=dict(line=dict(width=1.5, color="#0b0f17")),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Receita Liquida: R$ %{value:,.2f} MM<br>"
                "Participacao no Total: %{percentRoot:.1%}<extra></extra>"
            ),
        )
        fig.update_layout(
            **LAYOUT_DARK_BASE,
            margin=dict(t=75, b=20, l=10, r=10),
        )
        return fig

    df_setor = (
        df_ano.groupby("SETOR", as_index=False)
        .agg(
            RECEITA_LIQUIDA_MM=("RECEITA_LIQUIDA_MM", "sum"),
            EMPRESAS=("TICKER", lambda s: ", ".join(sorted(s.unique()))),
            QTD_EMPRESAS=("TICKER", "nunique"),
        )
        .sort_values("RECEITA_LIQUIDA_MM", ascending=True)
    )
    df_setor["PARTICIPACAO_PCT"] = (
        (df_setor["RECEITA_LIQUIDA_MM"] / total_receita * 100) if total_receita > 0 else 0.0
    )
    df_setor["ROTULO_BARRA"] = df_setor.apply(
        lambda r: f" {r['PARTICIPACAO_PCT']:.1f}% (R$ {r['RECEITA_LIQUIDA_MM'] / 1000:,.1f} bi)",
        axis=1,
    )

    fig = px.bar(
        df_setor,
        x="RECEITA_LIQUIDA_MM",
        y="SETOR",
        orientation="h",
        text="ROTULO_BARRA",
        color="PARTICIPACAO_PCT",
        color_continuous_scale=["#1e293b", "#2563eb", "#60a5fa"],
        custom_data=["PARTICIPACAO_PCT", "EMPRESAS", "QTD_EMPRESAS"],
        labels={
            "SETOR": "Setor Economico",
            "RECEITA_LIQUIDA_MM": "Receita Liquida Consolidada (R$ Milhoes)",
            "PARTICIPACAO_PCT": "Participacao (%)",
        },
        title=f"<b>2. Participacao Setorial na Receita Liquida Consolidada ({ano_foco})</b><br>"
              "<sup>Ranking em barras horizontais com participacao percentual (%) e volume em R$ bilhoes</sup>",
    )

    max_val = df_setor["RECEITA_LIQUIDA_MM"].max() if not df_setor.empty else 1.0
    fig.update_traces(
        textposition="outside",
        textfont=dict(color="#e2e8f0", size=11),
        cliponaxis=False,
        marker_line_color="#3b82f6",
        marker_line_width=0.8,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Receita Consolidada: R$ %{x:,.2f} MM<br>"
            "Participacao na Carteira: %{customdata[0]:.2f}%<br>"
            "Companhias (%{customdata[2]}): %{customdata[1]}<extra></extra>"
        ),
    )
    fig.update_layout(
        **LAYOUT_DARK_BASE,
        coloraxis_showscale=False,
        xaxis=dict(
            title="Receita Liquida Consolidada (R$ Milhoes)",
            tickprefix="R$ ",
            ticksuffix=" MM",
            range=[0, max_val * 1.44],
            showgrid=True,
        ),
        yaxis=dict(
            title="",
            categoryorder="total ascending",
        ),
        margin=dict(t=75, b=40, l=10, r=30),
    )
    _aplicar_estilo_eixos(fig)
    return fig


def plot_distribuicao_setorial_donut(
    df: pd.DataFrame,
    ano_foco: int = None,
    modo: str = "barras_horizontais",
) -> go.Figure:
    return plot_distribuicao_setorial_barras(df=df, ano_foco=ano_foco, modo=modo)


def plot_quadrantes_roe_margem(df: pd.DataFrame, usar_clip: bool = True) -> go.Figure:
    df_plot = df.copy()
    col_x = "MARGEM_LIQUIDA_PCT_CLIP" if (usar_clip and "MARGEM_LIQUIDA_PCT_CLIP" in df_plot.columns) else "MARGEM_LIQUIDA_PCT"
    col_y = "ROE_PCT_CLIP" if (usar_clip and "ROE_PCT_CLIP" in df_plot.columns) else "ROE_PCT"

    df_plot["TAMANHO_BOLHA"] = df_plot["RECEITA_LIQUIDA_MM"].clip(lower=100).fillna(100)
    mediana_x = df_plot[col_x].median()
    mediana_y = df_plot[col_y].median()

    fig = px.scatter(
        df_plot,
        x=col_x,
        y=col_y,
        size="TAMANHO_BOLHA",
        color="SETOR",
        text="TICKER",
        hover_name="EMPRESA",
        hover_data={
            "ANO": True,
            "RECEITA_LIQUIDA_MM": ":,.2f",
            "MARGEM_LIQUIDA_PCT": ":.2f",
            "ROE_PCT": ":.2f",
            "TAMANHO_BOLHA": False,
            col_x: False,
            col_y: False
        },
        size_max=45,
        color_discrete_map=MAPA_CORES_SETOR,
        color_discrete_sequence=PALETA_CORPORATIVA,
        labels={
            col_x: "Margem Liquida (%)",
            col_y: "Retorno sobre Patrimonio Liquido - ROE (%)",
            "SETOR": "Setor Economico"
        },
        title="<b>3. Matriz de Rentabilidade: Margem Liquida (%) vs. ROE (%)</b><br>"
              "<sup>Tamanho da bolha proporcional a Receita Liquida | Linhas tracejadas = Medianas da Carteira</sup>"
    )

    fig.update_traces(
        textposition="top center",
        textfont=dict(color="#e2e8f0", size=11),
        marker=dict(opacity=0.85, line=dict(width=1.2, color="#0f172a")),
    )

    if pd.notna(mediana_x):
        fig.add_vline(
            x=mediana_x, line_dash="dash", line_color="#60a5fa",
            annotation_text=f"Mediana Margem ({mediana_x:.1f}%)",
            annotation_position="top left",
            annotation_font_color="#93c5fd",
        )
    if pd.notna(mediana_y):
        fig.add_hline(
            y=mediana_y, line_dash="dash", line_color="#60a5fa",
            annotation_text=f"Mediana ROE ({mediana_y:.1f}%)",
            annotation_position="bottom right",
            annotation_font_color="#93c5fd",
        )

    fig.update_layout(
        **LAYOUT_DARK_BASE,
        xaxis_ticksuffix="%",
        yaxis_ticksuffix="%",
        legend=dict(
            title_text="<b>Setor Economico</b>",
            bgcolor="rgba(17, 24, 39, 0.85)",
            bordercolor="#1e293b",
            borderwidth=1,
        ),
        margin=dict(t=80, b=40, l=60, r=20)
    )
    _aplicar_estilo_eixos(fig)
    return fig


def plot_boxplot_margem_ebit_setor(df: pd.DataFrame) -> go.Figure:
    df_plot = df.dropna(subset=["MARGEM_EBIT_PCT"]).copy()

    ordem_setores = (
        df_plot.groupby("SETOR")["MARGEM_EBIT_PCT"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )

    fig = px.box(
        df_plot,
        x="SETOR",
        y="MARGEM_EBIT_PCT",
        color="SETOR",
        category_orders={"SETOR": ordem_setores},
        points="all",
        hover_name="EMPRESA",
        hover_data={"TICKER": True, "ANO": True, "MARGEM_EBIT_PCT": ":.2f", "SETOR": True},
        color_discrete_map=MAPA_CORES_SETOR,
        color_discrete_sequence=PALETA_CORPORATIVA,
        labels={
            "SETOR": "Setor Economico",
            "MARGEM_EBIT_PCT": "Margem Operacional EBIT (%)"
        },
        title="<b>4. Dispersao da Margem Operacional (EBIT %) por Setor Economico (2021-2023)</b><br>"
              "<sup>Setores ordenados pela mediana operacional | Nomes no eixo X codificados com a cor de cada setor</sup>"
    )

    fig.update_traces(
        width=0.55,
        jitter=0.25,
        pointpos=0,
        marker=dict(size=8, opacity=0.9, line=dict(width=1, color="#0b0f17")),
    )

    ticktext_colorido = [
        f"<span style='color:{MAPA_CORES_SETOR.get(s, '#cbd5e1')}'><b>{s}</b></span>"
        for s in ordem_setores
    ]

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="#f87171",
        annotation_text="Break-even (0%)",
        annotation_font_color="#fca5a5",
    )
    fig.update_layout(
        **LAYOUT_DARK_BASE,
        boxmode="overlay",
        height=520,
        showlegend=False,
        yaxis_ticksuffix="%",
        xaxis=dict(
            title="Setor Economico (ordenado pela mediana de Margem EBIT)",
            tickmode="array",
            tickvals=ordem_setores,
            ticktext=ticktext_colorido,
            tickangle=-20,
        ),
        margin=dict(t=80, b=105, l=60, r=20)
    )
    _aplicar_estilo_eixos(fig)
    return fig


def plot_solvencia_divida_liquidez(df: pd.DataFrame, ano_foco: int = None) -> go.Figure:
    df_plot = df.copy()
    if ano_foco is None:
        ano_foco = int(df_plot["ANO"].max())

    df_ano = df_plot[df_plot["ANO"] == ano_foco].sort_values("DIVIDA_LIQUIDA_MM", ascending=False)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    cores_divida = np.where(df_ano["DIVIDA_LIQUIDA_MM"] >= 0, "#2563eb", "#10b981")
    fig.add_trace(
        go.Bar(
            x=df_ano["TICKER"],
            y=df_ano["DIVIDA_LIQUIDA_MM"],
            name="Divida Liquida (R$ MM)",
            marker_color=cores_divida,
            marker_line_width=0,
            opacity=0.88,
            hovertemplate="<b>%{x}</b><br>Divida Liquida: R$ %{y:,.2f} MM<extra></extra>"
        ),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=df_ano["TICKER"],
            y=df_ano["LIQUIDEZ_CORRENTE"],
            name="Liquidez Corrente (x)",
            mode="lines+markers+text",
            text=df_ano["LIQUIDEZ_CORRENTE"].round(2).astype(str) + "x",
            textposition="top center",
            textfont=dict(color="#93c5fd", size=11),
            line=dict(color="#60a5fa", width=2.5),
            marker=dict(size=9, color="#93c5fd", symbol="diamond", line=dict(width=1, color="#0b0f17")),
            hovertemplate="<b>%{x}</b><br>Liquidez Corrente: %{y:.2f}x<extra></extra>"
        ),
        secondary_y=True
    )

    fig.add_hline(
        y=1.5,
        line_dash="dash",
        line_color="#f87171",
        annotation_text="Limiar Prudencial < 1.5x",
        annotation_position="top right",
        annotation_font_color="#fca5a5",
        secondary_y=True
    )

    fig.update_layout(
        **LAYOUT_DARK_BASE,
        title=f"<b>5. Estrutura de Solvencia ({ano_foco}): Divida Liquida (R$ MM) vs. Liquidez Corrente (x)</b><br>"
              "<sup>Barras verdes indicam Caixa Liquido (Divida Liquida negativa) | Linha tracejada coral = Limiar de 1,5x</sup>",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(t=85, b=40, l=60, r=60)
    )

    _aplicar_estilo_eixos(fig)
    fig.update_yaxes(title_text="Divida Liquida (R$ Milhoes)", tickprefix="R$ ", ticksuffix=" MM", secondary_y=False)
    fig.update_yaxes(title_text="Liquidez Corrente (Indice x)", ticksuffix="x", secondary_y=True, showgrid=False)

    return fig
