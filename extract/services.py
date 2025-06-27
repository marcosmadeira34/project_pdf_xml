import json
import os
from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account
from google.protobuf.json_format import MessageToJson
from dotenv import load_dotenv
from lxml import etree
from typing import Dict, Optional, List, Tuple
import base64
import re
from datetime import datetime
import pandas as pd
from dateutil.parser import parse
import logging
import cidades_ibge 
import unicodedata
from difflib import get_close_matches
from decimal import Decimal, InvalidOperation



# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# carrega as variáveis de ambiente
load_dotenv()

# define a classe de credenciais (conceito SOLID)
class CredentialsLoader:
    """Carrega as credenciais do Google a partir de um arquivo local ou de Base64"""

    @staticmethod
    def loader_credentials() -> Optional[service_account.Credentials]:
        credentials_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        print(f'Carregado credenciais do ambiente: {credentials_env}')

        if not credentials_env:
            print("Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS não definida")
            return None

        # Verifica se a string é um caminho de arquivo válido
        if os.path.exists(credentials_env):
            print(f"Carregando credenciais do arquivo: {credentials_env}")
            try:
                with open(credentials_env, "r") as file:
                    credentials_data = json.load(file)
                return service_account.Credentials.from_service_account_info(credentials_data)
            except Exception as e:
                print(f"Erro ao carregar credenciais do arquivo: {e}")
                return None

        # Se não for um caminho válido, assume que é um JSON codificado em Base64
        try:
            # print("Detectado formato Base64, decodificando credenciais...")
            credentials_json = base64.b64decode(credentials_env).decode("utf-8")

            # Salva temporariamente no sistema de arquivos
            temp_credentials_path = "/tmp/google_credentials.json"
            with open(temp_credentials_path, "w") as temp_file:
                temp_file.write(credentials_json)

            print(f"Credenciais salvas temporariamente em: {temp_credentials_path}")

            credentials_data = json.loads(credentials_json)
            return service_account.Credentials.from_service_account_info(credentials_data)

        except Exception as e:
            print(f"Erro ao processar credenciais: {e}")
            return None


