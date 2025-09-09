from typing import Dict
from lxml import etree
import re
from dateutil.parser import parse


@staticmethod
def _criar_estrutura_xml_base(cls):
    root = etree.Element('CompNfse', xmls='http://www.abrasf.org.br/nfse.xsd')
    nfse = etree.SubElement(root, "Nfse", versao="1.00")
    inf_nfse = etree.SubElement(nfse, "InfNfse", Id="")
    return root, nfse, inf_nfse


@staticmethod
def _inf_nfse_child(cls, inf_nfse, dados):
    numero_raw = dados.get("numero-nota-fiscal", "")
    linhas = numero_raw.splitlines()
    if len(linhas) >= 2:
        numero = linhas[1].strip()
    elif len(linhas) == 1:
        numero = linhas[0].strip()
    else:
        numero = ""
    numero_limpo = re.sub(r'[^a-zA-Z0-9]', '', numero)
    etree.SubElement(inf_nfse, "Numero").text = numero_limpo
    
    # Código de verificação
    codigo_verificacao = dados.get("codigoVerificacao", "")
    codigo_verificacao_clean = re.sub(r'[^a-zA-Z0-9]', '', codigo_verificacao)
    etree.SubElement(inf_nfse, "CodigoVerificacao").text = codigo_verificacao_clean
    
    # Data de emissão
    data_emissao = str(dados.get("dataEmissao", "")).replace(" às ", " ")
    print(f"A data de emissão é: {data_emissao} 1")
    try:
        data_emissao_obj = parse(data_emissao, dayfirst=True)
        data_emissao_formatada = data_emissao_obj.strftime("%Y-%m-%dT%H:%M:%S")
        print(f"Data de emissão formatada: {data_emissao_formatada}")
    except Exception as e:
        data_emissao_formatada = ""
        print(f"Erro ao converter a data de emissão: {data_emissao} -> {e}")
    etree.SubElement(inf_nfse, "DataEmissao").text = data_emissao_formatada
    print(f"A data de emissão é: {data_emissao_formatada} 2")
    # Retornamos a data formatada para uso posterior
    return data_emissao_formatada

