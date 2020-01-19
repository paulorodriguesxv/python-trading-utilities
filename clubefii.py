import requests
import argparse
import csv
import math

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    'sec-fetch-mode': 'cors',
    'origin': 'https://www.clubefii.com.br',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,it;q=0.6,es;q=0.5,ko;q=0.4',
    'x-requested-with': 'XMLHttpRequest',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'accept': '*/*',
    'referer': 'https://www.clubefii.com.br/',
    'authority': 'www.clubefii.com.br',
    'sec-fetch-site': 'same-origin',
    }

login_url = r'https://www.clubefii.com.br/login'
listar_fundo_url = r'https://www.clubefii.com.br/fundos_listagem?termo={termo}&ordenar=cod&super_compacto=true&considerar_1_item_tela_movimentacao_carteira=true'
inserir_fundo_url = r'https://www.clubefii.com.br/inserir_dado?tipo_dado=carteira_ativo&modo=inserir'
session = requests.Session()


def start_session(username, password):
    r = session.get(login_url,  headers=headers)
    r = session.post(login_url, data={'email': username, 'senha': password}, headers=headers)

    if r.status_code == 200 and r.text != "0":
        return r
    else:
        raise IOError('Usuario ou senha invalidos: ', r.text)


def get_fii_id(fii_code: str):
    fii_dict = {
        'FIIB11': '35',
        'GGRC11': '157',
        'IRDM11': '189',
        'JRDM11': '51',
        'OUJP11': '158',
        'RBVA11': '4',
        'SDIL11': '84',
        'XPML11': '168',
        'LVBI11': '220',
        'MALL11': '173',
        'TGAR11': '159',
    }

    return fii_dict.get(fii_code[0:6])


parser = argparse.ArgumentParser(
    description='Importador de operações para o ClubeFII.')
parser.add_argument('-o', '--oper', nargs=1,
                    help='arquivo com as operações', required=True)
parser.add_argument('-u', '--username', nargs=1,
                    help='Usuário para login no ClubeFII', required=True)
parser.add_argument('-p', '--password', nargs=1, type=str,
                    help='Senha para login no ClubeFII', required=True)                    

if __name__ == "__main__":
    args = parser.parse_args()

    filename = args.oper[0]
    username = args.username[0]
    password = args.password[0]

    r = start_session(username, password)
    codigo_carteira = 0
    with open(filename) as f:
        reader = csv.reader(f)
        operations = list(reader)

        operations.pop(0)

        for operation in operations:

            data = dict(
                cod_car=f'{codigo_carteira}',
                nom_car='FII Carteira 2020',
                cod_fii=get_fii_id(operation[2]),
                cmb_tip='COMPRA' if operation[1] == 'C' else 'VENDA',
                txt_dat=operation[0],
                txt_val_med=(operation[4]),
                txt_cus_ope='0',
                txt_qtd=int(math.floor(float(operation[3]))),
                txt_cat_rec_val_max='0'
            )

            r = session.post(inserir_fundo_url, data=data, headers=headers)
            if r.status_code == 200:
                codigo_carteira = r.text
