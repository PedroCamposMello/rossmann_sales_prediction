import os
import requests
import json
import pandas as pd

from flask import Flask, request, Response

# O telegram-bot foi projetado para trabalhar em conjunto com o webapp hospedado em um servidor em nuvem.

# Constantes
TOKEN = 'XXXXXXX' # <- Inserir o token do bot de telegram criado pelo BotFather

## Webhook - IMPORTANTE - O comando webhook deve ser executado no browser uma vez apra fazer a configuração com o app hospedado no servidor!
#https://api.telegram.org/botXXXXXXX/setWebhook?url=https://DOMINIO
#

def send_message( chat_id, text ):
    url = 'https://api.telegram.org/bot{}/'.format( TOKEN ) 
    url = url + 'sendMessage?chat_id={}'.format( chat_id ) 

    r = requests.post( url, json={'text': text } )
    print( 'Status Code {}'.format( r.status_code ) )

    return None


def load_dataset( store_id ):
    # Carregar os datasets
    df_production   = pd.read_csv( 'data/production.csv', low_memory=False )
    df_store        = pd.read_csv( 'data/store.csv', low_memory=False )

    # merge
    df_test = pd.merge( df_production, df_store, how='left', on='Store' )

    # Escolha de lojas para entrarem na previsão
    df_test = df_test[df_test['Store'] == store_id]

    if not df_test.empty:
        # Remover dias de lojas fechadas
        df_test = df_test[df_test['Open'] != 0]
        df_test = df_test[~df_test['Open'].isnull()]

        # Converter Dataframe para json
        data = json.dumps( df_test.to_dict( orient='records' ) )

    else:
        data = 'error'

    return data


def predict( data ):
    # API Call
    # Na url inserir https://DOMÍNIO_DO_APP/rossmann/predict
    url = 'https://XXXXXXXXX/rossmann/predict'
    header = {'Content-type': 'application/json' }
    data = data

    r = requests.post( url, data=data, headers=header )
    print( 'Status Code {}'.format( r.status_code ) )

    d1 = pd.DataFrame( r.json(), columns=r.json()[0].keys() )

    return d1


def parse_message( message ):
    chat_id     = message['message']['chat']['id']
    store_id    = message['message']['text']

    store_id = store_id.replace( '/', '' )

    try:
        store_id = int( store_id )

    except ValueError:
        store_id = 'error'

    return chat_id, store_id


# API
app = Flask( __name__ )

@app.route( '/', methods=['GET', 'POST'] )
def index():
    if request.method == 'POST':
        message = request.get_json()

        chat_id, store_id = parse_message( message )

        if store_id != 'error':
            # Carregar dados
            data = load_dataset( store_id )

            if data != 'error':
                # previsão
                d1 = predict( data )

                # Cálculo da previsão para a loja
                d2 = d1[['Store', 'predictions']].groupby( 'Store' ).sum().reset_index()
                
                # Enviar mensagem
                msg = 'Store Number {} will sell R${:,.2f} in the next 6 weeks'.format(
                                                                                       d2['Store'].values[0],
                                                                                       d2['predictions'].values[0] ) 

                send_message( chat_id, msg )
                return Response( 'Ok', status=200 )

            else:
                send_message( chat_id, 'Store Not Available' )
                return Response( 'Ok', status=200 )

        else:
            send_message( chat_id, 'Store ID is Wrong' )
            return Response( 'Ok', status=200 )


    else:
        return '<h1> Rossmann Telegram BOT </h1>'


if __name__ == '__main__':
    port = os.environ.get( 'PORT', 5000 )
    app.run( host='0.0.0.0', port=port )
