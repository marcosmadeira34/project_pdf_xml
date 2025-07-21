#!/usr/bin/env python3

"""
------------------------------------------------------------------------------
Script     : fatura-extractor
Description: extrai da Fatura eletrônica em .PDF informações e coloca em .csv
Version    : 0.1.0
Date       : 03/05/2023
Author     : Braulio Henrique Marques Souto <braulio@disroot.org>
License    : BSD-3-Clause
------------------------------------------------------------------------------

Copyright 2023 Braulio Henrique Marques Souto <braulio@disroot.org>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software
without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
------------------------------------------------------------------------------
"""

import json
import os
import time

import requests

"""
Variáveis obrigatorias que precisam passar os valores:
client_id = "xxxxxxxx"
client_secret = "xxxxxxxxxxxx"
cnpj_customer = "xxxxxxxxxxxxxx"
x_integration_key_customer = "xxxxxx"
cnpj_user = "xxxxxxxxxxxxx"

Essas duas variáveis são fixas então pode aproveitar seu valor no case de usar um função separada
se for usar o main, não precisa pois já esta colocada dentro da funcao main
cookie = "did=s%3Av0%3A145b8a90-ea57-11eb-ae8a-877f15a4a518.QhUcTCGsMP28yWAB%2BYsUUZ5Gw4Srxf%2F0IDRkKPUQQHs; 
did_compat=s%3Av0%3A145b8a90-ea57-11eb-ae8a-877f15a4a518.QhUcTCGsMP28yWAB%2BYsUUZ5Gw4Srxf%2F0IDRkKPUQQHs"
audience = "409f91f6-dc17-44c8-a5d8-e0a1bafd8b67"
"""


# Funcoes --------------------------------------------------------------------
def gen_token(client_id, client_secret, cookie, audience):
    """1"""
    valid = check_time_token("token.json")
    if valid:
        print("O arquivo de token ainda está valido, não foi necessário gerar um token novo")
        pass
    else:
        url = "https://auth.thomsonreuters.com/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": audience,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
            "Authorization": f"Basic {client_id}:{client_secret}",
        }
        response = requests.post(url, data=payload, headers=headers)
        if response.status_code == 200:
            reponse_json = response.json()
            gen_json("token", reponse_json)
        else:
            print(
                f"Houve um problema com a requisição na criação do token, seu status foi {response.status_code}"
            )


def get_token():
    with open("token.json", "r") as token_file:
        data = json.load(token_file)
    token = data["access_token"]
    return token





def check_customer(x_integration_key, cnpj_user, cnpj_customer):
    """2"""
    token = get_token()
    url = "https://api.onvio.com.br/dominio/integration/v1/activation/info"
    headers = {"Authorization": f"Bearer {token}", "x-integration-key": x_integration_key}
    response = requests.get(url, headers=headers)
    response_json = response.json()
    if (
        cnpj_user == response_json["accountantOfficeNationalIdentity"]
        and cnpj_customer == response_json["clientNationalIdentity"]
    ):
        return True
    else:
        return False


def check_file(file):
    if file:
        name, extension = os.path.splitext(file)
        print(name)
        print(extension)
        if extension == ".xml" or extension == ".XML":
            print("Arquivo valido")
            return file, name
        else:
            print("Arquivo não é um xml válido")
    else:
        print("É preciso ter um arquivo como parâmetro para ser verificado")


def check_send_xml(id_send, x_integration_key, xml_name):
    """5"""
    token = get_token()
    url = "https://api.onvio.com.br/dominio/invoice/v3/batches/"
    id_send = id_send
    headers = {"x-integration-key": x_integration_key, "Authorization": f"Bearer {token}"}
    params = {}
    response = requests.get(url + id_send, headers=headers, params=params)
    if response.status_code == 200:
        response_json = response.json()
        msg_final = response_json["filesExpanded"][0]["apiStatus"]["message"]
        gen_json(f"check_send_xml-{xml_name}", response_json)
        if msg_final == "Arquivo armazenado na API":
            return True
        else:
            print(
                f"A requisição de veficação teve sucesso, poré o processamento não, foi retornado a seguinte mensagem da API:\n\n\t{msg_final}\n"
            )
            return False
    else:
        print(f"Erro na requisição: seu status foi {response.status_code}")
        return False


