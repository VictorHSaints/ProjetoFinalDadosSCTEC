from pathlib import Path
import tomllib
import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_TRATADO = BASE_DIR / "data" / "processed" / "cvm_indicadores_linha1_tratado.csv"
SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"


def carregar_csv_para_supabase():
    if not SECRETS_PATH.exists():
        raise FileNotFoundError("Arquivo .streamlit/secrets.toml nao encontrado.")
    if not CSV_TRATADO.exists():
        raise FileNotFoundError("Execute o pipeline ETL antes de enviar ao banco.")

    with open(SECRETS_PATH, "rb") as f:
        secrets = tomllib.load(f)

    pg = secrets["connections"]["postgresql"]
    url_db = (
        f"postgresql+psycopg2://{pg['username']}:{pg['password']}"
        f"@{pg['host']}:{pg['port']}/{pg['database']}"
    )

    df = pd.read_csv(CSV_TRATADO)
    df.columns = [c.lower() for c in df.columns]

    engine = create_engine(url_db)
    with engine.begin() as conn:
        df.to_sql("cvm_indicadores_linha1", con=conn, if_exists="replace", index=False)
        res = conn.execute(text("SELECT COUNT(*) FROM cvm_indicadores_linha1;")).scalar()
        print(f"[SUCESSO SUPABASE] Tabela 'cvm_indicadores_linha1' criada com {res} registros!")


if __name__ == "__main__":
    carregar_csv_para_supabase()
