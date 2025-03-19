import json
import os
from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account
from google.protobuf.json_format import MessageToJson
from dotenv import load_dotenv
from lxml import etree
from typing import Dict, Optional

# carrega as variáveis de ambiente
load_dotenv()

# define a classe de credenciais (conceito SOLID)
class CredentialsLoader:
    """Carrega as variáveis do Google à partir de variáveis de ambiente"""

    @staticmethod
    def loader_credentials() -> Optional[service_account.Credentials]:
        credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_json:
            print("Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS não definida")
            return None

        print(f"Carregando credenciais de: {credentials_json}")

        try:
            with open(credentials_json, 'r') as file:
                credentials_data = json.load(file)  # Carrega diretamente o arquivo JSON
            return service_account.Credentials.from_service_account_info(credentials_data) 
        except json.JSONDecodeError as e:
            print(f"Erro ao carregar as credenciais: {e}")
            return None
        except FileNotFoundError as e:
            print(f"Arquivo de credenciais não encontrado: {e}")
            return None
        except Exception as e:
            print(f"Erro ao carregar as credenciais: {e}")
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
            print(f"Aqui está o resultado: {document_obj.text}")
            return json.loads(MessageToJson(document_obj._pb))
        except Exception as e:
            print(f"Erro ao processar o documento: {e}")
            return {}
        
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
            print(f"Tipo encontrado: {tipo}, chave mapeada: {chave}")
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


