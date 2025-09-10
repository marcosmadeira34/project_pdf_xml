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
    11: ["RO", "RONDONIA"],
    12: ["AC", "ACRE"],
    13: ["AM", "AMAZONAS"],
    14: ["RR", "RORAIMA"],
    15: ["PA", "PARA"],
    16: ["AP", "AMAPA"],
    17: ["TO", "TOCANTINS"],
    21: ["MA", "MARANHAO"],
    22: ["PI", "PIAUI"],
    23: ["CE", "CEARA"],
    24: ["RN", "RIO GRANDE DO NORTE"],
    25: ["PB", "PARAIBA"],
    26: ["PE", "PERNAMBUCO"],
    27: ["AL", "ALAGOAS"],
    28: ["SE", "SERGIPE"],
    29: ["BA", "BAHIA"],
    31: ["MG", "MINAS GERAIS"],
    32: ["ES", "ESPIRITO SANTO"],
    33: ["RJ", "RIO DE JANEIRO"],
    35: ["SP", "SAO PAULO"],
    41: ["PR", "PARANA"],
    42: ["SC", "SANTA CATARINA"],
    43: ["RS", "RIO GRANDE DO SUL"],
    50: ["MS", "MATO GROSSO DO SUL"],
    51: ["MT", "MATO GROSSO"],
    52: ["GO", "GOIAS"],
    53: ["DF", "DISTRITO FEDERAL"]
}


# Monta o dicionário com as chaves normalizadas
CIDADES_IBGE = {}
for m in municipios_raw:
    cod_uf = m["codigo_uf"]
    nomes_uf = UF_POR_CODIGO.get(cod_uf, [])
    for uf in (nomes_uf if isinstance(nomes_uf, list) else [nomes_uf]):
        chave = f"{unicodedata.normalize('NFD', m['nome']).encode('ascii', 'ignore').decode().upper().strip()}-{uf}"
        CIDADES_IBGE[chave] = str(m["codigo_ibge"])

        
# Função limpar_texto (mantemos)
def limpar_texto(texto):
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r'[\n\r\t]', ' ', texto)
    texto = re.sub(r'[^a-zA-Z0-9\s-]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.upper().strip()

    match = re.search(r'([A-Z]{2})[-\s]+\1$', texto)
    if match:
        texto = texto[:match.start()] + match.group(1)

    return texto

# Função extrair_municipio_uf (nova versão)
def extrair_municipio_uf(texto):
    padrao = r'([A-Z\s]+)[-\s]([A-Z]{2})'
    matches = list(re.finditer(padrao, texto))
    if matches:
        match = matches[-1]  # Última ocorrência
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



UF_POR_CODIGO = {
    42: ["SC", "SANTA CATARINA"]
}