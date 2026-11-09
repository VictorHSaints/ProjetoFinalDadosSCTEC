import zipfile
from pathlib import Path
import requests
import pandas as pd
import numpy as np

# 1. CONFIGURACAO DE DIRETORIOS (Uso obrigatorio de caminhos relativos)
BASE_DIR = Path(__file__).resolve().parent.parent if "__file__" in locals() else Path.cwd()
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"

DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# 2. MAPEAMENTO DO UNIVERSO DE EMPRESAS (12 Companhias Sugeridas - Linha 1)
EMPRESAS_ALVO = {
    "07.526.557/0001-00": {"ticker": "ABEV3", "nome": "Ambev", "setor": "Consumo / Bebidas"},
    "02.474.103/0001-19": {"ticker": "EGIE3", "nome": "Engie Brasil", "setor": "Energia Eletrica"},
    "07.689.002/0001-89": {"ticker": "EMBJ3", "nome": "Embraer", "setor": "Bens Industriais / Aviacao"},
    "33.611.500/0001-19": {"ticker": "GGBR4", "nome": "Gerdau", "setor": "Siderurgia e Metalurgia"},
    "60.872.504/0001-23": {"ticker": "ITUB4", "nome": "Itau Unibanco", "setor": "Financeiro / Bancos"},
    "02.916.265/0001-60": {"ticker": "JBSS3", "nome": "JBS", "setor": "Consumo / Alimentos"},
    "89.637.490/0001-45": {"ticker": "KLBN11", "nome": "Klabin", "setor": "Papel e Celulose"},
    "92.754.738/0001-62": {"ticker": "LREN3", "nome": "Lojas Renner", "setor": "Varejo"},
    "33.000.167/0001-01": {"ticker": "PETR4", "nome": "Petrobras", "setor": "Petroleo e Gas"},
    "16.404.287/0001-55": {"ticker": "SUZB3", "nome": "Suzano", "setor": "Papel e Celulose"},
    "33.592.510/0001-54": {"ticker": "VALE3", "nome": "Vale", "setor": "Mineracao"},
    "84.429.695/0001-11": {"ticker": "WEGE3", "nome": "WEG", "setor": "Bens Industriais"}
}

ANOS = [2021, 2022, 2023]
TIPOS_DFP = ["DRE_con", "BPA_con", "BPP_con"]


def baixar_e_extrair_cvm(anos: list, tipos_doc: list) -> pd.DataFrame:
    dfs = []
    url_base = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS"

    for ano in anos:
        zip_url = f"{url_base}/dfp_cia_aberta_{ano}.zip"
        zip_local = DATA_RAW_DIR / f"dfp_cia_aberta_{ano}.zip"

        if not zip_local.exists():
            print(f"[DOWNLOAD] Baixando base CVM do ano {ano}...")
            resposta = requests.get(zip_url, timeout=60)
            resposta.raise_for_status()
            with open(zip_local, "wb") as f:
                f.write(resposta.content)
        else:
            print(f"[CACHE LOCAL] Arquivo de {ano} ja existe em {zip_local.name}.")

        with zipfile.ZipFile(zip_local, "r") as z:
            for tipo in tipos_doc:
                nome_csv = f"dfp_cia_aberta_{tipo}_{ano}.csv"
                if nome_csv in z.namelist():
                    with z.open(nome_csv) as f:
                        df_temp = pd.read_csv(f, sep=";", encoding="latin1", low_memory=False)
                        df_temp = df_temp[df_temp["CNPJ_CIA"].isin(EMPRESAS_ALVO.keys())].copy()
                        df_temp["TIPO_DEMO"] = tipo
                        dfs.append(df_temp)

    return pd.concat(dfs, ignore_index=True)