# define a classe de extração de dados
class DocumentAIProcessor:
    """Processa documentos PDF usando API Google DocumentAI"""   
    def __init__(self, client: Optional[documentai.DocumentProcessorServiceClient] = None):
        self.credentials = CredentialsLoader.loader_credentials()
        if self.credentials:
            self.client = client or documentai.DocumentProcessorServiceClient(credentials=self.credentials)
            print("Cliente DocumentAI iniciado com sucesso")
        else:
            raise ValueError("Não foi possível carregar as credenciais")
        
    
    # método para envio de arquivos em lote para processamento evitando erros de limite de memória
    def dividir_em_lotes(self, arquivos: Dict[str, bytes], tamanho_lote: int) -> List[Dict[str, bytes]]:
        """Divide um dicionário de arquivos em lotes menores"""
        chaves = list(arquivos.keys())  # Pegamos apenas os nomes dos arquivos
        return [
            {chave: arquivos[chave] for chave in chaves[i:i + tamanho_lote]} 
            for i in range(0, len(chaves), tamanho_lote)
        ]

    
    
    # método para processar o PDF carregado pelo usuário
    def processar_pdf(self, project_id: str, location: str, processor_id: str, file_content: bytes) -> Dict:
        """Processa o PDF diretamente dos dados binários"""
        if not file_content:
            raise ValueError("Conteúdo do arquivo não pode ser vazio")
        
        document = {"content": file_content, "mime_type": "application/pdf"}
        name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
        request = {"name": name, "raw_document": document}

        try:
            result = self.client.process_document(request=request)
            document_obj = result.document
            # print(f"Aqui está o resultado: {document_obj.text}")
            return json.loads(MessageToJson(document_obj._pb))
        except Exception as e:
            print(f"Erro ao processar o documento: {e}")
            return {}
        
    
    # metodo para mapeamento dos campos extraídos do PDF
    def mapear_campos(self, document_json):
        """
        Mapeia as entidades extraídas pelo Document AI para um dicionário com os dados desejados.
        """
        dados = {}

        # Mapeamento entre os tipos de entidade retornados e as chaves que você quer no seu dicionário final.
        mapeamento = {
        "aliquota": "aliquota",
        "base_calculo": "baseCalculo",
        "bairro_prestador": "bairroPrestador",
        "bairro_tomador": "bairroTomador",
        "cep_prestador": "cepPrestador",
        "cep_tomador": "cepTomador",
        "cidade_nfs": "cidadeNfs",
        "cod_verificacao": "codigoVerificacao",
        "cofins": "cofins",
        "cpf_cnpj": "cpfCnpjPrestador",        # exemplo para prestador
        "cpf_cnpj_tomador": "cpfCnpjTomador",    # exemplo para tomador
        "credito": "credito",
        "csll": "csll",
        "data_da_emissao": "dataEmissao",
        "data_emissao_rps": "dataEmissaoRps",
        "data_rps": "dataRps",
        "deducoes": "deducoes",
        "desc_incon": "descIncondicional",
        "descontos_diversos": "descontosDiversos",
        "discriminacao": "Discriminacao",# pode ser o mesmo que 'discriminacao_servico'
        "email_prestador": "emailPrestador",
        "email_tomador": "emailTomador",
        "endereco_prestador": "enderecoPrestador",
        "endereco_tomador": "enderecoTomador",
        "exigibilidade_iss": "exigibilidadeIss",
        "imposto_renda": "impostoRenda",
        "inscricao_estadual": "inscricaoEstadualPrestador",
        "inscricao_estadual_tomador": "inscricaoEstadualTomador",
        "inscricao_municipal": "inscricaoMunicipalTomador",
        "inscricao_municipal_prestador": "inscricaoMunicipalPrestador",
        "inss": "valorInss",
        "iss": "valorIss",   
        "item_lista_servico" : "item_lista_servico",  # ou itemListaServico, dependendo do seu mapeamento
        "local_prestacao": "localPrestacao",
        "municipio_prestacao_servico": "municipioPrestacaoServico",
        "municipio_prestador": "municipioPrestador",
        "municipio_tomador": "municipioTomador",
        "nome_fantasia": "nomeFantasiaPrestador",
        "num_inscr_obra": "numInscricaoObra",
        "numero-nota-fiscal": "numero-nota-fiscal",        # ou numeroRps, dependendo do seu mapeamento
        'numero_lograd_prestador': 'numeroPrestador',
        'numero_lograd_tomador': 'numeroTomador',
        "pis": "pis",
        "prefeitura_nota": "prefeituraNota",
        "razao_social": "razaoSocialPrestador",
        "razao_social_tomador": "razaoSocialTomador",
        "regime_tributario": "regimeTributario",
        "repasse_terceiros": "repasseTerceiros",
        "serie": "serie",
        "serie_nfse": 'serieRps',
        "servico": "servico",
        "simples_nacional": "simplesNacional",
        "telefone_prestador": "telefonePrestador",
        "telefone_tomador": "telefoneTomador",
        "tipo_recolhimento": "tipoRecolhimento",
        "uf_prestador": 'ufPrestador',
        'uf_tomador': 'ufTomador',
        "valor_aprox_tributos_fonte": "valorAproxTributosFonte",
        "valor_liquido": "valorLiquido",
        "valor_servico": "valorServicos",
    }

        # Percorre todas as entidades retornadas
        for entidade in document_json.get("entities", []):
            tipo = entidade.get("type")
            chave = mapeamento.get(tipo)
            # print(f"Tipo encontrado: {tipo}, chave mapeada: {chave}")
            if chave:
                # Pode haver casos em que o mesmo campo seja identificado mais de uma vez;
                # aqui você pode definir como tratar isso (por exemplo, mantendo a primeira ocorrência).
                dados[chave] = entidade.get("mentionText")
                
                # Se houver valor normalizado (como data já formatada), você pode usá-lo:
                if entidade.get("normalizedValue"):
                    # Exemplo para data:
                    if tipo == "data_da_emissao" and entidade["normalizedValue"].get("text"):
                        dados[chave] = entidade["normalizedValue"]["text"]

        return dados



class CidadeIBGELoader:
    _cidades = None

    @classmethod
    def carregar(cls, caminho_arquivo="cidades_ibge.json"):
        if cls._cidades is None:
            with open(caminho_arquivo, encoding="utf-8") as f:
                cls._cidades = json.load(f)
        return cls._cidades


