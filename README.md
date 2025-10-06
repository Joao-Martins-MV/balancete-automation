# Balancete → Tabela (Cloud)
App em Streamlit para transformar **balancetes** em **tabelas (CSV/XLSX)** — com **preview** antes de exportar.

## Funcionalidades (MVP)
- Upload de **PDF ou imagem** (foto/scan).
- Extração automática de tabelas:
  - PDFs digitais: **Camelot** (lattice/stream) + fallback **pdfplumber**.
  - Scans/fotos: **Tesseract OCR** (pt+eng) com heurística simples de linhas/colunas.
- **Pré-visualização** editável (Streamlit `st.data_editor`) e download em **CSV/XLSX** (uma planilha por tabela).
- Suporte a múltiplas tabelas por arquivo (dropdown para selecionar).
- Exporta um único `.xlsx` com **uma aba por tabela** quando houver várias.

## Como rodar localmente
```bash
pip install -r requirements.txt
# Instale também os pacotes de sistema (Ubuntu/Debian):
# sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-por ghostscript poppler-utils libgl1
streamlit run app.py
```

## Deploy — Streamlit Cloud (mais simples)
1) Crie um repositório no GitHub e suba **todos** os arquivos deste projeto.
2) Acesse https://share.streamlit.io (ou Cloud) e clique em **New app**.
3) Selecione seu repositório, branch principal e arquivo `app.py`.
4) Ele vai instalar automaticamente `requirements.txt` e **packages.txt** (dependências do SO).
5) Ao finalizar, compartilhe o **link** com sua equipe.

> **Observação:** O Streamlit Cloud instala apt packages via `packages.txt`. Já incluímos:
> `tesseract-ocr`, `tesseract-ocr-por`, `ghostscript`, `poppler-utils`, `libgl1`.

## Deploy — Hugging Face Spaces (mais robusto p/ OCR)
1) Crie um Space (tipo **Streamlit**).
2) Faça upload de todos os arquivos (incluindo `packages.txt`).
3) O Space será buildado e publicado. Compartilhe o link.

## Deploy — Produção (Google Cloud Run — opcional)
- Dockerize o app e publique em **Cloud Run** (serverless). Use **GCS** para armazenar uploads e **Firestore** para estados de job.
- Para OCR/Tabelas de alta robustez, considere **Document AI** (Google) ou **Textract** (AWS) e troque a função `ocr_extract_tables` (ver `src/extract.py`).

## Mapeamento p/ seu Padrão de DRE / Plano de Contas
- Este MVP exporta as **tabelas brutas**.
- Para padronizar contas (sinônimos, códigos, “Conta / Código / Descrição”), preencha regras em `mapping_rules.yaml`
  e implemente ajustes em `src/normalize.py` (placeholders já prontos).

## Limitações & próximos passos
- OCR em documentos muito ruins pode exigir ajustes finos (threshold/deskew).
- **Tabula** exige Java e foi evitado neste MVP (para simplificar o deploy). **Camelot** cobre muitos casos.
- Para desempenho/escala, mover extração para um **worker** (Celery/Cloud Run Job) e UI só como orquestração.
