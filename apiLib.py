#!/usr/bin/python3

import requests
import math
from operator import itemgetter
import time
from RSI import *
import os

# Definitions:
global assetName

# TODO: Tweak the following variables
candle_time_frame = 3600  # Number of seconds per candle
timetowait = 3600  # Number of seconds to wait before execution


def getCredentials():  # Gets the authorization credentials
    global assetName
    global apiKey
    global accountID
    global base_url
    global assetName
    assetName = os.environ['pair']
    base_url = 'https://api-fxpractice.oanda.com/v3/accounts/'
    apiKey = os.environ['apiKey'].strip()
    accountID = os.environ['accountID'].strip()
    base_url = base_url + accountID
    return apiKey, accountID, base_url, assetName


def makeRequest(types, url, Params, Headers, Body):
    while True:
        try:
            url = url + "?"
            for parameter in Params:
                url += parameter + "=" + Params[parameter] + "&"
            Headers['Content-Type'] = 'application/json'
            response = requests.request(types, url, headers=Headers, data=Body)
            return response.json()
        except:
            continue
        else:
            break


def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.ceil(n * multiplier) / multiplier



# INPUT: assetName(e.g.EUR_USD)
# OUTPUT: {UNIX, averageAsk, averageBid, RSIValue}
# Note: Intended to run every 5 Minutes
def getData(assetTraded):
    response = {}
    assetTraded = assetTraded.strip()
    while 'candles' not in response:
        response = makeRequest('GET', base_url + '/instruments/' + assetTraded + '/candles',
                               {"price": "A", "granularity": 'H1', "count": '500'},
                               {'Authorization': apiKey, 'Accept-Datetime-Format': 'UNIX'}, "{}")
    response = response['candles']  # TODO: Manually change the candle granuality
    response = openclossolver(response)
    rsiResponse = rsisol(response[:-1])[-1]
    responseAsk = response[-3:-1]
    priceData = dict()
    priceData['time'] = responseAsk[1]['time']
    colour = ""
    if float(responseAsk[1]['ask']['o']) > float(responseAsk[1]['ask']['c']):
        priceData['avgAsk'] = float(
            responseAsk[0]['ask']['c'])  # With the purpose of finding the highest of a red candle
        priceData['lowest'] = float(
            responseAsk[1]['ask']['c'])  # With the purpose of finding the lowest of a red candle
        priceData['colour'] = 'red'
        colour = "red"
    elif float(responseAsk[1]['ask']['o']) <= float(responseAsk[1]['ask']['c']):
        priceData['avgAsk'] = float(
            responseAsk[1]['ask']['c'])  # With the purpose of finding the highest of a green candle
        priceData['lowest'] = float(responseAsk[0]['ask']['c'])  # With purpose of finding the lowest of a green candle
        priceData['colour'] = 'green'
        colour = "green"
    if colour == 'green':  # if green
        priceData['rsi'] = rsiResponse
    elif colour == 'red' and (
            float(responseAsk[0]['ask']['o']) <= float(responseAsk[0]['ask']['c'])):  # if red and previous one is green
        priceData['rsi'] = rsisol(response[:-2])[-1]
    else:  # if previous is red and current is red
        priceData['rsi'] = rsiResponse
    return priceData


#  OUTPUT: (Number of units to trade)
def noUnits():
    response = makeRequest('GET', base_url, '', {'Content-Type': 'application/json', 'Authorization': apiKey}, '')
    percent5Acct = float(response['account']["balance"])  # /20
    initial_currency = assetName.split("_")[0] + "_SGD"
    url = "https://api-fxpractice.oanda.com/v3/accounts/" + accountID + "/instruments/" + initial_currency + "/candles?price=A&granularity=H1&count=1"
    payload = {}
    headers = {
        'Authorization': apiKey,
        'Accept-Datetime-Format': 'UNIX'
    }
    rate = requests.request("GET", url, headers=headers, data=payload).json()
    rate = rate["candles"][0]["ask"]["o"]
    return math.ceil(percent5Acct / float(rate))


# INPUT: ID of order to close
def closeOrder(ID): return makeRequest("PUT", base_url + "/trades/" + str(ID) + "/close", {}, {"Authorization": apiKey},
                                       "")


# Aim: Calculates the take profit value in a divergence
# INPUT: dataset - List of Dictionary{UNIX, averageAsk, averageBid, RSIValue, lowest}, largest2['time']
def takeProfitCalculator(dataSet, largest2Time):
    listData = []
    count = 0
    for data in dataSet:
        if float(data['time']) == (float(largest2Time)):
            listData = dataSet[count:]
            break
        count += 1
    sortedList = sorted(listData, key=itemgetter('lowest'))
    return (sortedList[0])['lowest'], (sortedList[0])['time']


# INPUT: assetName(e.g.EUR_USD), units(e.g.3), order(e.g.Buy), price(price at which order is places), takeProfit, stopLoss
# OUTPUT: (Response of OANDA)
def marketOrder(assetName, units, order, price, takeProfit, stopLoss):
    if order == 'buy':
        pass
    else:
        units = -units
    body = '{"order": {"stopLossOnFill": {"price": "' + str(
        round(stopLoss, 5)) + '"},"takeProfitOnFill": {"price": "' + str(
        round(takeProfit, 5)) + '"},"timeInForce": "GTD","instrument": "' + assetName + '","units": "' + str(int(
        units * (20/22))) + '","type": "MARKET_IF_TOUCHED","positionFill": "DEFAULT","price": "' + str(
        price) + '","gtdTime": "' + str(int(time.time() + timetowait)) + '"}}'
    response = makeRequest('POST', base_url + '/orders', '',
                           {'Authorization': apiKey, 'Accept-Datetime-Format': 'UNIX'}, body)
    print(response)
    #  console = open('console.txt', 'a')
    #  console.write('\n' + "Gradient Down: " + str(gradient_down))
    #  console.write('\n' + "Gradient Up: " + str(gradient_up))
    #  console.write('\n' + str(response))
    #  console.close()
    if "orderCreateTransaction" not in response:
        return 0
    else:
        response = int(response["orderCreateTransaction"]["id"])
        return response


def openclossolver(response):
    index = 1
    for candle in response[1:]:
        response[index]['ask']['o'] = response[index-1]['ask']['c']
        index += 1
    return response

def rsisol(response):
    lst = []
    for i in response:
        lst.append(float(i['ask']['c']))
    return rsi(np.array(lst))


apiKey, accountID, base_url, assetName = getCredentials()
