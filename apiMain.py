#!/usr/bin/python3

from apiLib import *
import time
from operator import itemgetter
import requests
global tradeIDs, base_url, assetName, dataSet


apiKey, accountID, base_url, assetName = getCredentials() # Initializes Oanda Login credentials from apiCredentials.txt file
dataSet = [] # List of Dictionary [{UNIX, averageAsk, averageBid, RSIValue}]
orders = {} # Dictionary containing orders with their respective execution time
get1HrData = []
dataSet = [{'time': 0, 'avgBid': 0, 'avgAsk': 0, 'rsi': 0, 'colour': 'red'}, {'time': 0, 'avgBid': 0, 'avgAsk': 0, 'rsi': 0, 'colour': 'red'}]
orderPlaced = {}


max_loss_percentage = 3  # TODO: Program in the maximum loss percentage
max_profit_percentage = 100  # Because we remove 9% max profit
min_rsi_difference = 0
minimum_candle_difference = 3  # TODO: Program in the minimum candle difference
maximum_candle_difference = 18
candle_time_frame = 3600  # Number of seconds per candle
minimum_profit = 6  # TODO: Program in the minimum profit percentage
Rsi_level = 70  # TODO: 50, 60, 70, 80, 90

print('Currency pair:', assetName)
print('Starting... Will start at exact 1 Hour interval')
while True:  # Code to start exact at time 0 mins, 5 seconds
    if time.gmtime()[5] == 5 and time.gmtime()[4] == 0:  # TODO: Tweak this based on candle time frame used
        break