# define a classe para geração de XML
class XMLGenerator:
    
    
    NAMESPACE = "http://www.abrasf.org.br/nfse.xsd"
    nsmap = {None: NAMESPACE}

    @staticmethod
    def formatar_valor_monetario(valor: str) -> str:
        """Formata um valor monetário para o padrão brasileiro."""
        try:
            valor_limpo = valor.replace('.', '').replace(',', '.').strip()
            return "{:.2f}".format(float(valor_limpo))
        except ValueError:
            raise ValueError(f"Valor inválido para formatação: {valor}")



    @staticmethod
    def _adiciona_elemento(parent, tag: str, text: str):
        """Adiciona um elemento XML apenas se houver valor"""
        if text:
            elem = etree.SubElement(parent, tag)
            elem.text = text



    @staticmethod
    def validar_dados_criticos(dados, campo_nome: str, numero_nf_key='numero-nota-fiscal',
                               prestador_key="razaoSocialPrestador"):
        """
        Valida e formata um valor monetário extraído do dicionário `dados`.
        Emite alertas caso esteja ausente ou inválido.

        :param dados: dicionário com os dados da nota fiscal
        :param campo_nome: nome da chave no dicionário que contém o valor
        :param numero_nf_key: chave que contém o número da nota fiscal (para log)
        :param prestador_key: chave que contém o nome do prestador (para log)
        :return: valor formatado como string (ex: '123.45') ou string vazia se inválido
        """
        valor = str(dados.get(campo_nome, "0.00")).strip()
        numero_nf = dados.get(numero_nf_key, "0.00")
        prestador = dados.get(prestador_key, "0.00")

        if not valor:
            logger.warning(
                f"[AVISO] Campo '{campo_nome}' ausente na nota {numero_nf} | Prestador: {prestador}"
            )
            return ""

        try:
            valor_formatado = valor.replace(',', '.').replace(' ', '')
            valor_formatado = "{:.2f}".format(float(valor_formatado))
            return valor_formatado
        except ValueError:
            logger.warning(
                f"[ERRO] Valor inválido para '{campo_nome}': '{valor}' na nota {numero_nf} | Prestador: {prestador}"
            )
            return ""
        

    @staticmethod
    def obter_exigibilidade_iss(dados) -> str:
        """
        Determina a exigibilidade do ISS com base nas regras fiscais vigentes e nos dados da nota.
        """
        valor_bruto = str(dados.get("exigibilidade_iss", "")).strip()

        if valor_bruto in {"1", "2", "3", "4", "5", "6"}:
            return valor_bruto

        # Se há uma flag de exportação ou tomador do exterior
        pais_tomador = str(dados.get("paisTomador", "1058")).strip()  # 1058 = Brasil
        if pais_tomador and pais_tomador != "1058":
            return "4"  # Exportação

        # Se a natureza da operação indica isenção ou não incidência
        natureza = str(dados.get("naturezaOperacao", "")).lower()

        if "isencao" in natureza or "isenção" in natureza:
            return "3"
        elif "nao incidencia" in natureza or "não incidência" in natureza:
            return "2"
        elif "imunidade" in natureza:
            return "5"
        elif "decisao judicial" in natureza or "decisão judicial" in natureza:
            return "6"

        # Valor padrão
        logger.warning(
            f"[ExigibilidadeISS] Valor ausente ou não reconhecido para a nota {dados.get('numero-nota-fiscal', '')} | "
            f"Prestador: {dados.get('razaoSocialPrestador', '')}. Aplicado valor padrão '1' (Exigível)."
        )
        return "1"



    @staticmethod
    def obter_codigo_municipio(nome_municipio: str, uf: str) -> str:
        """
        Busca o código IBGE com base no nome e UF, usando o dicionário carregado no settings.
        Funciona mesmo que nome_municipio ou uf venham como lista (acidentalmente).
        """
        print(f"[DEBUG] municipioPrestador bruto: {nome_municipio}")
        print(f"[DEBUG] ufPrestador bruto: {uf}")
        
        # Corrige se os campos vierem como listas (por exemplo: ["PARNAMIRIM"])
        if isinstance(nome_municipio, list):
            nome_municipio = nome_municipio[0] if nome_municipio else ""
        if isinstance(uf, list):
            uf = uf[0] if uf else ""

        if not nome_municipio or not uf:
            logger.warning("Nome do município ou UF ausente ou inválido.")
            return ""

        def normalizar(texto):
            texto = unicodedata.normalize("NFD", texto)
            texto = texto.encode("ascii", "ignore").decode("utf-8")
            texto = re.sub(r'[^a-zA-Z0-9\s]', '', texto)
            return texto.upper().strip()

        # Normaliza
        nome_normalizado = normalizar(nome_municipio)
        uf_normalizado = normalizar(uf)

        chave_exata = f"{nome_normalizado}-{uf_normalizado}"

        print(f"[DEBUG] municipioPrestador normalizado: {nome_normalizado}")
        print(f"[DEBUG] ufPrestador normalizado: {uf_normalizado}")
        print(f"[DEBUG] chave_exata formada: {chave_exata}")

        # Busca exata
        if chave_exata in cidades_ibge.CIDADES_IBGE:
            return cidades_ibge.CIDADES_IBGE[chave_exata]

        # Busca parcial
        for chave, codigo in cidades_ibge.CIDADES_IBGE.items():
            try:
                nome_dicionario, uf_dicionario = chave.split("-")
            except ValueError:
                continue

            if nome_dicionario == nome_normalizado and uf_dicionario == uf_normalizado:
                return codigo

        for chave, codigo in cidades_ibge.CIDADES_IBGE.items():
            if nome_normalizado in chave and f"-{uf_normalizado}" in chave:
                logger.warning(f"[CodigoMunicipio] Correspondência parcial encontrada: '{chave}' para '{nome_municipio}-{uf}'")
                return codigo

        # Sugestão por similaridade
        chaves_possiveis = list(cidades_ibge.CIDADES_IBGE.keys())
        similares = get_close_matches(chave_exata, chaves_possiveis, n=1, cutoff=0.85)
        if similares:
            sugestao = similares[0]
            logger.warning(f"[CodigoMunicipio] Sugestão de chave similar encontrada: '{sugestao}' para '{chave_exata}'")
            return cidades_ibge.CIDADES_IBGE[sugestao]

        logger.warning(f"[CodigoMunicipio] Município '{nome_municipio}-{uf}' não encontrado na base IBGE.")
        return ""
    
    
    
    @classmethod
    def gerar_xml_abrasf(cls, dados: Dict) -> str:
        print(f"Dados recebidos para geração do XML: {json.dumps(dados, indent=4, ensure_ascii=False)}")

        # Criação dos elementos principais
        root = etree.Element("CompNfse", xmlns="http://www.abrasf.org.br/nfse.xsd")
        nfse = etree.SubElement(root, "Nfse", versao="1.00")
        inf_nfse = etree.SubElement(nfse, "InfNfse", Id="")

        # Adicionando os campos para 'InfNfse'
        etree.SubElement(inf_nfse, "Numero").text = dados.get("numero-nota-fiscal", "")
        codigo_verificacao = dados.get("codigoVerificacao", "")
        codigo_verificacao_clean = re.sub(r'[^a-zA-Z0-9]', '', codigo_verificacao)


        etree.SubElement(inf_nfse, "CodigoVerificacao").text = codigo_verificacao_clean
        data_emissao = str(dados.get("dataEmissao", "")).replace(" às ", " ")
        print(f"A data de emissão é: {data_emissao} 1")

        try:
            data_emissao_obj = parse(data_emissao, dayfirst=True)
            data_emissao_formatada = data_emissao_obj.strftime("%Y-%m-%dT%H:%M:%S")
            print(f"Data de emissão formatada: {data_emissao_formatada}")
        except Exception as e:
            data_emissao_formatada = ""
            print(f"Erro ao converter a data de emissão: {data_emissao} -> {e}")

        # Agora você pode usar a data formatada
        etree.SubElement(inf_nfse, "DataEmissao").text = data_emissao_formatada
        print(f"A data de emissão é: {data_emissao_formatada} 2")

        # Valores da NFS-e
        valores_nfse = etree.SubElement(inf_nfse, "ValoresNfse")
        base_calculo = str(dados.get("baseCalculo", ""))
        # Remove o ponto de milhar e substitui a vírgula por ponto
        base_calculo_formatada = base_calculo.replace('.', '').replace(',', '.')
        # Agora você pode usar a string formatada
        etree.SubElement(valores_nfse, "BaseCalculo").text = base_calculo_formatada

        aliquota = str(dados.get("aliquota", "")).strip()

        # Remove o caractere '%' e substitui a vírgula por ponto
        aliquota_formatada = aliquota.replace('%', '').replace(',', '.')

        # Tenta converter para float, lançando erro se for inválido
        if aliquota_formatada:
            aliquota_float = float(aliquota_formatada)
            print(f"Alíquota formatada linha 394: {aliquota_float}")
        else:
            aliquota_float = 0.0

        etree.SubElement(valores_nfse, "Aliquota").text = str(aliquota_float)

        valor_iss = str(dados.get("valorIss", "0,00"))
        # Remove o ponto de milhar e substitui a vírgula por ponto
        valor_iss_formatado = valor_iss.replace('.', '').replace(',', '.')
        etree.SubElement(valores_nfse, "ValorIss").text = valor_iss_formatado
        
        

        # Dados do prestador
        prestador_servico = etree.SubElement(inf_nfse, "PrestadorServico")
        id_prestador = etree.SubElement(prestador_servico, "IdentificacaoPrestador")
        cpf_cnpj_prestador = etree.SubElement(id_prestador, "CpfCnpj")
        cpf_cnpj_prestador_text = dados.get("cpfCnpjPrestador", "")
        # Remove caracteres não numéricos
        cpf_cnpj_prestador_clean = re.sub(r'\D', '', cpf_cnpj_prestador_text)
        # Verifica se é CPF ou CNPJ
        if len(cpf_cnpj_prestador_clean) == 11:
            etree.SubElement(cpf_cnpj_prestador, "Cpf").text = cpf_cnpj_prestador_clean
        else:
            etree.SubElement(cpf_cnpj_prestador, "Cnpj").text = cpf_cnpj_prestador_clean

        inscricao_municipal = dados.get("inscricaoMunicipalPrestador", "")
        # Remove caracteres não numéricos
        inscricao_municipal_clean = re.sub(r'\D', '', inscricao_municipal)
        etree.SubElement(id_prestador, "InscricaoMunicipal").text = inscricao_municipal_clean
        
        
        razao_social_raw = dados.get("razaoSocialPrestador", "")
        razao_social_formatada = re.sub(r'\s+', ' ', razao_social_raw).strip()
        etree.SubElement(prestador_servico, "RazaoSocial").text = razao_social_formatada

        nome_fantasia_raw = dados.get("nomeFantasiaPrestador", "")
        nome_fantasia_formatada = re.sub(r'\s+', ' ', nome_fantasia_raw).strip()
        etree.SubElement(prestador_servico, "NomeFantasia").text = nome_fantasia_formatada

        # Endereço do prestador
        endereco_prestador = etree.SubElement(prestador_servico, "Endereco")
        etree.SubElement(endereco_prestador, "Endereco").text = dados.get("enderecoPrestador")
        etree.SubElement(endereco_prestador, "Numero").text = str(dados.get("numeroPrestador"))
        etree.SubElement(endereco_prestador, "Bairro").text = dados.get("bairroPrestador")
        
        codigo_municipio_prestador = cls.obter_codigo_municipio(
            dados.get("municipioPrestador", ""),
            dados.get("ufPrestador", "")
        )        
        etree.SubElement(endereco_prestador, "CodigoMunicipio").text = codigo_municipio_prestador
        
        etree.SubElement(endereco_prestador, "CodigoPais").text = str(dados.get("codigoPais", "1058"))
        cep_prestador = dados.get("cepPrestador", "")
        # Remove caracteres não numéricos do CEP (ex: 68825-001 -> 68825001)
        cep_prestador_clean = re.sub(r'[^0-9]', '', cep_prestador)
        etree.SubElement(endereco_prestador, "Cep").text = cep_prestador_clean

        # Contato do prestador
        contato_prestador = etree.SubElement(prestador_servico, "Contato")
        telefone_prestador = etree.SubElement(contato_prestador, "Telefone")
        telefone_prestador.text = dados.get("telefonePrestador", "")
        
        etree.SubElement(contato_prestador, "Email").text = dados.get("emailPrestador")

        # Orgão Gerador
        orgao_gerador = etree.SubElement(inf_nfse, "OrgaoGerador")
        
        # Código do município do órgão gerador
        codigo_municipio_orgao = cls.obter_codigo_municipio(
            dados.get("municipioPrestador", ""),
            dados.get("ufPrestador", "")
        )
        etree.SubElement(orgao_gerador, "CodigoMunicipio").text = codigo_municipio_orgao


        etree.SubElement(orgao_gerador, "Uf").text = dados.get("ufPrestador")

        # Declaração de Prestação de Serviço
        declaracao_prestacao_servico = etree.SubElement(inf_nfse, "DeclaracaoPrestacaoServico")
        inf_declaracao_prestacao_servico = etree.SubElement(declaracao_prestacao_servico, "InfDeclaracaoPrestacaoServico")
        
        # Extrai a competência a partir do campo informado ou da data de emissão
        valor_competencia = dados.get("competencia", "").strip()
        print(f"Valor da competência (inicial): {valor_competencia}")

        if not valor_competencia:
            data_emissao = dados.get("dataEmissao", "")
            
            # Usa regex para extrair padrão DD-MM-YYYY
            match = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', data_emissao)
            if match:
                dia, mes, ano = match.groups()
                try:
                    data_formatada = datetime.strptime(f"{ano}-{mes}-{dia}", "%Y-%m-%d")
                    valor_competencia = data_formatada.strftime("%Y-%m-01")  # sempre o 1º dia do mês
                except ValueError as e:
                    logger.warning(f"[ERRO] Falha ao converter data de emissão '{data_emissao}' para competência: {e}")
            else:
                logger.warning(f"[ERRO] Nenhuma data reconhecida em dataEmissao: '{data_emissao}'")

        # Adiciona a tag ao XML
        etree.SubElement(inf_declaracao_prestacao_servico, "Competencia").text = valor_competencia

        if not valor_competencia:
            logger.warning(
                f"Competência não informada ou inválida para a nota {dados.get('numero-nota-fiscal', '')} | "
                f"Prestador: {dados.get('razaoSocialPrestador', '')}"
            )


        # Serviço
        servico = etree.SubElement(inf_declaracao_prestacao_servico, "Servico")
        valores_servico = etree.SubElement(servico, "Valores")
        
        # ValorServicos
        valor_servicos = cls.validar_dados_criticos(dados, "valorServicos")
        if valor_servicos is None:
            valor_servicos_none = "0.00"  # Define um valor padrão se não for encontrado
            etree.SubElement(valores_servico, "ValorServicos").text = valor_servicos_none
        else:
            etree.SubElement(valores_servico, "ValorServicos").text = valor_servicos        

        # ValorDeducoes
        valor_deducoes = cls.validar_dados_criticos(dados, "deducoes")
        if valor_deducoes is None:
            valor_deducoes_none = "0.00"
            etree.SubElement(valores_servico, "ValorDeducoes").text = valor_deducoes_none
        else:
            etree.SubElement(valores_servico, "ValorDeducoes").text = valor_deducoes       
        
        # ValorIr
        valor_ir = cls.validar_dados_criticos(dados, "impostoRenda")
        if valor_ir is None:
            valor_ir_none = "0.00"  # Define um valor padrão se não for encontrado        
            etree.SubElement(valores_servico, "ValorIr").text = valor_ir_none
        else:
            etree.SubElement(valores_servico, "ValorIr").text = valor_ir

        # ValorIss
        valor_iss_servico = cls.validar_dados_criticos(dados, "valorIss")
        if valor_iss_servico is None:
            valor_iss_servico_none = "0.00"  # Define um valor padrão se não for encontrado        
            etree.SubElement(valores_servico, "ValorIss").text = valor_iss_servico_none
        else:
            etree.SubElement(valores_servico, "ValorIss").text = valor_iss_servico


        # Aliquota
        aliquota_servico = str(dados.get("aliquota", "")).strip()
        aliquota_servico_formatada = aliquota_servico.replace('%', '').replace(',', '.')  # Remove espaços e converte vírgulas
        
        if aliquota_servico_formatada:
            aliquota_servico_float = float(aliquota_servico_formatada)
        else:
            aliquota_servico_float = "0.00"
            #raise ValueError(f"Valor inválido para alíquota: {aliquota_servico}")
        etree.SubElement(valores_servico, "Aliquota").text = str(aliquota_servico_float)    

        # IssRetido
        iss_retido_val = str(dados.get("iss_retido", "")).strip().lower()   
        iss_retido_formatado = "1" if iss_retido_val in ["1", "sim", "true"] else "2"
        logger.info(
            f"Houve retenção de ISS na nota {dados.get('numero-nota-fiscal', '')}: Valor: {iss_retido_formatado} | "
            f"Prestador: {dados.get('razaoSocialPrestador', '')}"
        )        
        etree.SubElement(servico, "IssRetido").text = iss_retido_formatado

        item_lista_servico = str(dados.get("item_lista_servico", "")).strip()
        print(f"Item Lista Serviço original: {item_lista_servico}")
        # Extrai apenas o código numérico do início (ex: "16.02" de "16.02-Outros serviços...")
        match = re.match(r'^(\d{2}\.\d{2})', item_lista_servico)
        item_lista_servico = match.group(1) if match else item_lista_servico.strip()
        print(f"Item Lista Serviço formatado: {item_lista_servico}")
        # Adiciona o item_lista_servico ao XML        
        etree.SubElement(servico, "ItemListaServico").text = item_lista_servico
        
        
        codigo_cnae = etree.SubElement(servico, "CodigoCnae").text = re.sub(r'[^\w\s]', '', dados.get("codigo_cnae", ""))
        # Verifica se o código CNAE está vazio
        if not codigo_cnae:
            logger.warning(
                f"Código CNAE não informado para a nota {dados.get('numero-nota-fiscal', '')} |"
                f" Prestador: {dados.get('razaoSocialPrestador', '')}"
            )

        discriminacao = etree.SubElement(servico, "Discriminacao").text = dados.get("Discriminacao", "")
        # Verifica se a discriminação está vazia
        if not discriminacao:
            logger.warning(
                f"Discriminação não informada para a nota {dados.get('numero-nota-fiscal', '')} | "
                f"Prestador: {dados.get('razaoSocialPrestador', '')}")

        
        # Código do município do prestador
        codigo_municipio_servico = cls.obter_codigo_municipio(
            dados.get("municipioPrestador", ""),
            dados.get("ufPrestador", "")
        )

        etree.SubElement(servico, "CodigoMunicipio").text = codigo_municipio_servico

        
        etree.SubElement(servico, "CodigoPais").text = str(dados.get("codigoPais", "1058"))
        
        exigibilidade = cls.obter_exigibilidade_iss(dados)
        etree.SubElement(servico, "ExigibilidadeISS").text = exigibilidade

       
        codigo_municipio_incidencia = cls.obter_codigo_municipio(
            dados.get("municipioPrestador", ""),  # ou outro campo, se for diferente
            dados.get("ufPrestador", "")
        )

        etree.SubElement(servico, "MunicipioIncidencia").text = codigo_municipio_incidencia


        # Tomador Serviço
        tomador_servico = etree.SubElement(inf_declaracao_prestacao_servico, "Tomador")
        id_tomador = etree.SubElement(tomador_servico, "IdentificacaoTomador")        
        cpf_cnpj_tomador = etree.SubElement(id_tomador, "CpfCnpj")
        cpf_cnpj_tomador_text = dados.get("cpfCnpjTomador", "")
        
        
        
        
        # remove caracteres não numéricos
        cpf_cnpj_tomador_clean = re.sub(r'\D', '', cpf_cnpj_tomador_text)
        # Verifica se é CPF ou CNPJ
        if len(cpf_cnpj_tomador_clean) == 11:
            etree.SubElement(cpf_cnpj_tomador, "Cpf").text = cpf_cnpj_tomador_clean
        else:
            etree.SubElement(cpf_cnpj_tomador, "Cnpj").text = cpf_cnpj_tomador_clean
        


        razao_social_tomador = etree.SubElement(tomador_servico, "RazaoSocial")
        razao_social_tomador.text = dados.get("razaoSocialTomador", "")
        
        
        # Endereço do tomador
        endereco_tomador = etree.SubElement(tomador_servico, "Endereco")
        logradouro_tomador = etree.SubElement(endereco_tomador, "Endereco")
        logradouro_tomador.text = dados.get("enderecoTomador", "")
        numero_tomador = etree.SubElement(endereco_tomador, "Numero")
        numero_tomador.text = dados.get("numeroTomador", "")
        bairro_tomador = etree.SubElement(endereco_tomador, "Bairro")
        bairro_tomador.text = dados.get("bairroTomador", "")
        codigo_municipio_tomador = cls.obter_codigo_municipio(
            dados.get("municipioTomador", ""),
            dados.get("ufTomador", "")
        )
        etree.SubElement(endereco_tomador, "CodigoMunicipio").text = codigo_municipio_tomador

        uf_tomador = etree.SubElement(endereco_tomador, "Uf")
        uf_tomador.text = dados.get("ufTomador", "")

        codigo_pais_tomador = etree.SubElement(endereco_tomador, "CodigoPais")
        codigo_pais_tomador.text = str(dados.get("codigoPais", "1058"))

        
        cep_tomador = etree.SubElement(endereco_tomador, "Cep")
        cep_tomador.text = dados.get("cepTomador", "")

        contato_tomador = etree.SubElement(tomador_servico, "Contato")
        telefone_tomador = etree.SubElement(contato_tomador, "Telefone")
        telefone_tomador.text = dados.get("telefoneTomador", "")

        email_tomador = etree.SubElement(contato_tomador, "Email")
        email_tomador.text = dados.get("emailTomador", "")


        valor_liquido_str = dados.get("valorLiquido", "").replace(',', '.').strip()

        try:
            valor_liquido_nfse = "{:.2f}".format(Decimal(valor_liquido_str))
        except (InvalidOperation, ValueError):
            try:
                valor_servicos_dec = Decimal(dados.get("valorServicos", "0").replace(',', '.'))
                valor_iss_dec = Decimal(dados.get("valorIss", "0").replace(',', '.'))
                valor_ir_dec = Decimal(dados.get("valorIr", "0").replace(',', '.'))

                valor_liquido_calc = valor_servicos_dec - valor_iss_dec - valor_ir_dec
                valor_liquido_nfse = "{:.2f}".format(valor_liquido_calc)
                print(f"Valor líquido calculado: {valor_liquido_nfse}")
            except (InvalidOperation, ValueError, TypeError) as e:
                valor_liquido_nfse = "0.00"
                logger.error(
                    f"Erro ao calcular o valor líquido: {e}. Usando valor padrão 0.00. "
                    f"Nota número: {dados.get('numero-nota-fiscal', '')}"
                )

        etree.SubElement(valores_nfse, "ValorLiquidoNfse").text = valor_liquido_nfse

        # Gerando o XML em formato string
        xml_str = etree.tostring(root, pretty_print=True, encoding="UTF-8").decode("utf-8")
        # Valida o XML gerado
        try:
            validador = ValidatorXSD()
            validador.validar_xml_abrasf(xml_str,
                                         caminho_xsd="nfse.xsd")
            logger.info("XML gerado e validado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao validar o XML gerado: {e}")
            raise

        # Imprime o XML gerado
        print(f"XML gerado: {xml_str}")
        return xml_str

    
    

