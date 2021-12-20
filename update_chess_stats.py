import mysql.connector as mysql
import chess.pgn
import requests
import io
import datetime
import json
import chess.svg
import pandas as pd
import stockfish
import sys
import time
import configparser

class ChessGameParser:

    def __init__(self):

        config = configparser.ConfigParser()
        config.read("general.conf")
        self.cc = config["DEFAULT"]


        self.sql_host = self.cc["HOST"]
        self.sql_user = self.cc["USER"]
        self.sql_password = self.cc["PASSWORD"]
        self.sql_database = self.cc["DATABASE"]
        self.file_names = [ "/home/robert/lichess_tuxmania_2021-05-21.pgn", "/home/robert/lichess_tuxmanischerTiger_2021-05-21.pgn","/home/robert/lichess_Papa-Ticulat_2021-05-21.pgn"]
        self.file_names_alias = [ "tuxmania","tuxmanischerTiger","Papa-Ticulat"]

        self.all_game_ids = self.get_game_id_list()

        self.openings = pd.concat(
            [pd.read_csv("a.tsv", sep="\t"), pd.read_csv("b.tsv", sep="\t"), pd.read_csv("c.tsv", sep="\t"),
             pd.read_csv("d.tsv", sep="\t"), pd.read_csv("e.tsv", sep="\t")])

    def store_game_in_db(self,game_id, game_pgn, source, played_date):

        if game_id in self.all_game_ids:
            return

        cnx = mysql.connect(user=self.sql_user, database=self.sql_database, password=self.sql_password)

        cursor = cnx.cursor()

        qry = "INSERT INTO rawgames (id, gameid, pgn, source, PlayedOn) SELECT NULL, %s, %s, %s, %s "
        
        try:
            data = (game_id, game_pgn, source, played_date)

            cursor.execute(qry, data)
            cnx.commit()
        except:
            pass
        cnx.close()



    def get_game_id_list(self):
        game_list = []

        cnx = mysql.connect(user=self.sql_user, database=self.sql_database, password=self.sql_password)

        cursor = cnx.cursor()

        qry = "SELECT gameid FROM rawgames"
        cursor.execute(qry)

        for game_id in cursor:
            game_list.append(game_id[0])

        cnx.commit()
        cnx.close()

        return game_list

    def insert_lichess_games(self,pgn_array,source):
        for game in pgn_array:
            g = chess.pgn.read_game(io.StringIO(game))
            
            if "UTCDate" not in g.headers:
                print(game)
                continue

            game_id = g.headers["Site"].replace("https://lichess.org/", "")
            played_on = (g.headers["UTCDate"]+" "+g.headers["UTCTime"]).replace(".","-")

            self.store_game_in_db(game_id, game, source, played_on)

    def insert_new_lichess_games(self, player_name):


        # check high water mark for player
        _sourcename = "lichess.org "+player_name
        qry = "SELECT MAX(PlayedOn) as maxdate from rawgames where source = '"+_sourcename+"'"
        

        cnx = mysql.connect(user=self.sql_user, database=self.sql_database, password=self.sql_password)

        cursor = cnx.cursor()
        cursor.execute(qry)

        maxdate_parsed = None

        for maxdate in cursor:
            maxdate_parsed = maxdate

        if maxdate_parsed[0] is None:
            maxdate_unix = 0
        else:
            maxdate_unix = int(maxdate_parsed[0].timestamp() * 1000)

        print(player_name, maxdate_unix)

        r = requests.get(f"https://lichess.org/api/games/user/{player_name}?perfType=blitz,rapid,classical&since={maxdate_unix}")
        all_games = r.content.decode("utf-8").strip().split("\n\n\n")
        self.insert_lichess_games(all_games, f"lichess.org {player_name}")


    def insert_old_tuxmania_games(self):
        i = 0
        for ff in self.file_names:
            with open(ff, "r") as f:
                 all_games = f.read().strip().split("\n\n\n")
            self.insert_lichess_games(all_games, f"lichess.org "+self.file_names_alias[i])
            i += 1


    def insert_new_chesscom_games(self):
        # iterate from 2020 beginning until current month
        years = range(2020, int(datetime.datetime.now().strftime("%Y"))+ 1)
        months = range(1,13)

        for y in years:
            for m in months:

                r = requests.get("https://api.chess.com/pub/player/tuxmania2/games/{}/{}".format(y, str(m).zfill(2)))
                jj = json.loads(r.content.decode("utf-8"))

                if "games" in jj:

                    for game in jj["games"]:

                        g = chess.pgn.read_game(io.StringIO(game["pgn"]))

                        if "UTCDate" not in g.headers:
                            print(game["pgn"])
                            continue
                        game_id = game["url"].replace("https://www.chess.com/live/game/","")
                        played_on = (g.headers["UTCDate"] + " " + g.headers["UTCTime"]).replace(".", "-")
                        source = "chess.com tuxmania2"

                        self.store_game_in_db(game_id, game["pgn"], source, played_on)



    def parse_new_games(self):

        # get all unparsed games

        qry = r"""
            SELECT a.pgn, a.gameid, a.source
            from rawgames as a
            where not exists (
                select 1
                from parsedgames2 as b
                where a.gameid = b.gameid
            )
         and a.active = 1
        """

        cnx = mysql.connect(user=self.sql_user, database=self.sql_database, password=self.sql_password)

        cursor = cnx.cursor()
        print("execute not exists query")
        cursor.execute(qry)

        insert_qry = r"""
        INSERT INTO parsedgames2 (id, gameid, rated, result, opening, moves, black,
            white, blackelo_pre, whiteelo_pre, endtype, endimage, playtime, increment, stockfish, thrown_white, thrown_black)
            
        VALUES (NULL, %s, %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        
        """
        _gamedata = {}
        
        print("put data into memory")
        for game_pgn, game_id,game_source in cursor:
            _gamedata[game_id] = game_pgn

        
        cnx.commit()
        cnx.close()
        
        iterator = 0

        for game_id, game_pgn in _gamedata.items():

            print(f"{iterator}/{len(_gamedata)}")
            iterator += 1
            g = chess.pgn.read_game(io.StringIO(game_pgn))
            
            rated = False
            if g.headers["Site"] == "Chess.com" or "rated" in g.headers["Event"].lower():
                rated = True

                

            color = None

            result = g.headers["Result"]
            opening = "???"

            it = g
            last_opening = None

            while it is not None:

                move_list = " ".join([x.uci() for x in it.board().move_stack])

                candidate_openings = self.openings[self.openings["moves"] == move_list]
                if len(candidate_openings.index) > 0:
                    last_opening = candidate_openings["name"]

                it = it.next()
                if last_opening is not None:
                    opening = last_opening.tolist()[0]

            moves = g.end().board().fullmove_number

            blackelo_pre = g.headers["BlackElo"]
            whiteelo_pre = g.headers["WhiteElo"] 
            if "chess.com" in game_source:
                try:
                    whiteelo_pre = str(int(whiteelo_pre)+300)
                except:
                    whiteelo_pre = "0"
                try:
                    blackelo_pre = str(int(blackelo_pre)+300)
                except:
                    blackelo_pre = "0"

            endtype = None
            if "mate" in g.headers["Termination"]:
                endtype = "checkmate"
            elif "resign" in g.headers["Termination"]:
                endtype = "resignation"
            elif "canc" in g.headers["Termination"]:
                endtype = "cancelled"
            elif "stale" in g.headers["Termination"]:
                endtype = "stalemate"
            elif "draw" in g.headers["Termination"]:
                endtype = "draw"
            else:
                endtype = g.headers["Termination"]

            #end_image = chess.svg.board(g.end().board(), size=350)
            #end_image = bytes(renderPM.drawToString(chess.svg.board(g.end().board(), size=350), fmt="PNG"), "utf-8")

            end_image = 0x0

            playtime_raw = g.headers["TimeControl"].split("+")

            increment = 0
            playtime = playtime_raw[0]
            if len(playtime_raw) > 1:
                increment = playtime_raw[1]



            stocklist = []
            thrown_white = 0
            thrown_black = 0
