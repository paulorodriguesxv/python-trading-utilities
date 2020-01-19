import pdftotext
import csv
import argparse
from collections import defaultdict

class ENotaNaoBovespaModal(Exception):
    pass


def split_trade(trade):
    return [x.strip() for x in trade.split("    ") if x != '']


def is_bovespa(page):
    _is_modal = False
    _is_bovespa = False
    for index, line in enumerate(page.split('\n')):
        if "MODAL" in line:
            _is_modal = True

        if "VISTA" in line:
            _is_bovespa = True

        if _is_bovespa and _is_modal:
            break

    return _is_bovespa and _is_modal


def _string_to_float(value):
    return float(value.replace('.', '').replace(',', '.'))


def get_preco_custo(
    tipoOperacao,
    preco,
    qtde,
    emol_tax=0.000049,
    liq_tax=0.000275,
    corr_tax=2.49):

    vl_custo = (preco * emol_tax) + (preco * liq_tax) + (corr_tax / qtde)

    if tipoOperacao == 'C':
        return (preco + vl_custo) * (-1)
    else:
        return preco - vl_custo


def get_trades(data, trades_index, page):
    trades = []

    trade_list = page[trades_index[0]:trades_index[-1]]

    for trade in trade_list:
        _trade = split_trade(trade)

        tipoOperacao = _trade[0].split(" ")[-4]
        
        qtde = _string_to_float(_trade[2])
        preco = convert_value(_trade[3])
        valor = convert_value(_trade[4])

        custo_preco = get_preco_custo(tipoOperacao, preco, qtde)
        custo_valor = custo_preco * qtde

        trades.append(
            dict(
                data=data,
                tipoOperacao=tipoOperacao,
                ativo=_trade[1],
                qtde=qtde,
                preco=preco,
                valor=valor,
                custo_preco=custo_preco,
                custo_valor=custo_valor
            )
        )

    return trades


def convert_value(value):
    value = value.split('   ')

    if len(value) > 1:
        return _string_to_float(value[0]) * (-1 if value[1] == "D" else 1)
    else:
        return _string_to_float(value[0])


def get_valor(index, page):
    valor = page[index[0]].replace('|', '')
    valor = split_trade(valor)
    valor = valor[-1].split('  ')

    return _string_to_float(valor[0]) * (-1 if valor[1] == "D" else 1)


def get_despesas(despesas_index, page):
    valor = page[despesas_index[0]].replace('|', '')
    valor = split_trade(valor)

    return _string_to_float(valor[-2])


def get_cblc(cblc_index, page):
    valor = page[cblc_index[0]].replace('|', '')
    valor = split_trade(valor)

    return _string_to_float(valor[-2])

def get_total_bovespa(total_bovespa_index, page):
    valor = page[total_bovespa_index[0]].replace('|', '')
    valor = split_trade(valor)

    return _string_to_float(valor[-2])        



def get_valor_negociado(valor_negociado_index, page):
    valor = page[valor_negociado_index[0]].replace('|', '')
    valor = split_trade(valor)
    valor = valor[-2].split('  ')

    return _string_to_float(valor[0]) * (-1 if valor[1] == "D" else 1)


def get_valor_liquido(valor_liquido_index, page):
    return get_valor(valor_liquido_index, page)


def get_data_pregao(index, page):
    return page[index[0]].split(" ")[-1]


def create_index(page):
    trades_index = []
    despesas_index = []
    valor_negociado_index = []
    valor_liquido_index = []
    data_pregao_index = []
    cblc_index = []
    total_bovespa_index = []

    reading_trades = False

    for index, line in enumerate(page):
        line = line.lower()
        if reading_trades:
            trades_index.append(index)

        if not reading_trades:
            reading_trades = ("negociação" in line)
        else:
            reading_trades = ("resumo dos negócios" not in line)

        if "total corretagem/despesa" in line:
            despesas_index.append(index)

        if "taxa de liquidação" in line:
            cblc_index.append(index)

        if "total bovespa" in line:
            total_bovespa_index.append(index)

        """
        if "Ajuste Day Trade" in line:
            valor_negociado_index.append(index+1)

        if "Total líquido da nota" in line:
            valor_liquido_index.append(index+1)
        """
        if "data pregão" in line:
            data_pregao_index.append(index+1)

    return dict(
        trades=trades_index,
        despesas=despesas_index,
        cblc=cblc_index,
        total_bovespa=total_bovespa_index,
        valor_negociado=valor_negociado_index,
        valor_liquido=valor_liquido_index,
        data_pregao=data_pregao_index)


def extract_data(pdf):
    documents = []
    for page_number, page in enumerate(pdf, start=1):
        if not is_bovespa(page):
            raise ENotaNaoBovespaModal

        page = page.split('\n')

        page_index = create_index(page)

        data_pregao = get_data_pregao(page_index['data_pregao'], page)
        
        trades = get_trades(
            data_pregao,
            page_index['trades'], page)

        documents.extend(trades)

    return documents


def filter_compra(x):
    return x["tipoOperacao"] == 'C'


def filter_venda(x):
    return x["tipoOperacao"] == 'V'


def group_by_trade_type(trade_list):
    trades = []
    for daily_trades in trade_list.values():
        for trade in daily_trades:
            trades.append(trade)

    compras = list(filter(filter_compra, trades))
    vendas = list(filter(filter_venda, trades))

    return {'C': compras, 'V': vendas}


def group_by_stock(trade_list):
    trades = defaultdict(lambda: [])
    for trade in trade_list:
        trades[trade['ativo']].extend([trade])

    return trades

def get_trade_results(trades):
    profit = 0
    for trade in trades:
        profit += (trade['custo_valor'])

    print(trade['ativo'])
    print(profit)


def create_tradelist(filename: str):
    with open(filename, "rb") as f:
        pdf = pdftotext.PDF(f)
        tradelist = extract_data(pdf)

        # trade_list = group_by_stock(trade_list)
        # for trade_stock in trade_list.values():
        #    get_trade_results(trade_stock)
        #    print(trade_stock)
        #    print("=====================")

    return tradelist


def save_as_csv(tradelist: list):
    csv_columns = ['data', 'tipoOperacao', 'ativo', 'qtde', 'preco']
    csv_file = "./operacoes.csv"
    try:
        with open(csv_file, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for data in tradelist:
                row = {x: data.get(x) for x in csv_columns}
                writer.writerow(row)
    except IOError:
        print("I/O error")


parser = argparse.ArgumentParser(description='Processar notas de corretagem do ModalMais.')
parser.add_argument('files', type=str, nargs='+')

if __name__ == "__main__":
    args = parser.parse_args()

    tradelist = []
    for filename in args.files:
        tradelist.extend(create_tradelist(filename))
    
    save_as_csv(tradelist)