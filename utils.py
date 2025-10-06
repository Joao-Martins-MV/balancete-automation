import io
from typing import List, Tuple
import pandas as pd

def to_xlsx_bytes(sheets: List[Tuple[str, pd.DataFrame]]) -> bytes:
    # sheets: list of tuples (sheet_name, df)
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, df in sheets:
            safe = name[:31] if name else "Sheet"
            df.to_excel(writer, index=False, sheet_name=safe)
    bio.seek(0)
    return bio.read()