def limpar_e_padronizar_dfp(df: pd.DataFrame) -> pd.DataFrame:
    df_clean = df.copy()
    df_clean = df_clean[df_clean["ORDEM_EXERC"] == "ÚLTIMO"].copy()

    df_clean["DT_REFER"] = pd.to_datetime(df_clean["DT_REFER"], errors="coerce")
    df_clean["DT_FIM_EXERC"] = pd.to_datetime(df_clean["DT_FIM_EXERC"], errors="coerce")
    df_clean["ANO_EXERC"] = df_clean["DT_REFER"].dt.year
    df_clean = df_clean[df_clean["ANO_EXERC"].isin(ANOS)]

    df_clean["VL_CONTA"] = pd.to_numeric(df_clean["VL_CONTA"], errors="coerce").fillna(0.0)
    df_clean["VL_CONTA_REAIS"] = np.where(
        df_clean["ESCALA_MOEDA"].str.upper() == "MIL",
        df_clean["VL_CONTA"] * 1_000,
        df_clean["VL_CONTA"]
    )
    df_clean["VL_CONTA_MILHOES"] = df_clean["VL_CONTA_REAIS"] / 1_000_000

    df_clean = (
        df_clean.sort_values("VERSAO")
        .drop_duplicates(subset=["CNPJ_CIA", "ANO_EXERC", "TIPO_DEMO", "CD_CONTA"], keep="last")
    )

    df_clean["TICKER"] = df_clean["CNPJ_CIA"].map(lambda x: EMPRESAS_ALVO[x]["ticker"])
    df_clean["EMPRESA"] = df_clean["CNPJ_CIA"].map(lambda x: EMPRESAS_ALVO[x]["nome"])
    df_clean["SETOR"] = df_clean["CNPJ_CIA"].map(lambda x: EMPRESAS_ALVO[x]["setor"])

    return df_clean


