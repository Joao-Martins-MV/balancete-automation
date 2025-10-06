import yaml
import pandas as pd
from rapidfuzz import process, fuzz

def load_mapping_rules(path: str="mapping_rules.yaml"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def apply_normalization(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    '''Aplica regras simples de normalização: renomeia colunas por sinônimos,
    tenta mapear "Conta/Descrição" para um nome padrão via fuzzy matching (opcional).'''
    df = df.copy()
    if not rules:
        return df

    # Renomear colunas por sinônimos
    col_map = {}
    synonyms = rules.get("column_synonyms", {})
    for std_name, alts in synonyms.items():
        for c in df.columns:
            if str(c).strip().lower() == std_name.lower() or str(c).strip().lower() in [a.lower() for a in alts]:
                col_map[c] = std_name
    if col_map:
        df = df.rename(columns=col_map)

    # Fuzzy matching para 'Conta' -> 'Conta_Padrao'
    account_col = rules.get("account_source_column", None)  # ex: "Conta" ou "Descrição"
    target_dict = rules.get("account_dictionary", {})       # ex: {"Caixa": ["Caixa","Caixa Geral","Disponibilidades"], ...}

    if account_col and account_col in df.columns and target_dict:
        expanded = []
        for k, alt_list in target_dict.items():
            expanded.append(k)
            expanded.extend(alt_list or [])

        def best_match(x):
            if not isinstance(x, str): 
                return None
            cand, score, _ = process.extractOne(x, expanded, scorer=fuzz.WRatio)
            # Recupera a chave principal (se o match foi em um sinônimo)
            for k, alt_list in target_dict.items():
                if cand == k or cand in (alt_list or []):
                    return k
            return cand if score >= 80 else None

        df["Conta_Padrao"] = df[account_col].astype(str).map(best_match)

    return df
