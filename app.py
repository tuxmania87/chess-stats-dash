import dash
import platform
from dash.dependencies import Input, Output

from dash import dcc
from dash import html

from dateutil.relativedelta import relativedelta

import flask
from numpy.core.numeric import roll
import pandas as pd
import time

import configparser


import os
import plotly.express as px
import mysql.connector as mysql
from dash import dash_table
import numpy as np

import datetime
from datetime import date

import dash_bootstrap_components as dbc

import plotly.graph_objs as go

server = flask.Flask('app')
server.secret_key = os.environ.get('secret_key', 'secret')



def avg_cp_loss(sline, max_move, white):
    # cut list if max_move is set

    sline = sline.split(",")

    if max_move is not None:
        sline = sline[:2*max_move]

    # replace FILL with last value

    sline = [float(x) if x != "FILL" else np.nan for x in sline]

    sline = pd.Series(sline).ffill().to_list()

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


home_dir = "" if platform.system() == "windows" else "/home/robert/chess-stats-dash"



frame_dict = {}

config = configparser.ConfigParser()
config.read(f"{home_dir}general.conf")
cc = config["DEFAULT"]

for p in cc["PLAYERS_SF"].split(","):
    frame_dict[p] = pd.read_csv(f"{home_dir}snapshot_{p}.csv")

frame_dict["fettarmqp"] = pd.read_csv("snapshot_fettarmqp.csv")
frame_dict["ultimaratio4"] = pd.read_csv("snapshot_ultimaratio4.csv")
frame_dict["paff-morris"] = pd.read_csv("snapshot_paff-morris.csv")
frame_dict["tuxmania"] = pd.read_csv("snapshot_tuxmania.csv")
frame_dict["therealknox"] = pd.read_csv("snapshot_therealknox.csv")

for k in frame_dict.keys():
    _df = frame_dict[k]
    _df["PlayedOn"] = pd.to_datetime(_df["PlayedOn"])

    frame_dict[k] = _df





# DEBUG

#df = df[df[""]]



'''
Lichess time controls are based on estimated game duration = (clock initial time) + 40  (clock increment)
For instance, the estimated duration of a 5+3 game is 5  60 + 40  3 = 420 seconds.

< 29s = UltraBullet
< 179s = Bullet
< 479s = Blitz
< 1499s = Rapid
 1500s = Classical
'''

def unix_time_millis(datetimevalue):
    return datetimevalue.timestamp()

def get_marks_from_start_end(start, end):
    ''' Returns dict with one item per month
    {1440080188.1900003: '2015-08',
    '''

    rd = relativedelta(months=1)
    td_seconds = (end-start).total_seconds()

    # smaller than 15 months
    if td_seconds / 60 / 60 / 24 / 30 <= 15:
        rd = relativedelta(months=1)
    elif td_seconds / 60 / 60 / 24 / 30 <= 36:
        rd = relativedelta(months=2)
    else: 
        rd = relativedelta(months=6)


    result = []
    current = start
    while current <= end:
        result.append(current)
        current += rd
    #print({unix_time_millis(m):(str(m.strftime('%Y-%m'))) for m in result})
    return {int(unix_time_millis(m)):(str(m.strftime('%Y-%m-%d'))) for m in result}

    #0: {'label': '0°C', 'style': {'color': '#77b0b1'}},
    #return {int(unix_time_millis(m)):{'label':(str(m.strftime('%Y-%m-%d'))), 'style': {'color':'black'}} for m in result}


# playtime increment
def timecontrol_classifier(playtime, increment):


    estimated_game_duration = playtime + 40 * increment

    if estimated_game_duration < 29:
        return "UltraBullet"
    if estimated_game_duration < 179:
        return "Bullet"
    if estimated_game_duration < 479:
        return "Blitz"
    if estimated_game_duration < 1499:
        return "Rapid"
    return "Classical"





app = dash.Dash('app', server=server)

app.scripts.config.serve_locally = False
#dcc._js_dist[0]['external_url'] = 'https://cdn.plot.ly/plotly-basic-latest.min.js'


external_stylesheets = [dbc.themes.BOOTSTRAP]


tabs_styles = {
    'height': '44px'
}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '6px',
    'fontWeight': 'bold'
}

tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': '#119DFF',
    'color': 'white',
    'padding': '6px'
}

# default player
selected_player = frame_dict["fettarmqp"]

