#!/usr/bin/python3

import numpy as np


def rsi(prices, period=10):
    num_prices = len(prices)
    if num_prices < period:
        # show error message
        raise SystemExit('Error: num_prices < period')

    # this could be named gains/losses to save time/memory in the future
    changes = prices[1:] - prices[:-1]
    #num_changes = len(changes)

    rsi_range = num_prices - period

    rsis = np.zeros(rsi_range)

    gains = np.array(changes)
    # assign 0 to all negative values
    masked_gains = gains < 0
    gains[masked_gains] = 0

    losses = np.array(changes)
    # assign 0 to all positive values
    masked_losses = losses > 0
    losses[masked_losses] = 0
    # convert all negatives into positives
    losses *= -1

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        rsis[0] = 100
    else:
        rs = avg_gain / avg_loss
        rsis[0] = 100 - (100 / (1 + rs))

    for idx in range(1, rsi_range):
        avg_gain = ((avg_gain * (period - 1) + gains[idx + (period - 1)]) /
                    period)
        avg_loss = ((avg_loss * (period - 1) + losses[idx + (period - 1)]) /
                    period)

        if avg_loss == 0:
            rsis[idx] = 100
        else:
            rs = avg_gain / avg_loss
            rsis[idx] = 100 - (100 / (1 + rs))

    return rsis

prices = np.array([44.55, 44.3, 44.36, 43.82, 44.46, 44.96, 45.23,45.56, 45.98, 46.22, 46.03, 46.17, 45.75, 46.42, 46.42, 46.14, 46.17,46.55, 46.36, 45.78, 46.35, 46.39, 45.85, 46.59, 45.92, 45.49, 44.16,44.31, 44.35, 44.7, 43.55, 42.79, 43.26])