class ExcelGenerator:
    """Gera um arquivo Excel com os dados extraídos."""
    
    @staticmethod
    def gerar_excel(dados: List[Dict], nome_arquivo: str = "dados_nfse.xlsx") -> str:
        """Gera um arquivo Excel a partir de uma lista de dicionários."""
        if not dados:
            raise ValueError("Nenhum dado fornecido para gerar o Excel")

        # Criação do DataFrame
        df = pd.DataFrame(dados)

        # Salvando o DataFrame em um arquivo Excel
        df.to_excel(nome_arquivo, index=False)

        print(f"Arquivo Excel gerado: {nome_arquivo}")
        return nome_arquivo


class ValidatorXSD:
    """Valida um XML contra um esquema XSD."""
    
    @staticmethod
    def validar_xml_abrasf(xml_str: str, caminho_xsd: str) -> Tuple[bool, list]:
        """
        Valida um XML gerado no padrão ABRASF contra o XSD oficial.
        
        :param xml_str: conteúdo do XML em string
        :param caminho_xsd: caminho do arquivo .xsd
        :return: (valido: bool, erros: list[str])
        """
        try:
            xml_doc = etree.fromstring(xml_str.encode("utf-8"))
            with open(caminho_xsd, "rb") as f:
                xsd_doc = etree.XML(f.read())
            schema = etree.XMLSchema(xsd_doc)

            if schema.validate(xml_doc):
                return True, []
            else:
                erros = [str(e.message) for e in schema.error_log]
                return False, erros
        except Exception as e:
            logger.error(f"[XSD] Erro ao validar XML: {e}")
            return False, [str(e)]
        

