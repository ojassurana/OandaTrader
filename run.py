import os

file = open('pairs.txt', 'r')
for pair in file:
    pair = pair.strip()
    os.environ['pair'] = pair
    command = 'screen -S '+pair+' -dm bash -c "python3 apiMain.py";'
    os.system(command)
    print('Deploying:', pair)
file.close()
