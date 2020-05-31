import requests
import math
from operator import itemgetter
import os
# Definitions:
global assetName
assetName = 'AUD_JPY'  # TODO: Update once changing currency pair
base_url = 'https://api-fxpractice.oanda.com/v3/accounts/'  # TODO: Update once using real account
def getCredentials():  # Gets the authorization credentials
    global assetName
    global apiKey
    global accountID
    global base_url
    global assetName
    apiKey = os.environ.get('oandaKey')
    accountID = os.environ.get('accountID')
    base_url = base_url + accountID
    return apiKey, accountID, base_url, assetName

def makeRequest(types, url, Params, Headers, Body):
    url = url+"?"
    for parameter in Params:
        url += parameter + "=" + Params[parameter] + "&"
    Headers['Content-Type'] = 'application/json'
    response = requests.request(types, url, headers=Headers, data=Body)
    return response.json()


def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.ceil(n * multiplier) / multiplier


def getRsi(response):
    priceLst = []
    for i in response:
        priceLst.append({'upward movement': 0, 'downward movement': 0, 'price': float(i['ask']['c']), 'average upward movement': 0, 'average downward movement': 0, 'RSI': 0})
    count = 0
    for price in priceLst[1:]:
        if price['price'] >= priceLst[count]['price']:
            priceLst[count+1]['upward movement'] += price['price'] - priceLst[count]['price']
        else:
            priceLst[count+1]['downward movement'] += priceLst[count]['price'] - price['price']
        count += 1
    first_avg_upward, first_avg_downward = 0, 0
    for i in priceLst[0:10]:
        first_avg_upward += i['upward movement']
        first_avg_downward += i['downward movement']
    del priceLst[:10]
    priceLst[0]['average upward movement'] = first_avg_upward/10
    priceLst[0]['average downward movement'] = first_avg_downward/10
    count = 0
    for price in priceLst[1:]:
        price['average upward movement'] = ((priceLst[count]['average upward movement']*9)+price['upward movement'])/10
        price['average downward movement'] = ((priceLst[count]['average downward movement'] * 9) + price['downward movement']) / 10
        count += 1
    return 100 - 100 / (1 + (priceLst[-1]['average upward movement'] / priceLst[-1]['average downward movement']))


# INPUT: assetName(e.g.EUR_USD)
# OUTPUT: {UNIX, averageAsk, averageBid, RSIValue}
# Note: Intended to run every 5 Minutes
def getData(assetTraded):
    response = makeRequest('GET', base_url + '/instruments/' + assetTraded + '/candles', {"price": "A", "granularity": 'M15', "count": '500'}, {'Authorization': apiKey, 'Accept-Datetime-Format': 'UNIX'}, "{}")['candles']
    rsiResponse = getRsi(response[:-1])
    responseAsk = response[-3:-1]
    priceData = dict()
    priceData['time'] = responseAsk[1]['time']
    colour = ""
    if float(responseAsk[1]['ask']['o']) > float(responseAsk[1]['ask']['c']):
        priceData['avgAsk'] = float(responseAsk[0]['ask']['c'])  # With the purpose of finding the highest of a red candle
        priceData['lowest'] = float(responseAsk[1]['ask']['c'])  # With the purpose of finding the lowest of a red candle
        priceData['colour'] = 'red'
    elif float(responseAsk[1]['ask']['o']) <= float(responseAsk[1]['ask']['c']):
        priceData['avgAsk'] = float(responseAsk[1]['ask']['c'])  # With the purpose of finding the highest of a green candle
        priceData['lowest'] = float(responseAsk[0]['ask']['c'])  # With purpose of finding the lowest of a green candle
        priceData['colour'] = 'green'
    if colour == 'green':  # if green
        priceData['rsi'] = rsiResponse
    elif colour == 'red' and (float(responseAsk[0]['ask']['o']) <= float(responseAsk[0]['ask']['c'])):  # if red and previous one is green
        priceData['rsi'] = getRsi(response[:-2])
    else:  # if previous is red and current is red
        priceData['rsi'] = rsiResponse
    return priceData


#  OUTPUT: (Number of units to trade)
def noUnits():
    response = makeRequest('GET', base_url, '', {'Content-Type': 'application/json', 'Authorization': apiKey}, '')
    percent5Acct = float(response['account']["balance"]) #/20
    url = "https://api-fxpractice.oanda.com/v3/accounts/"+accountID+"/instruments/AUD_SGD/candles?price=A&granularity=M15&count=1"
    payload = {}
    headers = {
        'Authorization': apiKey,
        'Accept-Datetime-Format': 'UNIX'
    }
    rate = requests.request("GET", url, headers=headers, data=payload).json()
    rate = rate["candles"][0]["ask"]["o"]
    return math.ceil(percent5Acct/float(rate))


# INPUT: ID of order to close
def closeOrder(ID): return makeRequest("PUT", base_url+"/trades/"+str(ID)+"/close", {}, {"Authorization": apiKey}, "")


# Aim: Calculates the take profit value in a divergence
# INPUT: dataset - List of Dictionary{UNIX, averageAsk, averageBid, RSIValue, lowest}, largest2['time']
def takeProfitCalculator(dataSet, largest2Time):
    listData = []
    count = 0
    for data in dataSet:
        if float(data['time']) == float(largest2Time):
            listData = dataSet[count:]
            break
        count += 1
    sortedList = sorted(listData, key=itemgetter('lowest'))
    return (sortedList[0])['lowest']


# INPUT: assetName(e.g.EUR_USD), units(e.g.3), order(e.g.Buy), price(price at which order is places), takeProfit, stopLoss
# OUTPUT: (Response of OANDA)
def marketOrder(assetName, units, order, takeProfit, stopLoss):
    if order == 'buy': pass
    else: units = -units
    body = '{"order": {"stopLossOnFill": {"price": "'+str(round(stopLoss,5))+'"},"takeProfitOnFill": {"price": "'+str(round(takeProfit, 5))+'"},"timeInForce": "FOK","instrument": "'+assetName+'","units": "'+str(units*20)+'","type": "MARKET","positionFill": "DEFAULT"}}'
    response = makeRequest('POST', base_url + '/orders', '', {'Authorization': apiKey, 'Accept-Datetime-Format': 'UNIX'}, body)
    print(response)
    console = open('console.txt', 'a')
    console.write('\n'+str(response))
    console.close()
    if "orderCreateTransaction" not in response:
        return 0
    else:
        response = int(response["orderCreateTransaction"]["id"])
        return response