# define a classe para geração de XML
class XMLGenerator:
    """Gera XML no padrão Abrasf com os dados extraídos."""
    NAMESPACE = "http://www.abrasf.org.br/nfse.xsd"
    nsmap = {None: NAMESPACE}

    @staticmethod
    def _adiciona_elemento(parent, tag: str, text: str):
        """Adiciona um elemento XML apenas se houver valor"""
        if text:
            elem = etree.SubElement(parent, tag)
            elem.text = text


   
    @classmethod
    def gerar_xml_abrasf(cls, dados: Dict) -> str:
        print(f"Dados recebidos para geração do XML: {json.dumps(dados, indent=4, ensure_ascii=False)}")


        """Gera um arquivo XML padrão ABRASF"""
        root = etree.Element("ConsultarNfseFaixaResposta", nsmap=cls.nsmap)
        lista_nfse = etree.SubElement(root, "ListaNfse")
        comp_nfse = etree.SubElement(lista_nfse, "CompNfse")
        nfse = etree.SubElement(comp_nfse, "Nfse")

        serie_nfse = etree.SubElement(nfse, "Serie")
        serie_nfse.text = dados.get("serie", "")

        tipo_nfse = etree.SubElement(nfse, "Tipo")
        tipo_nfse.text = dados.get("tipo_nfse", "1")

        status_nfse = etree.SubElement(nfse, "Status")
        status_nfse.text = dados.get("status", "1")

        inf_nfse = etree.SubElement(root, "InfNfse")
        numero = etree.SubElement(inf_nfse, "Numero")
        numero.text = dados.get("numero-nota-fiscal", "")
        
        codigo_verificacao = etree.SubElement(inf_nfse, "CodigoVerificacao")
        codigo_verificacao.text = dados.get("codigoVerificacao", "")

        data_emissao = etree.SubElement(inf_nfse, "DataEmissao")
        data_emissao.text = str(dados.get("dataEmissao", "") or "")
        print(f"Tipo de 'dataEmissao': {type(dados.get('dataEmissao'))}, valor: {dados.get('dataEmissao')}")
        
        # Valores da NFS-e      
        valores_nfse = etree.SubElement(inf_nfse, "ValoresNfse")
        base_calculo = etree.SubElement(valores_nfse, "BaseCalculo")
        base_calculo.text = str(dados.get("baseCalculo"))
        aliquota = etree.SubElement(valores_nfse, "Aliquota")
        aliquota.text = str(dados.get("aliquota", "") or "")
        print(f"A alíquota é: {aliquota}")
        valor_iss = etree.SubElement(valores_nfse, "ValorIss")
        valor_iss.text = str(dados.get("valorIss"))
        valor_liquido_nfse = etree.SubElement(valores_nfse, "ValorLiquidoNfse")
        valor_liquido_nfse.text = str(dados.get("valorLiquido", ""))
        
        # Dados do prestador
        prestador_servico = etree.SubElement(inf_nfse, "PrestadorServico")
        id_prestador = etree.SubElement(prestador_servico, "IdentificacaoPrestador")
        cpf_cnpj_prestador = etree.SubElement(id_prestador, "CpfCnpj")
        cpf_cnpj_prestador.text = dados.get("cpfCnpjPrestador")
        inscricao_municipal = etree.SubElement(id_prestador, "InscricaoMunicipal")
        inscricao_municipal.text = dados.get("inscricaoMunicipalPrestador", "")    
        razao_social = etree.SubElement(prestador_servico, "razaoSocialPrestador")
        razao_social.text = dados.get("razaoSocialPrestador")
        nome_fantasia = etree.SubElement(prestador_servico, "NomeFantasia")
        nome_fantasia.text = dados.get("nomeFantasiaPrestador")
        
        endereco_prestador = etree.SubElement(prestador_servico, "Endereco")
        endereco_texto = etree.SubElement(endereco_prestador, "Endereco")
        endereco_texto.text = dados.get("enderecoPrestador")
        numero_endereco = etree.SubElement(endereco_prestador, "Numero")
        numero_endereco.text = str(dados.get("numeroPrestador"))
        bairro = etree.SubElement(endereco_prestador, "Bairro")
        bairro.text = dados.get("bairroPrestador")
        complemento = etree.SubElement(endereco_prestador, "Complemento")
        complemento.text = dados.get("complemento")    
        cep = etree.SubElement(endereco_prestador, "Cep")
        cep.text = dados.get("cepPrestador")
        
        # Orgao Gerador
        orgao_gerador = etree.SubElement(inf_nfse, "OrgaoGerador")
        codigo_municipio_gerador = etree.SubElement(orgao_gerador, "CodigodoMunicipio")
        codigo_municipio_gerador.text = str(dados.get("municipioPrestacaoServico", ""))

        uf_gerador = etree.SubElement(orgao_gerador, "Uf")
        uf_gerador.text = dados.get("ufPrestador")

        # Declaracao Prestacao Servico
        declaracao_prestacao_servico = etree.SubElement(inf_nfse, "DeclaracaoPrestacaoServico")
        inf_declaracao_prestacao_servico = etree.SubElement(declaracao_prestacao_servico, "InfDeclaracaoPrestacaoServico")
        inf_declaracao_prestacao_servico.text = dados.get("inf_declaracao_prestacao_servico", "")
        competencia = etree.SubElement(inf_declaracao_prestacao_servico, "Competencia")
        competencia.text = dados.get("competencia", "")    
        
        # Servico
        servico = etree.SubElement(inf_declaracao_prestacao_servico, "Servico")
        cod_municipio = etree.SubElement(servico, 'CodigoMunicipio')
        cod_municipio.text = dados.get('CodigoMunicipio', "")
        discriminacao = etree.SubElement(servico, "Discriminacao")
        discriminacao.text = dados.get("Discriminacao")    
        exigibilidade_iss = etree.SubElement(servico, "ExigibilidadeISS")
        exigibilidade_iss.text = str(dados.get("exigibilidade_iss", ""))
        iss_retido = etree.SubElement(servico, "IssRetido")
        iss_retido.text = str(dados.get("iss_retido", "0,00"))
        item_lista_servico = etree.SubElement(servico, "ItemListaServico")
        item_lista_servico.text = dados.get("item_lista_servico", "")
        
        valores = etree.SubElement(servico, "Valores")
        valor_servicos = etree.SubElement(valores, 'ValorServicos')
        valor_servicos.text = str(dados.get("valorServicos"))
        valor_deducoes = etree.SubElement(valores, "ValorDeducoes")
        valor_deducoes.text = str(dados.get("deducoes", "0,00"))
        valor_pis = etree.SubElement(valores, "ValorPis")
        valor_pis.text = str(dados.get("pis", "0,00"))
        valor_cofins = etree.SubElement(valores, "ValorCofins")
        valor_cofins.text = str(dados.get("cofins", "0,00"))
        valor_inss = etree.SubElement(valores, "ValorInss")
        valor_inss.text = str(dados.get("valorInss", "0,00"))
        valor_ir = etree.SubElement(valores, "ValorIr")
        valor_ir.text = str(dados.get("impostoRenda", "0,00"))
        valor_csll = etree.SubElement(valores, "ValorCsll")
        valor_csll.text = str(dados.get("csll", "0,00"))
        outras_retencoes = etree.SubElement(valores, "OutrasRetencoes")
        outras_retencoes.text = str(dados.get("outras_retencoes", "0,00"))
        valor_iss_servico = etree.SubElement(valores, "ValorIss")
        valor_iss_servico.text = str(dados.get("valorIss", "0,00"))
        aliquota_servico = etree.SubElement(valores, "Aliquota")
        aliquota_servico.text = str(dados.get("aliquota"))
        desconto_incondicionado = etree.SubElement(valores, "DescontoIncondicionado")
        desconto_incondicionado.text = str(dados.get("desconto_incondicionado", '0.00'))
        desconto_condicionado = etree.SubElement(valores, "DescontoCondicionado")
        desconto_condicionado.text = str(dados.get("descIncondicional", "0,00"))

        # Tomador Servico
        tomador_servico = etree.SubElement(inf_declaracao_prestacao_servico, "TomadorServico")
        id_tomador = etree.SubElement(tomador_servico, "IdentificacaoTomador")
        id_tomador.text = dados.get("IdentificacaoTomador", "")
        cpf_cnpj_tomador = etree.SubElement(id_tomador, "CpfCnpj")
        cpf_cnpj_tomador.text = dados.get("cpfCnpjTomador", "")
        
        endereco_tomador = etree.SubElement(tomador_servico, "Endereco")
        logradouro_tomador = etree.SubElement(endereco_tomador, "Endereco")
        logradouro_tomador.text = dados.get("enderecoTomador", "")
        numero_tomador = etree.SubElement(endereco_tomador, "Numero")
        numero_tomador.text = dados.get("numeroTomador", "")
        bairro_tomador = etree.SubElement(endereco_tomador, "Bairro")
        bairro_tomador.text = dados.get("bairroTomador", "")
        complemento_tomador = etree.SubElement(endereco_tomador, "Complemento")
        complemento_tomador.text = dados.get("complementoTomador", "")
        cep_tomador = etree.SubElement(endereco_tomador, "Cep")
        cep_tomador.text = dados.get("cepTomador", "")

        rps = etree.SubElement(inf_declaracao_prestacao_servico, "Rps")
        identificacao_rps = etree.SubElement(rps, "IdentificacaoRps")
        
        numero_rps = etree.SubElement(identificacao_rps, "Numero")
        numero_rps.text = dados.get("numeroRps")

        serie = etree.SubElement(identificacao_rps, "Serie")
        serie.text = dados.get("serieRps")

        tipo = etree.SubElement(identificacao_rps, "Tipo")
        tipo.text = str(dados.get("tipo_recolhimento", ""))

        data_emissao_rps = etree.SubElement(identificacao_rps, "DataEmissaoRps")
        data_emissao_rps.text = dados.get("dataEmissaoRps")

        status = etree.SubElement(identificacao_rps, "Status")
        status.text = str(dados.get("status_rps", ""))
        servico = etree.SubElement(inf_declaracao_prestacao_servico, "Servico")

        responsavel_retencao = etree.SubElement(servico, "ResponsavelRetencao")
        responsavel_retencao.text = dados.get("responsavel_retencao", "")

        codigo_cnae = etree.SubElement(servico, "CodigoCnae")
        codigo_cnae.text = dados.get("codigo_cnae", "")

        codigo_tributacao_municipio = etree.SubElement(servico, "CodigoTributacaoMunicipio")
        codigo_tributacao_municipio.text = dados.get("codigo_tributacao_municipio", "")

        codigo_nbs = etree.SubElement(servico, "CodigoNbs")
        codigo_nbs.text = dados.get("codigo_nbs")

        codigo_municipio_servico = etree.SubElement(servico, "CodigoMunicipio")
        codigo_municipio_servico.text = dados.get("codigo_municipio_servico", "")

        codigo_pais = etree.SubElement(servico, "CodigoPais")
        codigo_pais.text = str(dados.get("codigo_pais",""))

        identificacao_nao_exigibilidade = etree.SubElement(servico, "IdentifNaoExigibilidade")
        identificacao_nao_exigibilidade.text = dados.get("identificacao_nao_exigibilidade")

        municipio_incidencia = etree.SubElement(servico, "MunicipioIncidencia")
        municipio_incidencia.text = str(dados.get("municipio_incidencia", ""))

        numero_processo = etree.SubElement(servico, "NumeroProcesso")
        numero_processo.text = dados.get("numero_processo")

        # Identificação do prestador
        prestador = etree.SubElement(inf_declaracao_prestacao_servico, "Prestador")
        cpf_cnpj = etree.SubElement(prestador, "CpfCnpj")
        cpf = etree.SubElement(cpf_cnpj, "Cpf")
        cpf.text = dados.get("prestador_cpf")

        cnpj = etree.SubElement(cpf_cnpj, "Cnpj")
        cnpj.text = dados.get("cpfCnpjPrestador")

        inscricao_municipal = etree.SubElement(prestador, "InscricaoMunicipal")
        inscricao_municipal.text = dados.get("inscricaoMunicipalPrestador")

        # Identificação do tomador
        # Gerando o XML em formato string
        xml_str = etree.tostring(root, pretty_print=True, encoding="UTF-8").decode("utf-8")
        print(f"XML gerado: {xml_str}")
        
        # Retorna o XML gerado
        return xml_str
    





        