import requests 
import pickle
from time import sleep
import json
import os.path

def dumpcache(cache):
    textfile = open("fide_profiles.txt", "w")
    for element in cache:
        textfile.write(json.dumps(element) + "\n")
    textfile.close()


def handle_profile(jj):
    if "fideRating" in jj["profile"]:

        # we have a candidate

        # check rd from blitz and rapid smaller than 100
        # and 50 games played 

        if jj["perfs"]["rapid"]["rd"] < 100 and jj["perfs"]["rapid"]["games"] >= 100:
            if jj["perfs"]["blitz"]["rd"] < 100 and jj["perfs"]["blitz"]["games"] >= 100:

                print(".",end="",flush=True)

                profile = {}
                profile["name"] = line
                profile["rapid"] = jj["perfs"]["rapid"]["rating"]
                profile["blitz"] = jj["perfs"]["blitz"]["rating"]
                try:
                    profile["classical"] = jj["perfs"]["classical"]["rating"]
                except:
                    pass
                profile["fide"] = jj["profile"]["fideRating"]

                fide_list.add(line)
                fide_profiles.append(profile)

url = "https://lichess.org/api/user/!player!"

done_list = set()
fide_list = set()
fide_profiles = list()


if os.path.isfile("done_list.pickle"):
    done_list = pickle.load( open("done_list.pickle", "rb"))
    fide_list = pickle.load( open("fide_list.pickle","rb"))
    fide_profiles = pickle.load( open("fide_profiles.pickle","rb"))



# read from crawler

f = open("crawler.txt","r")
crawler_candidates = [x.strip() for x in f.readlines()]
f.close()

i = 0

for line in crawler_candidates:

    if line in done_list:
        continue

    done_list.add(line)

    # check if name has fide profile

    r = requests.get(url.replace("!player!",line))

    
    try:
        jj = json.loads(r.content.decode("utf-8"))
        handle_profile(jj)
    except:
        pass


    if i % 10 == 0:
        pickle.dump(done_list,open("done_list.pickle","wb"))
        pickle.dump(fide_list,open("fide_list.pickle","wb"))
        pickle.dump(fide_profiles, open("fide_profiles.pickle","wb"))
        dumpcache(fide_profiles)

    sleep(0.2)



dumpcache(fide_profiles)






    
    






