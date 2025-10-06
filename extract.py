import os
import io
import tempfile
from typing import List
import pandas as pd

# PDFs
import pdfplumber

# Camelot para tabelas em PDFs digitais
import camelot

# Imagens + OCR
import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image

def is_pdf_digital_text(pdf_path: str) -> bool:
    '''Retorna True se o PDF possui texto embutido (não é apenas imagem).'''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:3]:
                txt = page.extract_text() or ""
                if txt.strip():
                    return True
        return False
    except Exception:
        return False

def extract_tables_camelot(pdf_path: str) -> List[pd.DataFrame]:
    '''Tenta extrair tabelas com Camelot nos modos lattice e stream.'''
    tables = []
    try:
        # 1) lattice (linhas visíveis)
        t_lattice = camelot.read_pdf(pdf_path, pages="all", flavor="lattice", strip_text="\n")
        for i in range(t_lattice.n):
            tables.append(t_lattice[i].df)
    except Exception:
        pass

    try:
        # 2) stream (colunas por espaçamento)
        t_stream = camelot.read_pdf(pdf_path, pages="all", flavor="stream", strip_text="\n")
        for i in range(t_stream.n):
            tables.append(t_stream[i].df)
    except Exception:
        pass

    # Limpeza simples: remover tabelas vazias/pequenas
    cleaned = []
    for df in tables:
        if isinstance(df, pd.DataFrame) and df.shape[1] >= 2 and df.shape[0] >= 2:
            # remove headers repetidos em todas as linhas (heurística leve)
            if not df.dropna(how="all").empty:
                cleaned.append(_clean_df(df))
    return cleaned

def extract_tables_pdfplumber(pdf_path: str) -> List[pd.DataFrame]:
    '''Fallback usando pdfplumber: faz uma tentativa de detecção de linhas e retorna tabelas aproximadas.'''
    out = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables(table_settings={"vertical_strategy":"lines", "horizontal_strategy":"lines"})
                for tbl in tables or []:
                    df = pd.DataFrame(tbl)
                    if df.shape[1] >= 2 and df.shape[0] >= 2:
                        out.append(_clean_df(df))
    except Exception:
        pass
    return out

def ocr_extract_tables(img: np.ndarray, lang: str = "por") -> List[pd.DataFrame]:
    '''OCR simplificado: usa Tesseract para extrair texto + caixas e tenta agrupar por linhas e colunas.
    OBS: É heurístico e serve como fallback. Em produção, considere DocTR/Table Transformer.'''
    # pré-processamento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    thr = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,35,11)

    data = pytesseract.image_to_data(thr, lang=lang, output_type=pytesseract.Output.DATAFRAME)
    data = data.dropna(subset=["text"])
    data = data[data["conf"] != -1]

    if data.empty:
        return []

    # Agrupar por linhas (y), tolerância
    data["cy"] = data["top"] + data["height"]/2
    rows = []
    for _, row in data.iterrows():
        placed = False
        for r in rows:
            if abs(r["cy_mean"] - row["cy"]) < 10:  # tolerância entre linhas
                r["items"].append(row)
                r["cy_vals"].append(row["cy"])
                r["cy_mean"] = sum(r["cy_vals"]) / len(r["cy_vals"])
                placed = True
                break
        if not placed:
            rows.append({"items":[row], "cy_vals":[row["cy"]], "cy_mean":row["cy"]})

    # Para cada linha, ordenar por x
    lines = []
    for r in rows:
        items_sorted = sorted(r["items"], key=lambda x: x["left"])
        texts = [str(x["text"]).strip() for x in items_sorted if str(x["text"]).strip()]
        lines.append(texts)

    # Heurística para colunas: separa por múltiplos espaços/tabulação implícita (já ordenado por x)
    max_cols = max(len(l) for l in lines) if lines else 0
    table = []
    for l in lines:
        if not l:
            continue
        row = l + [""]*(max_cols - len(l))
        table.append(row)

    if not table:
        return []

    df = pd.DataFrame(table)
    return [_clean_df(df)]

def images_from_pdf(pdf_path: str) -> List[np.ndarray]:
    '''Converte páginas do PDF em imagens (para OCR).'''
    try:
        images = convert_from_path(pdf_path, dpi=300)
        out = []
        for im in images:
            out.append(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
        return out
    except Exception:
        return []

def extract_tables_from_image_path(path: str, lang: str = "por") -> List[pd.DataFrame]:
    img = cv2.imread(path)
    if img is None:
        return []
    return ocr_extract_tables(img, lang=lang)

def extract_tables_auto(path: str, force_ocr: bool=False, ocr_langs: str="por") -> List[pd.DataFrame]:
    ext = os.path.splitext(path)[-1].lower()
    tables: List[pd.DataFrame] = []

    if ext == ".pdf" and not force_ocr:
        if is_pdf_digital_text(path):
            # Tenta Camelot
            tables = extract_tables_camelot(path)
            if tables:
                return tables
            # Fallback pdfplumber
            tables = extract_tables_pdfplumber(path)
            if tables:
                return tables
        # Caso não tenha texto ou preferiu OCR, cai para OCR
        imgs = images_from_pdf(path)
        out = []
        for im in imgs:
            out.extend(ocr_extract_tables(im, lang=ocr_langs or "por"))
        return out

    elif ext in [".png",".jpg",".jpeg",".tif",".tiff",".bmp"]:
        return extract_tables_from_image_path(path, lang=ocr_langs or "por")

    else:
        return []

def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    # Remove colunas completamente vazias e linhas vazias
    df = df.copy()
    df = df.dropna(how="all", axis=0)
    df = df.dropna(how="all", axis=1)
    df = df.reset_index(drop=True)
    # Tenta promover primeira linha a header se parecer header (heurística: strings não-numéricas)
    if not df.empty:
        first = df.iloc[0]
        def is_non_numeric(x):
            try:
                float(str(x).replace(".","").replace(",","."))
                return False
            except Exception:
                return True
        non_num_ratio = sum(is_non_numeric(x) for x in first) / len(first)
        if non_num_ratio >= 0.5:
            df.columns = [str(c).strip() if c is not None else "" for c in first]
            df = df.iloc[1:].reset_index(drop=True)
    return df
