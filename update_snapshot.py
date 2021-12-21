import mysql.connector as sql
import pandas as pd
import numpy as np
import configparser
import chess.pgn
import io

def get_game_type(sline, result):

    if sline == '':
        return np.nan


    sline = sline.split(",")

    sline = [float(x) if x != "FILL" else np.nan for x in sline]
    sline = pd.Series(sline).ffill().to_list()


    white_max = 0
    black_max = 0

    white_peek = 0
    black_peek = 0


    prev = None
    last_max = 0
    alternating = 0

    last_white_advantage = 0
    last_black_advantage = 0

    black_advantage_small = False 
    white_advantage_small = False

    black_reached_winning_condition = 0
    white_reached_winning_condition = 0

    black_in_winzone = False
    white_in_winzone = False

    ply = 0

    number_of_big_changes = 0

    for x in sline:
        ply += 1

        if x > 1: 
            white_advantage_small = True
        if x < -1:
            black_advantage_small = True

        if x >= 4.5:
            if not white_in_winzone:
                white_reached_winning_condition += 1
                white_in_winzone = True 
        else:
            white_in_winzone = False 

        if x <= -4.5:
            if not black_in_winzone:
                black_reached_winning_condition += 1
                black_in_winzone = True 
        else:
            black_in_winzone = False

        if prev is not None:
        
            if abs(prev-x) > 3:
                number_of_big_changes += 1

            if x < prev - 1 and prev > 1:
                white_max += 1
                if last_max == -1:
                    alternating += 1

                last_max = 1
            if x > prev + 1 and prev < -1:
                black_max += 1
                if last_max == 1:
                    alternating += 1

                last_max = -1
        prev = x
        if x > white_peek:
            white_peek = x
        if x < black_peek:
            black_peek = x

        if x > 0:
            last_white_advantage = ply 
        else:
            last_black_advantage = ply 

        
        
    if x < 0:
        black_max += 1
    else:
        white_max += 1
    if (white_max == 1 and black_max == 0 and result == "1-0") or (white_max == 0 and black_max == 1 and result == "0-1"):
        return "smooth"

    
    if white_peek <= 1.5 and black_peek >= -1.5:
        return "even"
    if (white_reached_winning_condition > 1 and black_reached_winning_condition >= 1) or (white_reached_winning_condition >= 1 and black_reached_winning_condition > 1):
        return "wild"

   


    #if result == "1-0" and len(sline) - last_black_advantage > 20:
        #return "smooth"

#    if result == "0-1" and len(sline) - last_white_advantage > 20:
        #return "smooth"

    if number_of_big_changes == 1 and alternating == 0 and black_max == 0 and white_max == 0:
        return "one error"

    
    if (white_max == 0 and black_max == 1 and result == "1/2-1/2") or (white_max == 0 and black_max == 1 and result == "1/2-1/2"):
        return "thrown"
    if (white_peek >= 5 and result != "1-0") or (black_peek <= -5 and result != "0-1"):
        return "thrown"

    if np.mean(sline) >= -0.5 and np.mean(sline) <= 0.5 and np.median(sline) >= -0.5 and np.median(sline) <= 0.5:
        return "calm"

    if (not black_advantage_small and result == '1-0') or (not white_advantage_small and result == '0-1'):
        return "smooth"

    if black_max > 3 or white_max > 3:
        return "tough"

    return "unknown"

def avg_cp_loss(sline, min_move, max_move, white):
    # cut list if max_move is set
  

    if sline == '':
        return np.nan


    sline = sline.split(",")
    sline = [float(x) if x != "FILL" else np.nan for x in sline]
    sline = pd.Series(sline).ffill().to_list()


    if max_move is not None:
        sline = sline[:2*max_move]

    if min_move is not None:
        sline = sline[2*min_move:]

    # replace FILL with last value

    if len(sline) <= 2:
        return np.nan

    np_list = np.array(sline)
    shift_list = np_list[1:]

    difflist = np_list[:-1] - shift_list

    if white:
        return int((np.abs(difflist[::2]).mean() * 100))
    
    return int((np.abs(difflist[1::2]).mean() * 100))