app.layout = html.Div([
    html.H1('Chess Stats'),

    html.Div([
        html.Span('Choose name', style={'font-weight': 'bold'}),
        dcc.Dropdown(
        id='input-player',
        options=[
            {'label': 'FettarmQP', 'value': 'fettarmqp'},
            {'label': 'UltimaRatio4', 'value': 'ultimaratio4'},
            {'label': 'Paff-Morris', 'value': 'paff-morris'},
            {'label': 'TheRealKnox', 'value': 'therealknox'},
            {'label': 'Tuxmania', 'value': 'tuxmania'},
        ],
        value='fettarmqp',
        className="dash-bootstrap"
    ),
    ], style={'width': '20%', 'margin': 'auto', 'margin-bottom': '20px'}),

    
     html.Div([
        html.Span('Choose time control', style={'font-weight': 'bold'}),
        dcc.Dropdown(
        id='dropdown-timecontrol',
        options=[
            {'label': 'Rapid', 'value': 'Rapid'},
        ],
        value='Rapid',
        className="dash-bootstrap"
    ),
    ], style={'width': '20%', 'margin': 'auto', 'margin-bottom': '20px'}),

    
    #html.Div([     
    #    dcc.RangeSlider(   
    #    id='time-slider', 
    #    #min=unix_time_millis(selected_player["PlayedOn"].min()),
    #    #max=unix_time_millis(selected_player["PlayedOn"].max()), 
    #    #value=[unix_time_millis(selected_player["PlayedOn"].min()), unix_time_millis(selected_player["PlayedOn"].max())],         
    #    #marks=get_marks_from_start_end(selected_player["PlayedOn"].min(), selected_player["PlayedOn"].max()),    
    #    #tooltip={"placement": "bottom", "always_visible": True}  
    #    className="dash-bootstrap"
    #    ), 
    #    html.Div(id='output-container-range-slider')    
    #]), 
    

    html.Div([     
        dcc.DatePickerRange(
        id='date-picker',
        #min_date_allowed=date(2021, 1, 1),
        #max_date_allowed=date(2021, 6, 1),
        #initial_visible_month=date(2021, 8, 5),
        #start_date=date(2020, 8, 25),
        #end_date=date(2021,1,1),
        display_format='YYYY-MM-DD',
        className="dash-bootstrap"
        ),
    ], style={'width': '30%', 'margin': 'auto', 'margin-bottom': '20px'}),
    
  

    dcc.Graph(id='graph-elo', className='container'),
    dcc.Graph(id='graph-overallelo', className='container'),
    dcc.Graph(id='graph-overallcpl', className='container'),
    #dcc.Graph(id='graph-op-rating', className='container'),
    dcc.Graph(id='graph-op-rating2', className='container'),


    dcc.Graph(id='graph-phasis', className='container'),
    dcc.Graph(id='graph-phasis-cploss', className='container'),
    dcc.Graph(id='graph-phasis-result', className='container'),

    dcc.Graph(id='graph-gtype', className='container'),
    dcc.Graph(id='graph-gtype-cploss', className='container'),
    dcc.Graph(id='graph-gtype-result', className='container'),

    dcc.Graph(id='graph-daytime', className='container'),
    dcc.Graph(id='graph-daytime-cploss', className='container'),
    dcc.Graph(id='graph-daytime-result', className='container'),

    dcc.Graph(id='graph-weekday', className='container'),
    dcc.Graph(id='graph-weekday-cploss', className='container'),
    dcc.Graph(id='graph-weekday-result', className='container'),


    html.Div([
        html.Span('Rating Milestones', style={'font-weight': 'bold'}),
        dash_table.DataTable(
            id='table-elocross',
            columns = [
                {"name":"Rating","id":"elo"},
                {"name":"Rating reached","id":"milestone_reached"},
                {"name":"Rating passed","id":"milestone_crossed"},
                {"name":"Success","id":"success_rate"},
                ],

            style_header={
                'backgroundColor': 'rgb(30, 30, 30)',
                'color': 'white'
            },
            style_data={
                'backgroundColor': 'rgb(50, 50, 50)',
                'color': 'white'
            },

        )
    ], style={'width': '40%', 'margin': 'auto', 'margin-bottom': '20px'}),


#], )
],className="container", style={'margin': 'auto', 'text-align': 'center', 'width':'60%'})

'''
        min_date_allowed=date(2021, 1, 1),
        max_date_allowed=date(2021, 6, 1),
        initial_visible_month=date(2021, 8, 5),
        start_date=date(2020, 8, 25),
        end_date=date(2021,1,1),
        # '''

@app.callback(Output('date-picker', 'max_date_allowed'),
              [Input('input-player', 'value')])
def update_date_picker_max(input):   
    
    df = frame_dict[input.lower()]
    return df.PlayedOn.max().date()

@app.callback(Output('date-picker', 'min_date_allowed'),
              [Input('input-player', 'value')])
def update_date_picker_min(input):   
    
    df = frame_dict[input.lower()]
    return df.PlayedOn.min().date()


@app.callback(Output('date-picker', 'start_date'),
              [Input('input-player', 'value')])
def update_date_picker_start(input):   
    
    df = frame_dict[input.lower()]
    return df.PlayedOn.min().date()

@app.callback(Output('date-picker', 'end_date'),
              [Input('input-player', 'value')])
def update_date_picker_end(input):   
    
    df = frame_dict[input.lower()]
    return df.PlayedOn.max().date()

@app.callback(Output('date-picker', 'initial_visible_month'),
              [Input('input-player', 'value')])
def update_date_picker_initial(input):   
    
    df = frame_dict[input.lower()]
    return df.PlayedOn.max().date()




@app.callback(Output('time-slider', 'min'),
              [Input('input-player', 'value')])
def update_slider_example_min(input):   
    df = frame_dict[input.lower()]
    min_value = unix_time_millis(df["PlayedOn"].min())
    return min_value

@app.callback(Output('time-slider', 'max'),
              [Input('input-player', 'value')])
def update_slider_example_max(input):
    df = frame_dict[input.lower()]
    max_value = unix_time_millis(df["PlayedOn"].max())
    return max_value

@app.callback(Output('time-slider', 'value'), [Input('time-slider', 'min'),Input('time-slider', 'max')])
def update_slider_example_value(min_value, max_value): 
        return [min_value, max_value]

