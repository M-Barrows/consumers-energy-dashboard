import requests
import pandas as pd
from dotenv import load_dotenv
import os 
import json 
import dash
import dash_html_components as html
from datetime import date
import plotly.express as px
from constants import RATES
from itertools import chain
from flask_caching import Cache
load_dotenv() 

app = dash.Dash(__name__)
config = {
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300
}
cache = Cache(app.server, config=config)

def get_time_category(hour:int):
    if hour in chain(range(6,14),range(19,23)):
        return 'off_peak'
    elif hour in chain(range(6),range(23,25)):
        return 'super_off_peak'
    else:
        return 'peak'

def get_rate(row,rate_name:str):
    return RATES[rate_name][row['season']][row['time_category']]['rate']

def get_color(row,rate_name:str):
    return RATES[rate_name][row['season']][row['time_category']]['color']

def transform_data(df,rate_name):
    data = df.copy()
    data['start'] = pd.to_datetime(data['start'])
    data['hour'] = data['start'].dt.hour
    data['month'] = data['start'].dt.month
    data['date'] = data['start'].dt.date
    data['season'] = data.apply(lambda x: 'summer' if x['month'] in range(6,10) else 'winter',axis=1)
    data['time_category'] = data['hour'].apply(get_time_category)
    data['rate'] = data.apply(get_rate,rate_name=rate_name,axis=1)
    data['cost'] = round(data['rate'] * df['kwh']/100,2)
    data = data.join(data[['time_category','date','cost']].groupby(by=['date','time_category']).mean(),on=['date','time_category'],rsuffix='_cat_avg')
    data = data.join(data[['time_category','date','kwh']].groupby(by=['date','time_category']).mean(),on=['date','time_category'],rsuffix='_cat_avg')
    data['color'] = data.apply(get_color,rate_name=rate_name,axis=1)
    return data



@cache.memoize(timeout=3600)
def get_data(date):
    response = requests.get(url=f"https://utilityapi.com/api/v2/intervals?meters={','.join(json.loads(os.environ.get('METERS')))}&start={date}",headers=json.loads(os.environ.get('HEADERS'))) 
    data = response.json() 
    readings = data['intervals'][0]['readings']
    flat_readings = [{k: reading.get(k,None) for k in ('start', 'kwh')} for reading in readings]
    return pd.DataFrame(flat_readings)


app.layout = [
    html.Div("Energy Meter"),
    dash.dcc.DatePickerSingle(
        id='date-picker',
        min_date_allowed=date(2022, 8, 5),
        max_date_allowed=date(2024, 9, 19),
        initial_visible_month=date(2024, 1, 1),
        date=date(2024,1,1)
    ),
    dash.html.Div([
        dash.html.H3("Current Rate Type"),
        dash.dcc.Dropdown(
        list(RATES.keys()),
        list(RATES.keys())[0],
        id='rate-picker',
    ),
    ]),
    dash.html.Div([
        dash.html.H3("shift excess peak load to:"),
        dash.dcc.Dropdown(
        ['off_peak','super_off_peak'],
        'off_peak',
        id='shift-picker',
    ),
    ]),
    
    dash.html.Div(id='current-total'),
    dash.html.Div(id='adjusted-total'),
    dash.dcc.Graph(id='energy-graph')
]


@dash.callback(
        dash.Output('current-total','children'),
        dash.Input('date-picker','date'),
        dash.Input('rate-picker','value'),
)
def get_current_total(date,rate_name):
    df = get_data(date)
    df = transform_data(df,rate_name)
    return dash.html.H2(f"Current Total: ${df['cost'].sum():,.2f}")

def shift_usage(row,target_time_category):
    r = row.copy()
    if row['kwh']['peak'] - row['kwh_cat_avg']['peak'] > 0:
        r['kwh'][target_time_category] = row['kwh']['peak'] - row['kwh_cat_avg']['peak']
        r['kwh']['peak'] = row['kwh_cat_avg']['peak']
    return r

def calculate_adjusted_rate(row):
    r = row.copy()
    r['super_off_peak_cost']= (row['super_off_peak_kwh']*row['super_off_peak_rate'] ) 
    r['off_peak_cost'] = (row['off_peak_kwh']*row['off_peak_rate'] )
    r['peak_cost'] = (row['peak_kwh']*row['peak_rate'] )
    r['cost'] = (r['super_off_peak_cost'] + r['off_peak_cost'] + r['peak_cost'])
    return r

@dash.callback(
        dash.Output('adjusted-total','children'),
        dash.Input('date-picker','date'),
        dash.Input('rate-picker','value'),
        dash.Input('shift-picker','value')
)
def get_adjusted_total(date,rate_name,target_time_category):
    df = get_data(date)
    df = transform_data(df,rate_name)
    new_df = df[['start','kwh','kwh_cat_avg','time_category']].pivot(index='start',columns='time_category',values=['kwh','kwh_cat_avg'])
    adjusted_df = new_df.apply(shift_usage,target_time_category=target_time_category,axis=1)['kwh']
    adjusted_df = adjusted_df.join(df[['start','rate','time_category']].drop_duplicates().pivot(index='start',columns='time_category',values='rate'),lsuffix="_kwh",rsuffix="_rate")
    cost_df = adjusted_df.fillna(0).apply(calculate_adjusted_rate, axis=1)
    print(cost_df)
    #[['start','cost']].groupby('start').sum()
    
    return dash.html.H2(f"Adjusted Total: ${cost_df['cost'].sum()/100:,.2f}")

@dash.callback(
        dash.Output('energy-graph','figure'),
        dash.Input('date-picker','date'),
        dash.Input('rate-picker','value'),
)
def update(date,rate_name):
    df = get_data(date)
    df = transform_data(df,rate_name)
    a = px.bar(df, x='start', y='kwh',color='color',color_discrete_map="identity")
    for cat in df['time_category'].unique():
        a.add_hline(
            df.loc[df['time_category']==cat].iloc[0]['kwh_cat_avg'],
            line_color=df.loc[df['time_category']==cat].iloc[0]['color'],
            annotation_text=cat,
            annotation_position="right",
            line_dash='dot')
    return a

if __name__ == '__main__':
    app.run_server(debug=True)
