import io
import os
import tempfile
from typing import List, Dict, Any

import streamlit as st
import pandas as pd

from src.extract import extract_tables_auto
from src.normalize import apply_normalization, load_mapping_rules
from src.utils import to_xlsx_bytes

st.set_page_config(page_title="Balancete → Tabela", layout="wide")

st.title("⚙️ Balancete → Tabela (Cloud MVP)")
st.caption("Faça upload de um PDF ou imagem, visualize as tabelas extraídas e exporte em CSV/XLSX.")

with st.sidebar:
    st.header("Configurações")
    lang_pt = st.checkbox("Priorizar OCR em Português (pt)", value=True)
    lang_en = st.checkbox("Incluir Inglês (eng) no OCR", value=False)
    use_ocr = st.checkbox("Forçar OCR (mesmo para PDF digital)?", value=False)
    apply_norm = st.checkbox("Aplicar normalização (mapping_rules.yaml)", value=False)

uploaded = st.file_uploader("Envie um PDF ou imagem", type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"])

if uploaded is not None:
    # Salva arquivo temporário
    suffix = os.path.splitext(uploaded.name)[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    st.info(f"Arquivo carregado: **{uploaded.name}**")

    with st.spinner("Extraindo tabelas..."):
        tables: List[pd.DataFrame] = extract_tables_auto(
            tmp_path,
            force_ocr=use_ocr,
            ocr_langs=("por" if lang_pt else "") + ("+eng" if lang_en else "")
        )

    if not tables:
        st.error("Nenhuma tabela encontrada. Tente marcar 'Forçar OCR' ou revisar a qualidade do arquivo.")
    else:
        st.success(f"{len(tables)} tabela(s) detectada(s).")

        # Selecionar tabela
        idx = st.selectbox("Selecione a tabela para pré-visualização", options=list(range(len(tables))), format_func=lambda i: f"Tabela #{i+1}")
        df = tables[idx].copy()

        st.subheader("Pré-visualização (editável)")
        st.caption("Ajuste valores, títulos de colunas e tipos conforme necessário.")
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)

        # Normalização opcional
        if apply_norm:
            rules = load_mapping_rules()
            edited = apply_normalization(edited, rules)
            st.caption("✔️ Normalização aplicada conforme mapping_rules.yaml")

        # Downloads
        st.download_button("⬇️ Baixar CSV (tabela atual)", data=edited.to_csv(index=False).encode("utf-8"), file_name="tabela_balancete.csv", mime="text/csv")

        # Multi-aba XLSX
        # Usa tabelas originais (ou normalizadas?) — aqui salvamos *todas* as tabelas,
        # e a selecionada com as edições do usuário.
        dfs_to_save = []
        for i, t in enumerate(tables):
            if i == idx:
                dfs_to_save.append(("Tabela_%02d" % (i+1), edited))
            else:
                dfs_to_save.append(("Tabela_%02d" % (i+1), t))

        xlsx_bytes = to_xlsx_bytes(dfs_to_save)
        st.download_button("⬇️ Baixar XLSX (todas as tabelas)", data=xlsx_bytes, file_name="balancete_tabelas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.divider()
        with st.expander("Ver amostra das primeiras linhas da(s) outra(s) tabela(s)"):
            for i, t in enumerate(tables):
                if i != idx:
                    st.markdown(f"**Tabela #{i+1}**")
                    st.dataframe(t.head(10), use_container_width=True)