@app.callback(Output('time-slider', 'marks'), [Input('input-player', 'value')])
def update_slider_example_marks(input): 
        df = frame_dict[input.lower()]
        marks = get_marks_from_start_end(df["PlayedOn"].min(), df["PlayedOn"].max()),
        return marks[0]


@app.callback(Output('graph-elo', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_elo(player_name, time_control, min_date, max_date):

    #min_date = datetime.datetime.strptime(min_date, "%Y-%m-%d")
    #max_date = datetime.datetime.strptime(max_date, "%Y-%m-%d")

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    df = df.set_index("PlayedOn")

    df = df.resample("1D").mean().ffill().rolling(3).mean().dropna().reset_index()

    fig = px.line(
        df.iloc[15:], x="PlayedOn",y="elo"
    )


    fig.update_layout(
        yaxis=dict(
        title_text="rating progress",
        titlefont=dict(size=15),
    ), xaxis=dict(
        title_text="Time"
    ),
    title={
        'text': "Rating gained over time",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
        template='plotly_dark'
    )
    
    return fig 

@app.callback(Output('graph-overallelo', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph(player_name, time_control, min_date, max_date):

    #min_date = datetime.datetime.strptime(min_date, "%Y-%m-%d")
    #max_date = datetime.datetime.strptime(max_date, "%Y-%m-%d")

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    y = df[["Year","Month","id"]].groupby(["Year","Month"]).count().reset_index()
    y["time"] = y.apply(lambda x: x["Year"].astype(str) + "-M" + ("0" if x["Month"] < 10 else "") +   x["Month"].astype(str),axis=1)

    
    
    #fig = px.bar(
    #        y, x="time",y="id", template="plotly_dark",
    #)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = y.id,
        x = y.time,
        #hovertemplate = '<b>Opening</b>' +
        #                '<br>Games played: %{text}' + 
        #                '<br>Percentage %{x:.2f} %<extra></extra>',
        #text = xx.opening.to_list(),
        name = "Opening %",
        marker = dict(
            color = 'rgba(51,172,210,0.6)',
            line=dict(color='rgba(51,172,210,0.6)', width=0.05)
        ),
        #orientation='h',
    ))


    fig.update_layout(
        yaxis=dict(
        title_text="games played",
        titlefont=dict(size=15),
    ), xaxis=dict(
        title_text="Time"
    ),
    title={
        'text': "Games played over time",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
        template='plotly_dark'
    )
    
    return fig 

@app.callback(Output('graph-overallcpl', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_overallcpl(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    y = df[["Year","Month","cp_loss"]].groupby(["Year","Month"]).mean().reset_index()
    y["time"] = y.apply(lambda x: x["Year"].astype(int).astype(str) + "-M" + ("0" if x["Month"] < 10 else "") +   x["Month"].astype(int).astype(str),axis=1)

    y["cp_loss"] = y["cp_loss"].fillna(0)


     
    #fig = px.bar(
    #        y, x="time",y="cp_loss", template="plotly_dark"
    #)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = y.cp_loss,
        x = y.time,
        #hovertemplate = '<b>Opening</b>' +
        #                '<br>Games played: %{text}' + 
        #                '<br>Percentage %{x:.2f} %<extra></extra>',
        #text = xx.opening.to_list(),
        name = "Opening %",
        marker = dict(
            color = 'rgba(51,172,210,0.6)',
            line=dict(color='rgba(51,172,210,0.6)', width=0.05)
        ),
        #orientation='h',
    ))


    fig.update_layout(
        yaxis=dict(
        title_text="centipawn loss",
        titlefont=dict(size=15),
    ),
    title={
            'text': "Centipawn loss over time",
            #'y':0.96,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        template="plotly_dark"
    )
    
    return fig 


@app.callback(Output('graph-op-rating2', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_oprating2(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["id","win","opponent_bucket"]].groupby(["win","opponent_bucket"]).count().reset_index()

    xx = xx[xx["win"] == 1]
    xx = xx[["opponent_bucket","id"]]
    xx.columns = ["Rating","wins"]

    df_wins_rating = xx.set_index("Rating")

    xx = df[["id","draw","opponent_bucket"]].groupby(["draw","opponent_bucket"]).count().reset_index()

    xx = xx[xx["draw"] == 1]
    xx = xx[["opponent_bucket","id"]]
    xx.columns = ["Rating","draws"]

    df_draws_rating = xx.set_index("Rating")

    xx = df[["id","loss","opponent_bucket"]].groupby(["loss","opponent_bucket"]).count().reset_index()

    xx = xx[xx["loss"] == 1]
    xx = xx[["opponent_bucket","id"]]
    xx.columns = ["Rating","loss"]

    df_loss_rating = xx.set_index("Rating")


    df_total_ratings = df_wins_rating.join(df_loss_rating, how="outer").reset_index().set_index("Rating").join(df_draws_rating, how="outer").fillna(0)

    df_total_ratings["sum"] = df_total_ratings.wins + df_total_ratings.loss + df_total_ratings.draws

    df_total_ratings["Wins %"] = df_total_ratings.wins / df_total_ratings["sum"] * 100
    df_total_ratings["Draws %"] = df_total_ratings.draws / df_total_ratings["sum"] * 100
    df_total_ratings["Losses %"] = df_total_ratings.loss / df_total_ratings["sum"] * 100

     

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = df_total_ratings["Wins %"],
        x = df_total_ratings.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Wins: %{text}' + 
                        '<br>Win percentage %{y:.2f} %<extra></extra>',
        text = df_total_ratings.wins.to_list(),
        name = "Win %",
        marker = dict(
            color = 'rgba(0,128,0,0.6)',
            line=dict(color='rgba(0,128,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
        
    ))

    fig.add_trace(go.Bar(
        y = df_total_ratings["Draws %"],
        x = df_total_ratings.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Draws: %{text}' + 
                        '<br>Draw percentage %{y:.2f} %<extra></extra>',
        text = df_total_ratings.draws.to_list(),
        name = "Draw %",
        marker = dict(
            color = 'rgba(211,211,211,0.6)',
            line=dict(color='rgba(211,211,211,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(0, 0, 0)'
        )
    ))

    fig.add_trace(go.Bar(
        y = df_total_ratings["Losses %"],
        x = df_total_ratings.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Losses: %{text}' + 
                        '<br>Loss percentage %{y:.2f} %<extra></extra>',
        text = df_total_ratings.loss.to_list(),
        name = "Loss %",
        marker = dict(
            color = 'rgba(255,0,0,0.6)',
            line=dict(color='rgba(255,0,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
    ))

    fig.update_layout(
        yaxis=dict(
        title_text="%",
        ticktext=["0%", "20%", "40%", "60%","80%","100%"],
        tickvals=[0, 20, 40, 60, 80, 100],
        tickmode="array",
        titlefont=dict(size=15),
        
    ),
    autosize=False,
    #width=1000,
    #height=400,
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    title={
        'text': "Game results per opponent strength",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    barmode='stack',
    template="plotly_dark"
    
    
    
    
    )

   
    return fig 


@app.callback(Output('graph-phasis', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_phasis(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["id","phasis","iswhite"]].groupby(["phasis"]).count().reset_index()


    xx = xx.drop(["iswhite"],axis=1)
    xx.columns = ["Phasis", "#Games"]

    xx = xx.T
    xx.columns = ["endgame", "middlegame", "opening"]
    xx = xx.drop(["Phasis"])
    xx = xx.reset_index()



    xx["opening%"] = (xx["opening"] / (xx.opening + xx.middlegame + xx.endgame)) * 100
    xx["middlegame%"] = (xx["middlegame"] / (xx.opening + xx.middlegame + xx.endgame)) * 100
    xx["endgame%"] = (xx["endgame"] / (xx.opening + xx.middlegame + xx.endgame)) * 100

    

    

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x = xx["opening%"],
        y = xx.index,
        hovertemplate = '<b>Opening</b>' +
                        '<br>Games played: %{text}' + 
                        '<br>Percentage %{x:.2f} %<extra></extra>',
        text = xx.opening.to_list(),
        name = "Opening %",
        marker = dict(
            color = 'rgba(255,0,0,0.6)',
            line=dict(color='rgba(255,0,0,0.6)', width=0.05)
        ),
        orientation='h',
    ))

    fig.add_trace(go.Bar(
        x = xx["middlegame%"],
        y = xx.index,
        hovertemplate = '<b>Middlegame</b>' +
                        '<br>Games played: %{text}' + 
                        '<br>Percentage %{x:.2f} %<extra></extra>',
        text = xx.middlegame.to_list(),
        name = "Middlegame %",
        marker = dict(
            color = 'rgba(211,211,211,0.6)',
            line=dict(color='rgba(211,211,211,0.6)', width=0.05)
        ),
        orientation='h',
    ))

    
    fig.add_trace(go.Bar(
        x = xx["endgame%"],
        y = xx.index,
        hovertemplate = '<b>Endgame</b>' +
                        '<br>Games played: %{text}' + 
                        '<br>Percentage %{x:.2f} %<extra></extra>',
        text = xx.opening.to_list(),
        name = "Endgame %",
        marker = dict(
            color = 'rgba(0,128,0,0.6)',
            line=dict(color='rgba(0,128,0,0.6)', width=0.05)
        ),
        orientation='h',
    ))

    fig.update_layout(
        
    title={
        'text': "Games ended in Phasis...",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    barmode='stack',
    height=300,
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    autosize=False,
    template="plotly_dark",
    )

    fig.update_yaxes(visible=False, showticklabels=False)
   
    return fig 
        
@app.callback(Output('graph-phasis-cploss', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_phasis_cploss(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["cp_loss","phasis"]].groupby(["phasis"]).mean()

    xx = xx.reset_index()    
    xx = xx.sort_values(["phasis"], ascending=False)

    xx["cp_loss"] = xx["cp_loss"].astype(int)

    #fig = px.bar(xx, x="phasis", y="cp_loss")


    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = xx.cp_loss,
        x = xx.phasis,
        #hovertemplate = '<b>Opening</b>' +
        #                '<br>Games played: %{text}' + 
        #                '<br>Percentage %{x:.2f} %<extra></extra>',
        #text = xx.opening.to_list(),
        name = "Opening %",
        marker = dict(
            color = 'rgba(51,172,210,0.6)',
            line=dict(color='rgba(51,172,210,0.6)', width=0.05)
        ),
        #orientation='h',
    ))


    fig.update_layout(
        yaxis=dict(
        title_text="centipawn loss",
        titlefont=dict(size=15),
    ),
    
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    autosize=False,
    title={
        'text': "Centipawn loss for game phasis",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    template="plotly_dark",
    )
   
    return fig 

@app.callback(Output('graph-phasis-result', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_phasis_result(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["cp_loss","phasis","win"]].groupby(["phasis","win"]).count().reset_index()

    xxw = xx[xx["win"] == 1]
    xxw = xxw.drop(["win"], axis=1)
    xxw = xxw.set_index("phasis")
    xxw.columns = ["wins"]


    xx = df[["cp_loss","phasis","draw"]].groupby(["phasis","draw"]).count().reset_index()

    xxd = xx[xx["draw"] == 1]
    xxd = xxd.drop(["draw"], axis=1)
    xxd = xxd.set_index("phasis")
    xxd.columns = ["draws"]

    xx = df[["cp_loss","phasis","loss"]].groupby(["phasis","loss"]).count().reset_index()

    xxl = xx[xx["loss"] == 1]
    xxl = xxl.drop(["loss"], axis=1)
    xxl = xxl.set_index("phasis")
    xxl.columns = ["loss"]

    xx_total = xxw.join(xxd).fillna(0).join(xxl)

    # add percentages
    xx_total["rsum"] = xx_total.sum(axis=1)

    xx_total["win%"] = xx_total.wins /  xx_total.rsum * 100
    xx_total["draw%"] = xx_total.draws /  xx_total.rsum * 100
    xx_total["loss%"] = xx_total.loss /  xx_total.rsum * 100

    xx_total = xx_total.drop(["rsum"],axis=1)

    xx_total = xx_total.sort_index(ascending=False)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = xx_total["win%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Wins: %{text}' + 
                        '<br>Win percentage %{y:.2f} %<extra></extra>',
        text = xx_total.wins.to_list(),
        name = "Win %",
        marker = dict(
            color = 'rgba(0,128,0,0.6)',
            line=dict(color='rgba(0,128,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
    ))

    fig.add_trace(go.Bar(
        y = xx_total["draw%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Draws: %{text}' + 
                        '<br>Draw percentage %{y:.2f} %<extra></extra>',
        text = xx_total.draws.to_list(),
        name = "Draw %",
        marker = dict(
            color = 'rgba(211,211,211,0.6)',
            line=dict(color='rgba(211,211,211,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(0, 0, 0)'
        )
    ))

    fig.add_trace(go.Bar(
        y = xx_total["loss%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Losses: %{text}' + 
                        '<br>Loss percentage %{y:.2f} %<extra></extra>',
        text = xx_total.loss.to_list(),
        name = "Loss %",
        marker = dict(
            color = 'rgba(255,0,0,0.6)',
            line=dict(color='rgba(255,0,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
    ))

    fig.update_layout(
        yaxis=dict(
        title_text="%",
        ticktext=["0%", "20%", "40%", "60%","80%","100%"],
        tickvals=[0, 20, 40, 60, 80, 100],
        tickmode="array",
        titlefont=dict(size=15),
        
    ),
    autosize=False,
    #width=1000,
    #height=400,
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    title={
        'text': "Results when game ends in phase...",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    barmode='stack',
    template="plotly_dark",
    )

    

    return fig 


### gtype

@app.callback(Output('graph-gtype', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_gtype(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["id","gametype"]].groupby(["gametype"]).count().reset_index()

    xx.columns = ["gametype","#games"]

    fig = go.Figure(
        data=[go.Pie(labels=xx["gametype"], values=xx["#games"], hole=.3)]
    )

    fig.update_layout(
        
        autosize=False,
        #width=1000,
        #height=400,
        #paper_bgcolor='rgba(0,0,0,0)',
        #plot_bgcolor='rgba(0,0,0,0)',
        title={
            'text': "Game types",
            #'y':0.96,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'},
        barmode='stack',
        template="plotly_dark",
    )

    #fig.update_yaxes(visible=False, showticklabels=False)
   
    return fig 
        
@app.callback(Output('graph-gtype-cploss', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_gtype_cploss(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["cp_loss","gametype"]].groupby(["gametype"]).mean()

    xx = xx.reset_index()    
    xx = xx.sort_values(["gametype"], ascending=False)

    xx["cp_loss"] = xx["cp_loss"].astype(int)

    #fig = px.bar(xx, x="phasis", y="cp_loss")


    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = xx.cp_loss,
        x = xx.gametype,
        #hovertemplate = '<b>Opening</b>' +
        #                '<br>Games played: %{text}' + 
        #                '<br>Percentage %{x:.2f} %<extra></extra>',
        #text = xx.opening.to_list(),
        name = "Opening %",
        marker = dict(
            color = 'rgba(51,172,210,0.6)',
            line=dict(color='rgba(51,172,210,0.6)', width=0.05)
        ),
        #orientation='h',
    ))


    fig.update_layout(
        yaxis=dict(
        title_text="centipawn loss",
        titlefont=dict(size=15),
    ),
    
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    autosize=False,
    title={
        'text': "Centipawn loss by game type",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    template="plotly_dark",
    )
   
    return fig 

@app.callback(Output('graph-gtype-result', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_gtype_result(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["cp_loss","gametype","win"]].groupby(["gametype","win"]).count().reset_index()

    xxw = xx[xx["win"] == 1]
    xxw = xxw.drop(["win"], axis=1)
    xxw = xxw.set_index("gametype")
    xxw.columns = ["wins"]


    xx = df[["cp_loss","gametype","draw"]].groupby(["gametype","draw"]).count().reset_index()

    xxd = xx[xx["draw"] == 1]
    xxd = xxd.drop(["draw"], axis=1)
    xxd = xxd.set_index("gametype")
    xxd.columns = ["draws"]

    xx = df[["cp_loss","gametype","loss"]].groupby(["gametype","loss"]).count().reset_index()

    xxl = xx[xx["loss"] == 1]
    xxl = xxl.drop(["loss"], axis=1)
    xxl = xxl.set_index("gametype")
    xxl.columns = ["loss"]

    xx_total = xxw.join(xxd).fillna(0).join(xxl)

    # add percentages
    xx_total["rsum"] = xx_total.sum(axis=1)

    xx_total["win%"] = xx_total.wins /  xx_total.rsum * 100
    xx_total["draw%"] = xx_total.draws /  xx_total.rsum * 100
    xx_total["loss%"] = xx_total.loss /  xx_total.rsum * 100

    xx_total = xx_total.drop(["rsum"],axis=1)

    xx_total = xx_total.sort_index(ascending=False)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = xx_total["win%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Wins: %{text}' + 
                        '<br>Win percentage %{y:.2f} %<extra></extra>',
        text = xx_total.wins.to_list(),
        name = "Win %",
        marker = dict(
            color = 'rgba(0,128,0,0.6)',
            line=dict(color='rgba(0,128,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
    ))

    fig.add_trace(go.Bar(
        y = xx_total["draw%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Draws: %{text}' + 
                        '<br>Draw percentage %{y:.2f} %<extra></extra>',
        text = xx_total.draws.to_list(),
        name = "Draw %",
        marker = dict(
            color = 'rgba(211,211,211,0.6)',
            line=dict(color='rgba(211,211,211,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(0, 0, 0)'
        )
    ))

    fig.add_trace(go.Bar(
        y = xx_total["loss%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Losses: %{text}' + 
                        '<br>Loss percentage %{y:.2f} %<extra></extra>',
        text = xx_total.loss.to_list(),
        name = "Loss %",
        marker = dict(
            color = 'rgba(255,0,0,0.6)',
            line=dict(color='rgba(255,0,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
    ))

    fig.update_layout(
        yaxis=dict(
        title_text="%",
        ticktext=["0%", "20%", "40%", "60%","80%","100%"],
        tickvals=[0, 20, 40, 60, 80, 100],
        tickmode="array",
        titlefont=dict(size=15),
        
    ),
    autosize=False,
    #width=1000,
    #height=400,
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    title={
        'text': "Results by game type",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    barmode='stack',
    template="plotly_dark",
    )

    

    return fig 

## eo gypte


@app.callback(Output('graph-daytime', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_daytime(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["id","daytime"]].groupby(["daytime"]).count().reset_index()

    xx.columns = ["daytime","#games"]

    fig = go.Figure(
        data=[go.Pie(labels=xx["daytime"], values=xx["#games"], hole=.3)]
    )


    fig.update_layout(
        
        autosize=False,
        #width=1000,
        #height=400,
        #paper_bgcolor='rgba(0,0,0,0)',
        #plot_bgcolor='rgba(0,0,0,0)',
        title={
            'text': "Games played during the day",
            #'y':0.96,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'},
        barmode='stack',
        template="plotly_dark",
    )

    

    return fig 


@app.callback(Output('graph-daytime-cploss', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_daytime_cploss(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["cp_loss","daytime"]].groupby(["daytime"]).mean()

    xx = xx.reset_index()    
    xx = xx.sort_values(["daytime"], ascending=False)

    xx["cp_loss"] = xx["cp_loss"].astype(int)

    daytime_sort = {
        "morning" : 1,
        "afternoon": 2,
        "evening":3,
        "night": 4
    }

    xx["sort_key"] = xx.daytime.apply(lambda x: daytime_sort[x])

    xx = xx.sort_values(["sort_key"])

    #fig = px.bar(xx, x="phasis", y="cp_loss")

    
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = xx.cp_loss,
        x = xx.daytime,
        #hovertemplate = '<b>Opening</b>' +
        #                '<br>Games played: %{text}' + 
        #                '<br>Percentage %{x:.2f} %<extra></extra>',
        #text = xx.opening.to_list(),
        name = "Opening %",
        marker = dict(
            color = 'rgba(51,172,210,0.6)',
            line=dict(color='rgba(51,172,210,0.6)', width=0.05)
        ),
        #orientation='h',
    ))


    fig.update_layout(
        yaxis=dict(
        title_text="centipawn loss",
        titlefont=dict(size=15),
    ),
    
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    autosize=False,
    title={
        'text': "Centipawn loss by daytime",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    template="plotly_dark",
    )
   
    

    return fig 


@app.callback(Output('graph-daytime-result', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_daytime_result(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["cp_loss","daytime","win"]].groupby(["daytime","win"]).count().reset_index()

    xxw = xx[xx["win"] == 1]
    xxw = xxw.drop(["win"], axis=1)
    xxw = xxw.set_index("daytime")
    xxw.columns = ["wins"]


    xx = df[["cp_loss","daytime","draw"]].groupby(["daytime","draw"]).count().reset_index()

    xxd = xx[xx["draw"] == 1]
    xxd = xxd.drop(["draw"], axis=1)
    xxd = xxd.set_index("daytime")
    xxd.columns = ["draws"]

    xx = df[["cp_loss","daytime","loss"]].groupby(["daytime","loss"]).count().reset_index()

    xxl = xx[xx["loss"] == 1]
    xxl = xxl.drop(["loss"], axis=1)
    xxl = xxl.set_index("daytime")
    xxl.columns = ["loss"]

    xx_total = xxw.join(xxd).fillna(0).join(xxl)

    # add percentages
    xx_total["rsum"] = xx_total.sum(axis=1)

    xx_total["win%"] = xx_total.wins /  xx_total.rsum * 100
    xx_total["draw%"] = xx_total.draws /  xx_total.rsum * 100
    xx_total["loss%"] = xx_total.loss /  xx_total.rsum * 100

    xx_total = xx_total.drop(["rsum"],axis=1)

    daytime_sort = {
        "morning" : 1,
        "afternoon": 2,
        "evening":3,
        "night": 4
    }

    xx_total = xx_total.reset_index()
    xx_total["sort_key"] = xx_total.daytime.apply(lambda x: daytime_sort[x])
    xx_total = xx_total.sort_values(["sort_key"]).set_index("daytime")
    



    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = xx_total["win%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Wins: %{text}' + 
                        '<br>Win percentage %{y:.2f} %<extra></extra>',
        text = xx_total.wins.to_list(),
        name = "Win %",
        marker = dict(
            color = 'rgba(0,128,0,0.6)',
            line=dict(color='rgba(0,128,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
    ))

    fig.add_trace(go.Bar(
        y = xx_total["draw%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Draws: %{text}' + 
                        '<br>Draw percentage %{y:.2f} %<extra></extra>',
        text = xx_total.draws.to_list(),
        name = "Draw %",
        marker = dict(
            color = 'rgba(211,211,211,0.6)',
            line=dict(color='rgba(211,211,211,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(0, 0, 0)'
        )
    ))

    fig.add_trace(go.Bar(
        y = xx_total["loss%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Losses: %{text}' + 
                        '<br>Loss percentage %{y:.2f} %<extra></extra>',
        text = xx_total.loss.to_list(),
        name = "Loss %",
        marker = dict(
            color = 'rgba(255,0,0,0.6)',
            line=dict(color='rgba(255,0,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
    ))

    fig.update_layout(
        yaxis=dict(
        title_text="%",
        ticktext=["0%", "20%", "40%", "60%","80%","100%"],
        tickvals=[0, 20, 40, 60, 80, 100],
        tickmode="array",
        titlefont=dict(size=15),
        
    ),
    autosize=False,
    #width=1000,
    #height=400,
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    title={
        'text': "Results on a specific time of the day",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    barmode='stack',
    template="plotly_dark",
    )

    

    return fig 


# weekday

@app.callback(Output('graph-weekday', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_weekday(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["id","weekday"]].groupby(["weekday"]).count().reset_index()

    xx.columns = ["weekday","#games"]

    fig = go.Figure(
        data=[go.Pie(labels=xx["weekday"], values=xx["#games"], hole=.3)]
    )


    fig.update_layout(
        
        autosize=False,
        #width=1000,
        #height=400,
        #paper_bgcolor='rgba(0,0,0,0)',
        #plot_bgcolor='rgba(0,0,0,0)',
        title={
            'text': "Games played by week day",
            #'y':0.96,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'},
        barmode='stack',
        template="plotly_dark",
    )

    

    return fig 


@app.callback(Output('graph-weekday-cploss', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_weekday_cploss(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["cp_loss","weekday"]].groupby(["weekday"]).mean()

    xx = xx.reset_index()    
    xx = xx.sort_values(["weekday"], ascending=False)

    xx["cp_loss"] = xx["cp_loss"].astype(int)

    weekday_sort = {
        "Monday" : 1,
        "Tuesday": 2,
        "Wednesday":3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7,
    }

    xx["sort_key"] = xx.weekday.apply(lambda x: weekday_sort[x])

    xx = xx.sort_values(["sort_key"])

    #fig = px.bar(xx, x="phasis", y="cp_loss")

    
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = xx.cp_loss,
        x = xx.weekday,
        #hovertemplate = '<b>Opening</b>' +
        #                '<br>Games played: %{text}' + 
        #                '<br>Percentage %{x:.2f} %<extra></extra>',
        #text = xx.opening.to_list(),
        name = "Opening %",
        marker = dict(
            color = 'rgba(51,172,210,0.6)',
            line=dict(color='rgba(51,172,210,0.6)', width=0.05)
        ),
        #orientation='h',
    ))


    fig.update_layout(
        yaxis=dict(
        title_text="centipawn loss",
        titlefont=dict(size=15),
    ),
    
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    autosize=False,
    title={
        'text': "Centipawn loss by week day",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    template="plotly_dark",
    )
   
    

    return fig 


@app.callback(Output('graph-weekday-result', 'figure'),
              [Input('input-player','value'), Input('dropdown-timecontrol','value'),Input('date-picker', 'start_date'),Input('date-picker', 'end_date')])
def update_graph_weekday_result(player_name, time_control, min_date, max_date):

    df = frame_dict[player_name.lower()]

    df = df[(df["PlayedOn"] >= min_date) & (df["PlayedOn"] <= max_date)]

    xx = df[["cp_loss","weekday","win"]].groupby(["weekday","win"]).count().reset_index()

    xxw = xx[xx["win"] == 1]
    xxw = xxw.drop(["win"], axis=1)
    xxw = xxw.set_index("weekday")
    xxw.columns = ["wins"]


    xx = df[["cp_loss","weekday","draw"]].groupby(["weekday","draw"]).count().reset_index()

    xxd = xx[xx["draw"] == 1]
    xxd = xxd.drop(["draw"], axis=1)
    xxd = xxd.set_index("weekday")
    xxd.columns = ["draws"]

    xx = df[["cp_loss","weekday","loss"]].groupby(["weekday","loss"]).count().reset_index()

    xxl = xx[xx["loss"] == 1]
    xxl = xxl.drop(["loss"], axis=1)
    xxl = xxl.set_index("weekday")
    xxl.columns = ["loss"]

    xx_total = xxw.join(xxd).fillna(0).join(xxl)

    # add percentages
    xx_total["rsum"] = xx_total.sum(axis=1)

    xx_total["win%"] = xx_total.wins /  xx_total.rsum * 100
    xx_total["draw%"] = xx_total.draws /  xx_total.rsum * 100
    xx_total["loss%"] = xx_total.loss /  xx_total.rsum * 100

    xx_total = xx_total.drop(["rsum"],axis=1)

    weekday_sort = {
        "Monday" : 1,
        "Tuesday": 2,
        "Wednesday":3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7,
    }

    xx_total = xx_total.reset_index()
    xx_total["sort_key"] = xx_total.weekday.apply(lambda x: weekday_sort[x])
    xx_total = xx_total.sort_values(["sort_key"]).set_index("weekday")
    



    fig = go.Figure()

    fig.add_trace(go.Bar(
        y = xx_total["win%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Wins: %{text}' + 
                        '<br>Win percentage %{y:.2f} %<extra></extra>',
        text = xx_total.wins.to_list(),
        name = "Win %",
        marker = dict(
            color = 'rgba(0,128,0,0.6)',
            line=dict(color='rgba(0,128,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
    ))

    fig.add_trace(go.Bar(
        y = xx_total["draw%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Draws: %{text}' + 
                        '<br>Draw percentage %{y:.2f} %<extra></extra>',
        text = xx_total.draws.to_list(),
        name = "Draw %",
        marker = dict(
            color = 'rgba(211,211,211,0.6)',
            line=dict(color='rgba(211,211,211,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(0, 0, 0)'
        )
    ))

    fig.add_trace(go.Bar(
        y = xx_total["loss%"],
        x = xx_total.index,
        hovertemplate = 'Rating: %{x}' +
                        '<br>Losses: %{text}' + 
                        '<br>Loss percentage %{y:.2f} %<extra></extra>',
        text = xx_total.loss.to_list(),
        name = "Loss %",
        marker = dict(
            color = 'rgba(255,0,0,0.6)',
            line=dict(color='rgba(255,0,0,0.6)', width=0.05)
        ),
        textfont=dict(
            color='rgb(255, 255, 255)'
        )
    ))

    fig.update_layout(
        yaxis=dict(
        title_text="%",
        ticktext=["0%", "20%", "40%", "60%","80%","100%"],
        tickvals=[0, 20, 40, 60, 80, 100],
        tickmode="array",
        titlefont=dict(size=15),
        
    ),
    autosize=False,
    #width=1000,
    #height=400,
    #paper_bgcolor='rgba(0,0,0,0)',
    #plot_bgcolor='rgba(0,0,0,0)',
    title={
        'text': "Results on specific week day",
        #'y':0.96,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'},
    barmode='stack',
    template="plotly_dark",
    )

    

    return fig 

## elo cross



@app.callback(Output('table-elocross', 'data'),
    [Input('input-player','value')])
def update_table_elocross(player_name):

    df = frame_dict[player_name.lower()]

    dff = df.copy()

    dff = dff.sort_values(["PlayedOn"])

    dff["elo"] = dff.apply(lambda x: x["blackelo_pre"] if x["black"].lower() == player_name.lower() else x["whiteelo_pre"], axis=1)
    
    inv = dff[["PlayedOn","elo"]]

    inv["diff"] = inv["elo"].diff(-1)

    inv["nextelo"] = inv["elo"] + (-1 * inv["diff"])

    inv = inv.drop(["diff"],axis=1)

    out_list = []
    all_elo = [1000,1100,1200,1300,1400,1500,1600,1700,1800,1900,2000,2100,2200,2300,2400,2500,2600,2700,2800,2900,3000]

    #[{'col1': 1, 'col2': 0.5}, {'col1': 2, 'col2': 0.75}]

    for e in all_elo:
        #reaching elo
        reaching_elo = len(inv[ (inv["elo"] >= e-5) & (inv["nextelo"] < e)])
        #crossed elo
        crossed_elo = len(inv[ (inv["elo"] < e) & (inv["nextelo"] >= e)])

        if crossed_elo > reaching_elo:
            reaching_elo = crossed_elo

        if reaching_elo > 0:

            success_rate = str(int(crossed_elo / reaching_elo * 100)) + " %"
            #success_rate = int(float(crossed_elo) / reaching_elo * 100)
            out_list.append({'elo': e, 'milestone_reached': reaching_elo, 'milestone_crossed': crossed_elo,'success_rate': success_rate})


    
    return out_list

if __name__ == '__main__':
    app.run_server()