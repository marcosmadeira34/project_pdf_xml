from pathlib import Path
import re
import json
import unicodedata
from rapidfuzz import process, fuzz
import logging

# Configurar o logger (você pode ajustar para o seu logger padrão)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CodigoMunicipio")


BASE_DIR = Path(__file__).resolve().parent.parent


with open("municipios.json", encoding="utf-8") as f:
    municipios_raw = json.load(f)
# Mapeamento UF por código IBGE
UF_POR_CODIGO = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF"
}

# Monta o dicionário com as chaves normalizadas
CIDADES_IBGE = {
    f"{unicodedata.normalize('NFD', m['nome']).encode('ascii', 'ignore').decode().upper().strip()}-{UF_POR_CODIGO[m['codigo_uf']]}": str(m['codigo_ibge'])
    for m in municipios_raw
}

def limpar_texto(texto):
    """Limpa e normaliza o texto extraído"""
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r'[\n\r\t]', ' ', texto)
    texto = re.sub(r'[^a-zA-Z0-9\s-]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.upper().strip()

def extrair_municipio_uf(texto):
    """Extrai automaticamente o município e UF do texto"""
    padrao = r'([A-Z\s]+)[-\s]([A-Z]{2})'
    match = re.search(padrao, texto)
    if match:
        municipio = match.group(1).strip()
        uf = match.group(2).strip()
        return municipio, uf
    return "", ""

def buscar_codigo_municipio(texto_ocr):
    """Fluxo completo de busca do código IBGE"""
    texto_limpo = limpar_texto(texto_ocr)
    municipio, uf = extrair_municipio_uf(texto_limpo)

    if not municipio or not uf:
        logger.warning(f"Não foi possível extrair município e UF do texto: {texto_ocr}")
        return ""

    chave = f"{municipio}-{uf}"
    # Busca direta
    if chave in CIDADES_IBGE:
        return CIDADES_IBGE[chave]

    # Matching fuzzy
    melhor, score, _ = process.extractOne(
        chave, CIDADES_IBGE.keys(), scorer=fuzz.WRatio
    )
    if score > 85:
        logger.warning(f"[CodigoMunicipio] Fuzzy Match aplicado: '{melhor}' para '{chave}' (Score: {score})")
        return CIDADES_IBGE[melhor]

    logger.error(f"[CodigoMunicipio] Município NÃO encontrado: '{municipio}-{uf}' extraído de '{texto_ocr}'")
    return ""
