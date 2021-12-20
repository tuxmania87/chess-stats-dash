import chess
import chess.pgn
import chess.engine
import sys
import io
import configparser



def get_stockfish_list(pgn):

    config = configparser.ConfigParser()
    config.read("general.conf")
    cc = config["DEFAULT"]

    engine = chess.engine.SimpleEngine.popen_uci(cc["SF_LOCATION"])
    game = chess.pgn.read_game(io.StringIO(pgn))

    l = []
    print(game.headers["Site"])
    i = 0
    while game is not None:
        board = game.board()

        info = engine.analyse(board, chess.engine.Limit(time=.5))
        if "engine.Cp" in str(type(info["score"].relative)):
            intval = int(info["score"].relative.cp) / 100
            if i % 2 == 1:
               intval *= -1
            l.append(str(intval))
        else:
            l.append("FILL")
        # Score: PovScore(Mate(+1), WHITE)
        game = game.next()
        i += 1

    engine.quit()

    return l