def assign_daytime(ts):

    if ts.hour < 6:
        return "night"
    if ts.hour < 12:
        return "morning"
    if ts.hour < 18:
        return "afternoon"
    return "evening"

def handle_specific_snapshots(player):

    config = configparser.ConfigParser()
    config.read("general.conf")
    cc = config["DEFAULT"]

    db_connection = sql.connect(host=cc["HOST"], database=cc["DATABASE"], user=cc["USER"], password=cc["PASSWORD"])  
    db_cursor = db_connection.cursor()  

    db_cursor.execute(f''' 
    select a.*, b.PlayedOn
    from vparsedgames2 as a     
     join rawgames as b   
     on a.gameid = b.gameid     
    where b.active = 1 

    and a.rated=1
    and ( a.black = '{player}' or a.white = '{player}')
    and (a.playtime + 40 * a.increment) >= 480 
    and (a.playtime + 40 * a.increment) < 1499 

    ''')

    #< 479s = Blitz
    #< 1499s = Rapid

    table_rows = db_cursor.fetchall()    
    df = pd.DataFrame(table_rows,columns=db_cursor.column_names)  


    df["PlayedOn"] = pd.to_datetime(df["PlayedOn"])



        #df = df[df["gameid"] == "NYxVOHAl"]

    df["iswhite"] = (df["white"].str.lower() == player)

    df["cp_loss_opening"] = df.apply(lambda x: avg_cp_loss(x["stockfish"],None, 12, x["iswhite"]) if isinstance(x["stockfish"], str) else np.nan,axis=1)
    df["cp_loss_midgame"] = df.apply(lambda x: avg_cp_loss(x["stockfish"], 12,35, x["iswhite"]) if isinstance(x["stockfish"] , str) else np.nan,axis=1)
    df["cp_loss_endgame"] = df.apply(lambda x: avg_cp_loss(x["stockfish"], 35,None, x["iswhite"]) if isinstance(x["stockfish"] , str) else np.nan,axis=1)
    df["cp_loss"] = df.apply(lambda x: avg_cp_loss(x["stockfish"], None, None, x["iswhite"]) if isinstance(x["stockfish"], str)  else np.nan,axis=1)





    df["blackelo_bucket"] = np.round(df["blackelo_pre"] / 100) * 100
    df["whiteelo_bucket"] = np.round(df["whiteelo_pre"] / 100) * 100

    df["opponent_bucket"] = df.apply(lambda x: x["blackelo_bucket"] if x["iswhite"] else x["whiteelo_bucket"],axis=1)

    df["elo"] = df.apply(lambda x: x["whiteelo_pre"] if x["iswhite"] else x["blackelo_pre"],axis=1)


    df["phasis"] = df.moves.apply(lambda x: "opening" if x <=12 else ("endgame" if x >= 30 else "middlegame"))

    df["daytime"] = df.PlayedOn.apply(assign_daytime)
    df["weekday"] = df.PlayedOn.dt.day_name()
    df["Year"] = df.PlayedOn.dt.year
    df["Month"] = df.PlayedOn.dt.month

    df["win"] = df.apply(lambda x: 1 if (x["iswhite"] and x["result"] == "1-0") or (not x["iswhite"] and x["result"] == "0-1") else 0, axis=1)
    df["loss"] = df.apply(lambda x: 1 if (x["iswhite"] and x["result"] == "0-1") or (not x["iswhite"] and x["result"] == "1-0") else 0, axis=1)

    df["draw"] = df.apply(lambda x: 1 if (x["result"] == "1/2-1/2")  else 0, axis=1)

    df["gametype"] = df.apply(lambda x: get_game_type(x["stockfish"], x["result"]), axis=1)

    df["outcome"] = df["endtype"]
    
    df.to_csv(f"snapshot_{player}.csv") 

    db_connection.close()       

config = configparser.ConfigParser()
config.read("general.conf")
cc = config["DEFAULT"]
players = cc["PLAYERS_SF"].split(",")

for p in players:
    print("Handle",p)
    handle_specific_snapshots(p)
