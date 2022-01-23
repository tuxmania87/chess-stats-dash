import requests 
import pickle
from time import sleep
import json
import os.path

def dumpcache(cache):
    textfile = open("crawler.txt", "w")
    for element in cache:
        textfile.write(element + "\n")
    textfile.close()


url = "https://lichess.org/api/games/user/!player!?sort=dateDesc&perftype=rapid,blitz&rated=true&max=100"

global_cache = set()
cache = list()
i = 0

if os.path.isfile("cache.pickle"):
    cache = pickle.load( open("cache.pickle", "rb"))
    global_cache = pickle.load( open("global_cache.pickle","rb"))
    i = int(pickle.load(open("i.pickle","rb")))
else:
    cache.append("tuxmanischerTiger")
    global_cache.add("tuxmanischerTiger")


def get_next_players(playername):

    r = requests.get(url.replace("!player!", playername))

    pgns = r.content.decode("utf-8").split("\n")

    for line in pgns:
        if ("Black " in line or "White " in line) and playername not in line:
            new_name = line[8:-2]

            if new_name not in global_cache:

                cache.append(new_name)
                global_cache.add(new_name)





limit = 10000000

while True:

    get_next_players(cache[i])

    ll = len(cache)

    if ll > limit:
        break

    print(i, ll)

    i += 1

    if i % 2 == 0:
        pickle.dump(cache,open("cache.pickle","wb"))
        pickle.dump(global_cache,open("global_cache.pickle","wb"))
        pickle.dump(i, open("i.pickle","wb"))
        dumpcache(cache)

    sleep(0.2)



dumpcache(cache)






    
    






