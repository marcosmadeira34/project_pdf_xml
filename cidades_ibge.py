import unicodedata
import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r'[^a-zA-Z0-9\s]', '', texto)
    return texto.upper().strip()


with open("municipios.json", encoding="utf-8") as f:
    municipios_raw = json.load(f)


UF_POR_CODIGO = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF"
}

CIDADES_IBGE = {
    f"{normalizar(m['nome'])}-{UF_POR_CODIGO.get(m['codigo_uf'], '')}": str(m["codigo_ibge"])
    for m in municipios_raw
    if "nome" in m and "codigo_ibge" in m and "codigo_uf" in m
}