from apiLib import *
import time
from operator import itemgetter
import requests
global tradeIDs, base_url, assetName, dataSet

# TODO: Variable initialization
apiKey, accountID, base_url, assetName = getCredentials() # Initializes Oanda Login credentials from apiCredentials.txt file
dataSet = [] # List of Dictionary [{UNIX, averageAsk, averageBid, RSIValue}]
orders = {} # Dictionary containing orders with their respective execution time
get1HrData = []
dataSet = [{'time': 0, 'avgBid': 0, 'avgAsk': 0, 'rsi': 0, 'colour': 'red'}, {'time': 0, 'avgBid': 0, 'avgAsk': 0, 'rsi': 0, 'colour': 'red'}]
orderPlaced = {}

# TODO: Tweak the following variables
assetName = 'AUD_JPY'
max_loss_percentage = 3
max_profit_percentage = 4
min_rsi_difference = 1
minimum_candle_difference = 3
maximum_candle_difference = 18

while True:  # Code to start exact at time 0 mins, 5 seconds
    if time.gmtime()[5] == 5 and time.gmtime()[4] % 15 == 0: break
    print('Starting... Will start at exact 15 mins interval')

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
    console = open('console.txt', 'a')
    console.write('\n' + str(dataSet))
    console.close()
    divergenceFound = False
    count = 1
    largest = dataSet[-1]  # Latest block
    leave = False
    if not isRed:
        box = [largest]  # Programmed in descending order in terms of time
        if sorted(dataSet, key=itemgetter('avgAsk'))[-1] == largest:
            largest2 = sorted(dataSet, key=itemgetter('avgAsk'))[-2]
            if float(largest['time']) - float(largest2['time']) < minimum_candle_difference*15*60:
                largest2 = sorted(dataSet, key=itemgetter('avgAsk'))[-3]
            if (largest2['rsi'] - min_rsi_difference) >= largest['rsi']:
                divergenceFound = True
                print('Found falling RSI: ', largest['rsi'], ',', largest2['rsi'])
                console = open('console.txt', 'a')
                console.write('\n' + 'Found falling RSI: ' + str(largest['rsi']) + ', ' + str(largest2['rsi']))
                console.close()
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
                            console = open('console.txt', 'a')
                            console.write('\n' + 'Found falling RSI: ' + str(largest['rsi']) + ', ' + str(largest2['rsi']))
                            console.close()
                            break
                count += 1
    else:
        pass
    if divergenceFound:
        timeRn = time.time() + 300
        while time.time() < timeRn:
            pass
        message = "A divergence has been found. Check the graph if it could have been a successful trade 🙏" + '\n' + assetName
        requests.request('GET', 'https://api.telegram.org/bot1285074044:AAGhVLID-dipo5G13zW4iw2Yz2XKnqL-TjE/sendMessage?chat_id=-492311350&text=' + message)
        # Calculating the risk-to-reward
        risk = True
        takeProfit = takeProfitCalculator(dataSet, largest2['time'])
        bidPrice = makeRequest('GET', base_url + '/instruments/' + assetName + '/candles', {"price": "B", "granularity": 'M15', "count": '1'}, {'Authorization': apiKey, 'Accept-Datetime-Format': 'UNIX'}, "{}")['candles'][0]['ask']['c']
        stopLoss = bidPrice/(1-(max_loss_percentage/2000))
        stopLoss = (round_up(stopLoss, decimals=len(str(bidPrice).split('.')[1])))
        profit = ((bidPrice - takeProfit)/bidPrice)*200  # Calculates percentage profit
        loss = ((stopLoss - bidPrice)/bidPrice)*200  # Calculates percentage loss
        if loss < profit:  # Potential profits is more than or equal to potential loss
            risk = False
        if float(priceRn) < float(largest['avgAsk']) and (risk is not True):
            size = noUnits()  # Determines order size
            timeNow = float(largest['time'])  # The time of the largest
            priceRn = makeRequest('GET', base_url + '/instruments/' + assetName + '/candles', {"price": "B", "granularity": 'M15', "count": '1'}, {'Authorization': apiKey, 'Accept-Datetime-Format': 'UNIX'}, "{}")['candles'][0]['ask']['c']
            takeProfit = takeProfitCalculator(dataSet, largest2['time'])
            if ((bidPrice - takeProfit)/bidPrice)*200 > 4:  # Maximising take profit to be 4%
                takeProfit = bidPrice-((max_profit_percentage/2000)*bidPrice)
                takeProfit = (round_up(takeProfit, decimals=len(str(priceRn).split('.')[1])))
            message = 'Time:' + str(timeNow) + '\n' + 'Take profit: ' + str(takeProfit) + '\n' + 'Stop Loss: ' + str(round_up(float(largest['avgAsk']), decimals=3) + 0.1) + '\n' + str([largest['time'], largest2['time']]) + str([largest['rsi'], largest2['rsi']]) + '\n' + assetName
            requests.request('GET', 'https://api.telegram.org/bot1285074044:AAGhVLID-dipo5G13zW4iw2Yz2XKnqL-TjE/sendMessage?chat_id=-492311350&text=' + message)
            orderPlaced[marketOrder(assetName, size, "sell", takeProfit, stopLoss)] = largest['time']
            orders[largest['time']] = ('sell', largest2['avgAsk'], takeProfit, largest['avgAsk'], [largest['time'], largest2['time']], [largest['rsi'], largest2['rsi']], [largest['avgAsk'], largest2['avgAsk']])
            # orders format: {time: 'sell', sellingPrice, takeProfit, stopLoss,[Highest,2ndHighest]}
            file = open('data.txt', 'a')
            file.write('\n' + str((largest['time'], largest2['avgAsk'], takeProfit, str(round_up(float(largest2['avgAsk']), decimals=3) + 0.04), "Timing of largest and second largest: " + str([largest['time'], largest2['time']]), "Timing of largest and second largest rsi: " + str([largest['rsi'], largest2['rsi']]), "Price of largest and 2nd largest: " + str([largest['avgAsk'], largest2['avgAsk']]))))
            file.close()
    # Close after 20 candles
    if len(dataSet) > maximum_candle_difference:
        del (dataSet[0])
    # Delete the orders which has not closed for 6 candles:______________________________
    # TODO: This is the code for closing after 6 candles
    # timeNow = time.time()
    # closeList = []
    # for ID in orderPlaced:
    #     if (float(timeNow) - float(orderPlaced[ID])) >= 5400:
    #         closeList.append(ID)
    # for ID in closeList:
    #     closeOrder(ID)  # Closes that order regardless of what happens
    #     del orderPlaced[ID]
    # ____________________________________________________________________________________
    while True:  # Code to start exact at time 0 minutes, 5 seconds
        if time.gmtime()[5] == 5 and time.gmtime()[4] % 15 == 0:
            break
