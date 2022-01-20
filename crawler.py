import requests 
import pickle
from time import sleep
import json

url = "https://lichess.org/api/games/user/!player!?sort=dateDesc&perftype=rapid,blitz&rated=true&max=100"

global_cache = set()
cache = list()



def get_next_players(playername):

    r = requests.get(url.replace("!player!", playername))

    pgns = r.content.decode("utf-8").split("\n")

    for line in pgns:
        if ("Black " in line or "White " in line) and playername not in line:
            new_name = line[8:-2]

            if new_name not in global_cache:

                cache.append(new_name)
                global_cache.add(new_name)



cache.append("tuxmanischerTiger")
global_cache.add("tuxmanischerTiger")

i = 0

limit = 3000

while True:

    get_next_players(cache[i])

    ll = len(cache)

    if ll > limit:
        break

    print(i, ll)

    i += 1
    sleep(0.5)




textfile = open("crawler.txt", "w")
for element in cache:
    textfile.write(element + "\n")
textfile.close()







    
    