def construir_tabela_indicadores(df_clean: pd.DataFrame) -> pd.DataFrame:
    registros = []

    for (ticker, empresa, setor, ano), grupo in df_clean.groupby(["TICKER", "EMPRESA", "SETOR", "ANO_EXERC"]):
        def buscar_valor(codigos_exatos: list, termos_descricao: list = None, tipo_demo: str = None) -> float:
            sub = grupo if tipo_demo is None else grupo[grupo["TIPO_DEMO"] == tipo_demo]
            achado = sub[sub["CD_CONTA"].isin(codigos_exatos)]
            if not achado.empty:
                return achado["VL_CONTA_MILHOES"].iloc[0]
            if termos_descricao:
                padrao = "|".join(termos_descricao)
                achado_desc = sub[sub["DS_CONTA"].str.contains(padrao, case=False, na=False)]
                if not achado_desc.empty:
                    return achado_desc.sort_values("CD_CONTA")["VL_CONTA_MILHOES"].iloc[0]
            return np.nan

        receita_liquida = buscar_valor(["3.01"], ["Receita de Venda", "Receitas da Intermedia"], "DRE_con")
        lucro_bruto     = buscar_valor(["3.03"], ["Resultado Bruto"], "DRE_con")
        ebit            = buscar_valor(["3.05"], ["Resultado Antes do Resultado Financeiro", "Resultado Operacional", "Resultado Antes dos Tributos"], "DRE_con")
        lucro_liquido   = buscar_valor(["3.11"], ["Lucro/Prejuízo Consolidado", "Lucro Líquido"], "DRE_con")

        if ticker == "ITUB4":
            # Instituicoes financeiras seguem o plano COSIF/BACEN sem segregacao em 1.01/2.01 industriais
            ativo_circulante   = np.nan
            passivo_circulante = np.nan
            patrimonio_liquido = buscar_valor(["2.08"], ["Patrimônio Líquido Consolidado"], "BPP_con")
            divida_liquida     = 0.0
        else:
            ativo_circulante   = buscar_valor(["1.01"], ["Ativo Circulante"], "BPA_con")
            caixa_equivalentes = buscar_valor(["1.01.01"], ["Caixa e Equivalentes"], "BPA_con")
            aplic_financeiras  = buscar_valor(["1.01.02"], ["Aplicações Financeiras"], "BPA_con")

            passivo_circulante = buscar_valor(["2.01"], ["Passivo Circulante"], "BPP_con")
            divida_cp          = buscar_valor(["2.01.04"], ["Empréstimos e Financiamentos"], "BPP_con")
            divida_lp          = buscar_valor(["2.02.01"], ["Empréstimos e Financiamentos"], "BPP_con")
            patrimonio_liquido = buscar_valor(["2.03", "2.07"], ["Patrimônio Líquido Consolidado"], "BPP_con")

            divida_bruta = (0 if pd.isna(divida_cp) else divida_cp) + (0 if pd.isna(divida_lp) else divida_lp)
            disponibilidades = (0 if pd.isna(caixa_equivalentes) else caixa_equivalentes) + (0 if pd.isna(aplic_financeiras) else aplic_financeiras)
            divida_liquida = divida_bruta - disponibilidades

        margem_bruta   = (lucro_bruto / receita_liquida * 100) if receita_liquida and receita_liquida != 0 else np.nan
        margem_ebit    = (ebit / receita_liquida * 100) if receita_liquida and receita_liquida != 0 else np.nan
        margem_liquida = (lucro_liquido / receita_liquida * 100) if receita_liquida and receita_liquida != 0 else np.nan
        roe            = (lucro_liquido / patrimonio_liquido * 100) if patrimonio_liquido and patrimonio_liquido > 0 else np.nan
        liquidez_corr  = (ativo_circulante / passivo_circulante) if passivo_circulante and passivo_circulante > 0 else np.nan

        registros.append({
            "TICKER": ticker,
            "EMPRESA": empresa,
            "SETOR": setor,
            "ANO": int(ano),
            "DT_REFER": f"{int(ano)}-12-31",
            "RECEITA_LIQUIDA_MM": round(receita_liquida, 2) if pd.notna(receita_liquida) else np.nan,
            "LUCRO_BRUTO_MM": round(lucro_bruto, 2) if pd.notna(lucro_bruto) else np.nan,
            "EBIT_MM": round(ebit, 2) if pd.notna(ebit) else np.nan,
            "LUCRO_LIQUIDO_MM": round(lucro_liquido, 2) if pd.notna(lucro_liquido) else np.nan,
            "ATIVO_CIRCULANTE_MM": round(ativo_circulante, 2) if pd.notna(ativo_circulante) else np.nan,
            "PASSIVO_CIRCULANTE_MM": round(passivo_circulante, 2) if pd.notna(passivo_circulante) else np.nan,
            "PATRIMONIO_LIQUIDO_MM": round(patrimonio_liquido, 2) if pd.notna(patrimonio_liquido) else np.nan,
            "DIVIDA_LIQUIDA_MM": round(divida_liquida, 2),
            "MARGEM_BRUTA_PCT": round(margem_bruta, 2) if pd.notna(margem_bruta) else np.nan,
            "MARGEM_EBIT_PCT": round(margem_ebit, 2) if pd.notna(margem_ebit) else np.nan,
            "MARGEM_LIQUIDA_PCT": round(margem_liquida, 2) if pd.notna(margem_liquida) else np.nan,
            "ROE_PCT": round(roe, 2) if pd.notna(roe) else np.nan,
            "LIQUIDEZ_CORRENTE": round(liquidez_corr, 2) if pd.notna(liquidez_corr) else np.nan,
        })

    return pd.DataFrame(registros)


if __name__ == "__main__":
    print("Iniciando pipeline de Extracao e EDA da Linha 1 (CVM / DFP)...")
    df_bruto = baixar_e_extrair_cvm(ANOS, TIPOS_DFP)
    df_limpo = limpar_e_padronizar_dfp(df_bruto)
    df_indicadores = construir_tabela_indicadores(df_limpo)

    caminho_csv = DATA_PROCESSED_DIR / "cvm_indicadores_linha1_2021_2023.csv"
    df_indicadores.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
    print(f"[SUCESSO] Tabela analitica salva em: {caminho_csv.relative_to(BASE_DIR)}")
