import mysql.connector as mysql
import stockfish
import sys
import configparser
from multiprocessing import Pool

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
        SET stockfish = %s
        where id = %s
        
        
        """



    def parse_SF_do_update(self, id, pgn):
        stocklist = []


        stocklist = stockfish.get_stockfish_list(pgn)
        values = (",".join(stocklist), id)
        
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
         and b.stockfish = ''
         and b.playtime >= 600 and b.playtime <=900
         and b.rated = 1
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
    

        with Pool(8) as p:
            p.starmap(self.parse_SF_do_update, zip(_gamedata.keys(), _gamedata.values()))

        



if __name__=="__main__":
    x = ChessGameParser()
    x.parse_SF()