def check_time_token(file):
    if os.path.exists(file):
        info_arquivo = os.stat(file)
        data_modify = info_arquivo.st_mtime
        diff_time = (time.time() - data_modify) / 3600
        if diff_time < 24:
            print(f"O arquivo {file} foi criado nas últimas 24 horas.")
            return True
        else:
            print(f"O arquivo {file} foi criado há mais de 24 horas. Será gerado novo token")
            return False
    else:
        print(f"O arquivo {file} não foi encontrado")
        return False


def gen_integration_key(x_integration_key):
    """3"""
    token = get_token()
    url = "https://api.onvio.com.br/dominio/integration/v1/activation/enable"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-integration-key": x_integration_key,
    }
    response = requests.post(url, headers=headers)
    response_json = response.json()
    return response_json["integrationKey"]


def gen_json(file_name, reponse_in_json):
    with open(f"{file_name}.json", "w") as f:
        json.dump(reponse_in_json, f)





def send_xml(x_integration_key, file_xml):
    """4"""
    token = get_token()
    url = "https://api.onvio.com.br/dominio/invoice/v3/batches"
    headers = {"x-integration-key": x_integration_key, "Authorization": f"Bearer {token}"}
    data = {
        "file[]": (file_xml, open(file_xml, "rb"), "application/xml"),
        "query": ('{"boxe/File": false}', "application/json"),
    }
    response = requests.post(url, headers=headers, files=data)
    if response.status_code == 200:
        response_json = response.json()
        return response_json["id"]
    else:
        print(
            f"Houve um problema com a requisição no envio do xml, seu status foi {response.status_code}"
        )


# MAIN -----------------------------------------------------------------------
def main(client_id, client_secret, x_integration_key_customer, cnpj_user, cnpj_customer, file_xml):
    cookie = "did=s%3Av0%3A145b8a90-ea57-11eb-ae8a-877f15a4a518.QhUcTCGsMP28yWAB%2BYsUUZ5Gw4Srxf%2F0IDRkKPUQQHs; did_compat=s%3Av0%3A145b8a90-ea57-11eb-ae8a-877f15a4a518.QhUcTCGsMP28yWAB%2BYsUUZ5Gw4Srxf%2F0IDRkKPUQQHs"
    audience = "409f91f6-dc17-44c8-a5d8-e0a1bafd8b67"

    # Supondo que file_xml pode ser uma lista de arquivos XML para envio em lote
    if isinstance(file_xml, list):
        resultados = []
        for single_file_xml in file_xml:
            arquivo_xml, nome_arquivo_xml = check_file(single_file_xml)
            if arquivo_xml:
                gen_token(client_id, client_secret, cookie, audience)
                customer = check_customer(x_integration_key_customer, cnpj_user, cnpj_customer)
                if customer:
                    integrationKey = gen_integration_key(x_integration_key_customer)
                    id_send = send_xml(integrationKey, arquivo_xml)
                    if check_send_xml(id_send, integrationKey, nome_arquivo_xml):
                        resultados.append((single_file_xml, True))
                    else:
                        resultados.append((single_file_xml, False))
                else:
                    print(
                        "O cnpj do usuario ou do cliente está diferente do retornado pela API, verifique no cadastro se estão corretos."
                    )
                    resultados.append((single_file_xml, False))
            else:
                print(f"Arquivo {single_file_xml} no formato inválido")
                resultados.append((single_file_xml, False))
        return resultados
    else:
        arquivo_xml, nome_arquivo_xml = check_file(file_xml)
        if arquivo_xml:
            gen_token(client_id, client_secret, cookie, audience)
            customer = check_customer(x_integration_key_customer, cnpj_user, cnpj_customer)
            if customer:
                integrationKey = gen_integration_key(x_integration_key_customer)
                id_send = send_xml(integrationKey, arquivo_xml)
                if check_send_xml(id_send, integrationKey, nome_arquivo_xml):
                    return True
            else:
                print(
                    "O cnpj do usuario ou do cliente está diferente do retornado pela API, verifique no cadastro se estão corretos."
                )
                return False
        else:
            print("Arquivo no formato inválido")
            return False