#            if rated and playtime.isdigit() and int(playtime) >= 300:
#                stocklist = stockfish.get_stockfish_list(game_pgn)
#                for cp in stocklist:
#                    if cp != "FILL" and float(cp) >= 3 and result == "0-1":
#                        thrown_white = 1
#                        break
                    
#                    if cp != "FILL" and float(cp) <= -3 and result == "1-0":
#                        thrown_black = 1
#                        break

            # hard filter
            '''if "lichess.org" in website:
                df__ = df__[(
                        ((df__["myelo_pre"] < 1530) & (df__["playedOn"] < '2020-12-04')) | (
                        df__["playedOn"] >= '2020-12-05'))]'''


            values = (game_id, 1 if rated else 0, g.headers["Result"], opening, moves, g.headers["Black"], g.headers["White"], blackelo_pre, whiteelo_pre, endtype, end_image, playtime, increment, ",".join(stocklist), thrown_white, thrown_black)

            if playtime == '-':
                continue

            cnx2 = mysql.connect(user=self.sql_user, database=self.sql_database, password=self.sql_password)

            c2 = cnx2.cursor()
            print(values)
            try:
                c2.execute(insert_qry, values)
                cnx2.commit()
            except:
                print("failed to insert ", values)
                e = sys.exc_info()[0]
                print(e)
            cnx2.close()


x = ChessGameParser()

players = x.cc["PLAYERS_PARSE"].split(",")

for p in players:
    print(f"Handle {p}")
    x.insert_new_lichess_games(p)
#x.insert_old_tuxmania_games()
#print("handle new chess com games")
#x.insert_new_chesscom_games()

x.parse_new_games()