while True:
    data_to_add = getData(assetName)
    while data_to_add['time'] == dataSet[-1]['time']:
        data_to_add = getData(assetName)
    if data_to_add['colour'] == 'red':
        isRed = True
    else:
        isRed = False
    dataSet.append(data_to_add)  # Adds latest data set on the bottom
    print(dataSet)
    #  console = open('console.txt', 'a')
    #  console.write('\n' + str(dataSet))
    #  console.close()
    divergenceFound = False
    count = 1
    largest = dataSet[-1]  # Latest block
    leave = False
    if not isRed:
        box = [largest]  # Programmed in descending order in terms of time
        if sorted(dataSet, key=itemgetter('avgAsk'))[-1] == largest:
            largest2 = sorted(dataSet, key=itemgetter('avgAsk'))[-2]
            if float(largest['time']) - float(largest2['time']) < minimum_candle_difference*candle_time_frame:
                largest2 = sorted(dataSet, key=itemgetter('avgAsk'))[-3]
            if (largest2['rsi'] - min_rsi_difference) >= largest['rsi']:
                divergenceFound = True
                print('Found falling RSI: ', largest['rsi'], ',', largest2['rsi'])
                #  console = open('console.txt', 'a')
                #  console.write('\n' + 'Found falling RSI: ' + str(largest['rsi']) + ', ' + str(largest2['rsi']))
                #  console.close()
                leave = True
        if not leave:
            for candle in dataSet[::-1][1:]:
                if dataSet[::-1][1]['avgAsk'] > largest['avgAsk'] or dataSet[::-1][2]['avgAsk'] > largest['avgAsk']:  # Base Case 1: 1st or 2nd candle before main candle is more
                    break
                if candle['avgAsk'] > largest['avgAsk']:  # Base Case 2: Candles avgAsk is more than "largest"
                    break
                if candle['colour'] == 'red':  # ignore reds
                    pass
                else:  # Colour is green
                    if count < minimum_candle_difference:
                        pass
                    else:
                        box.append(candle)
                        box_sorted = sorted(box, key=itemgetter('avgAsk'))
                        largest2 = box_sorted[-2]
                        # Divergence detection time :>
                        if (largest2['rsi'] - min_rsi_difference) >= largest['rsi']:
                            divergenceFound = True
                            print('Found falling RSI: ', largest['rsi'], ',', largest2['rsi'])
                            #  console = open('console.txt', 'a')
                            #  console.write('\n' + 'Found falling RSI: ' + str(largest['rsi']) + ', ' + str(largest2['rsi']))
                            #  console.close()
                            break
                count += 1
    else:
        pass
    if divergenceFound:
        reasons_why = "Reasons why:" + '\n'
        message = assetName + '\n' + str([largest['time'], largest2['time']]) + '\n' + str([largest['rsi'], largest2['rsi']])
        # Calculating the risk-to-reward
        bidPrice = float(makeRequest('GET', base_url + '/instruments/' + assetName + '/candles', {"price": "B", "granularity": 'H1', "count": '1'}, {'Authorization': apiKey, 'Accept-Datetime-Format': 'UNIX'}, "{}")['candles'][0]['bid']['c'])  # TODO: Manually change granuality
        priceRn = float(makeRequest('GET', base_url + '/instruments/' + assetName + '/candles', {"price": "A", "granularity": 'H1', "count": '1'}, {'Authorization': apiKey, 'Accept-Datetime-Format': 'UNIX'}, "{}")['candles'][0]['ask']['c'])   # TODO: Manually change granuality
        takeProfit, takeProfitTime = takeProfitCalculator(dataSet, largest2['time'])
        stopLoss = bidPrice/(1-(max_loss_percentage/2000))
        stopLoss = (round_up(stopLoss, decimals=len(str(bidPrice).split('.')[1])))
        profit = ((bidPrice - takeProfit)/takeProfit)*2000  # Calculates percentage profit
        loss = ((stopLoss - bidPrice)/bidPrice)*2000  # Calculates percentage loss
        if largest['rsi'] < Rsi_level or largest2['rsi'] < Rsi_level:
            reasons_why = reasons_why + 'RSI < Minimum RSI Level' + '\n'
        if profit < minimum_profit:
            reasons_why = reasons_why + 'Profit < 6%' + '\n'
        if loss > profit:
            reasons_why = reasons_why + 'loss > profit' + '\n'
        double = False
        if profit >= minimum_profit and largest['rsi'] > Rsi_level and largest2['rsi'] > Rsi_level and (float(largest['time'])-float(largest2['time']) >= minimum_candle_difference*3600):
            size = noUnits()  # Determines order size
            timeNow = float(largest['time'])  # The time of the largest
            takeProfit, takeProfitTime = takeProfitCalculator(dataSet, largest2['time'])
            if ((bidPrice - takeProfit)/bidPrice)*2000 > max_profit_percentage:  # Maximising take profit to be 9%
                takeProfit = bidPrice-((max_profit_percentage/2000)*bidPrice)
                takeProfit = (round_up(takeProfit, decimals=len(str(priceRn).split('.')[1])))
            message = 'Time:' + str(timeNow) + '\n' + 'Take profit: ' + str(takeProfit) + '\n' + 'Stop Loss: ' + str(stopLoss) + '\n' + str([largest['time'], largest2['time']]) + str([largest['rsi'], largest2['rsi']]) + '\n' + assetName
            requests.request('GET', 'https://api.telegram.org/bot1285074044:AAGhVLID-dipo5G13zW4iw2Yz2XKnqL-TjE/sendMessage?chat_id=-486754139&text=' + message)
            orderPlaced[marketOrder(assetName, size, "sell", bidPrice, takeProfit, stopLoss)] = largest['time']
            orders[largest['time']] = ('sell', largest2['avgAsk'], takeProfit, largest['avgAsk'], [largest['time'], largest2['time']], [largest['rsi'], largest2['rsi']], [largest['avgAsk'], largest2['avgAsk']])
            double = True
        if double == False:
            requests.request('GET', 'https://api.telegram.org/bot1285074044:AAGhVLID-dipo5G13zW4iw2Yz2XKnqL-TjE/sendMessage?chat_id=-492311350&text=' + message + '\n' + reasons_why)
    # Close after 20 candles
    if len(dataSet) > maximum_candle_difference:
        del (dataSet[0])
    while True:  # Code to start exact at time 0 minutes, 5 seconds
        if time.gmtime()[5] == 5 and time.gmtime()[4] == 0:  # TODO: Tweak this based on candle time frame used
            break
