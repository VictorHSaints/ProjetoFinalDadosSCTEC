from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent if "__file__" in locals() else Path.cwd()
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def tratar_valores_nulos(df_ind: pd.DataFrame, estrategia_indicadores: str = "manter_setorial") -> pd.DataFrame:
    df_null = df_ind.copy()
    if "DT_REFER" in df_null.columns:
        df_null["DT_REFER"] = pd.to_datetime(df_null["DT_REFER"], errors="coerce").dt.strftime("%Y-%m-%d")

    if "DIVIDA_LIQUIDA_MM" in df_null.columns:
        df_null["DIVIDA_LIQUIDA_MM"] = df_null["DIVIDA_LIQUIDA_MM"].fillna(0.0)

    df_null = df_null.sort_values(["TICKER", "ANO"]).reset_index(drop=True)
    df_null["FLG_DADO_IMPUTADO"] = False

    colunas_metricas = [
        "MARGEM_BRUTA_PCT", "MARGEM_EBIT_PCT", "MARGEM_LIQUIDA_PCT",
        "ROE_PCT", "LIQUIDEZ_CORRENTE"
    ]

    for col in colunas_metricas:
        if col not in df_null.columns:
            continue
        mascara_nulo_original = df_null[col].isna()

        if estrategia_indicadores == "interpolacao_temporal":
            df_null[col] = df_null.groupby("TICKER")[col].transform(
                lambda s: s.interpolate(method="linear").bfill().ffill()
            )
        elif estrategia_indicadores == "manter_setorial":
            mediana_setor = df_null.groupby(["SETOR", "ANO"])[col].transform("median")
            mediana_geral = df_null.groupby("ANO")[col].transform("median")
            df_null[col] = df_null[col].fillna(mediana_setor).fillna(mediana_geral)

        df_null.loc[mascara_nulo_original & df_null[col].notna(), "FLG_DADO_IMPUTADO"] = True

    return df_null


def detectar_e_tratar_outliers(df_ind: pd.DataFrame, colunas_alvo: list = None, fator_iqr: float = 1.5):
    df_out = df_ind.copy()
    if colunas_alvo is None:
        colunas_alvo = ["MARGEM_EBIT_PCT", "MARGEM_LIQUIDA_PCT", "ROE_PCT", "LIQUIDEZ_CORRENTE"]

    relatorio_outliers = []

    for col in colunas_alvo:
        if col not in df_out.columns:
            continue

        serie = df_out[col].dropna()
        q1 = serie.quantile(0.25)
        q3 = serie.quantile(0.75)
        iqr = q3 - q1

        limite_inferior = q1 - (fator_iqr * iqr)
        limite_superior = q3 + (fator_iqr * iqr)
        media = serie.mean()
        desvio = serie.std()

        condicao_iqr = (df_out[col] < limite_inferior) | (df_out[col] > limite_superior)
        z_scores = (df_out[col] - media) / desvio if desvio != 0 else 0
        condicao_z = z_scores.abs() > 2.5

        df_out[f"OUTLIER_{col}"] = condicao_iqr
        df_out[f"{col}_CLIP"] = df_out[col].clip(lower=round(limite_inferior, 2), upper=round(limite_superior, 2))

        casos_extremos = df_out[condicao_iqr | condicao_z]
        for _, row in casos_extremos.iterrows():
            relatorio_outliers.append({
                "INDICADOR": col,
                "TICKER": row["TICKER"],
                "EMPRESA": row["EMPRESA"],
                "ANO": row["ANO"],
                "VALOR_ORIGINAL": round(row[col], 2),
                "LIMITE_INF_IQR": round(limite_inferior, 2),
                "LIMITE_SUP_IQR": round(limite_superior, 2),
                "VALOR_WINSORIZED": round(row[f"{col}_CLIP"], 2),
                "Z_SCORE": round((row[col] - media) / desvio, 2) if desvio != 0 else 0.0
            })

    return df_out, pd.DataFrame(relatorio_outliers)


if __name__ == "__main__":
    caminho_entrada = DATA_PROCESSED_DIR / "cvm_indicadores_linha1_2021_2023.csv"
    if caminho_entrada.exists():
        df_indicadores = pd.read_csv(caminho_entrada)
        df_sem_nulos = tratar_valores_nulos(df_indicadores, estrategia_indicadores="manter_setorial")
        df_final, df_log_outliers = detectar_e_tratar_outliers(df_sem_nulos)

        caminho_saida = DATA_PROCESSED_DIR / "cvm_indicadores_linha1_tratado.csv"
        caminho_outliers = DATA_PROCESSED_DIR / "auditoria_outliers_linha1.csv"

        df_final.to_csv(caminho_saida, index=False, encoding="utf-8-sig")
        df_log_outliers.to_csv(caminho_outliers, index=False, encoding="utf-8-sig")
        print(f"[OK] Base tratada salva em: {caminho_saida.relative_to(BASE_DIR)}")
        print(f"[OK] Relatorio de outliers salvo em: {caminho_outliers.relative_to(BASE_DIR)}")
    else:
        print("Execute primeiro: python notebooks/eda_cvm_linha1.py")
