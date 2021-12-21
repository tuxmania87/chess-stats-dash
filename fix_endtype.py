import mysql.connector as mysql
import sys
import configparser
from multiprocessing import Pool
import os
import chess.pgn
import io

class ChessGameParser:

    

    def __init__(self):

        config = configparser.ConfigParser()
        config.read("general.conf")
        self.cc = config["DEFAULT"]

        self.sql_host = self.cc["HOST"]
        self.sql_user = self.cc["USER"]
        self.sql_password = self.cc["PASSWORD"]
        self.sql_database = self.cc["DATABASE"]
        
        self.update_qry = r"""
        UPDATE parsedgames2 
        SET endtype = %s
        where id = %s
        
        
        """

    def get_outcome(self, pgn):
        game = chess.pgn.read_game(io.StringIO(pgn))

        draw = game.headers["Result"] == "1/2-1/2"
    
        if game.headers["Termination"] == "Time forfeit":
            return "TIME_FORFEIT"

        outcome = game.end().board().outcome().termination.name if game.end().board().outcome() is not None else None

        if outcome is not None:
            if outcome == "FIVEFOLD_REPETITION":
                outcome = "THREEFOLD_REPETITION"
            return outcome

    # check for threefold or fivefold

        if game.end().board().is_repetition():
            return "THREEFOLD_REPETITION"

        if game.end().board().is_fifty_moves():
            return "FIFTY_MOVE_RULE"

    

        return "RESIGN" if not draw else "MUTUAL_AGREEMENT"


    def parse_SF_do_update(self, id, pgn):
       

        outcome = self.get_outcome(pgn)

        values = (outcome, id)

        cnx2 = mysql.connect(user=self.sql_user, database=self.sql_database, password=self.sql_password,  host=self.sql_host)
        c2 = cnx2.cursor()
        print(values)
        try:
            c2.execute(self.update_qry, values)
            cnx2.commit()
        except:
            print("failed to update ", values)
            e = sys.exc_info()[0]
            print(e)
        cnx2.close()

    def parse_SF(self):

        players= self.cc["PLAYERS_SF"].split(",")

        joined_string = ','.join([ "'lichess.org "+ x+"'" for x in players])

        # get all unparsed games

        qry = f"""
            SELECT a.pgn, b.id
            from rawgames as a
            join parsedgames2 as b 
               on a.gameid= b.gameid
         where a.active = 1
         and a.source in ({joined_string})
         and (b.playtime + 40 * b.increment) >= 480 
         and (b.playtime + 40 * b.increment) < 1499 
         and b.rated = 1
         and b.endtype = ''
        """

        print(qry)

        cnx = mysql.connect(user=self.sql_user, database=self.sql_database, password=self.sql_password, host=self.sql_host)

        cursor = cnx.cursor()
        print("execute not exists query")
        cursor.execute(qry)

        
        _gamedata = {}
        
        print("put data into memory")
        for game_pgn, parsed_id in cursor:
            _gamedata[parsed_id] = game_pgn

        
        cnx.commit()
        cnx.close()
    

        with Pool(int(self.cc["DOP"])) as p:
            p.starmap(self.parse_SF_do_update, zip(_gamedata.keys(), _gamedata.values()))

        



if __name__=="__main__":

    if os.path.isfile("INPROGRESS_FIX"):
        exit(0)

    open("INPROGRESS_FIX","a").close()

    x = ChessGameParser()
    x.parse_SF()

    os.remove("INPROGRESS_FIX")
