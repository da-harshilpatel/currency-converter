import pandas as pd
import os
import requests
from datetime import datetime, date, timedelta
import json
import plotly.express as px
from prophet import Prophet

cache = {
    "data": None
}

def getdate():
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=365)
    end_date = end_date.isoformat()
    start_date = start_date.isoformat()
    return end_date, start_date;

    

def url_builder():
    end_date, start_date = getdate()
    url = f"https://api.apilayer.com/exchangerates_data/timeseries?start_date={start_date}&end_date={end_date}"
    payload = {}

    headers = {
        "apikey": "shU3YpzInoBZbHH58BwwC3BUs4Szgdi1"
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    status_code = response.status_code
    result = response.text
    print("API is being called...")
    return result;                   #This returns data in json format which is string for python


def get_cached_data():
    global cache
    if cache['data'] is not None:
        return cache['data']    
    else:
        df = transform_data()
        cache['data'] = df
        return df


def transform_data():
    api_data = url_builder()
    api_response = json.loads(api_data)  #Converting data to python dictionary
    df = pd.DataFrame(api_response['rates']) #only want to extract rates part from dict

    df = df.reset_index() #reset index as the data we have does not have a header for the first column and no indexing
    df_melted = df.melt(id_vars='index', var_name = 'Date', value_name = 'Rate')
    df_melted = df_melted.rename(columns = {'index': 'Currency'})

    return df_melted;


def etl_process():
    df = get_cached_data()
    
    df['Date'] = pd.to_datetime(df['Date'])
    df['Rate'] = pd.to_numeric(df['Rate'], errors='coerce')
    df = df.sort_values(by=['Date', 'Currency'])

    df = df.dropna(subset=["Date", "Currency", "Rate"])

    return df;


def convert(source_amount, source_currency, dest_currency):

    try:
        source_amount = float(source_amount)
    except ValueError:
        return "Enter numeric values"
    
    df = etl_process()
    latest_date = df['Date'].max()
    
    latest_df = df[df['Date'] == latest_date]

    source_rate = latest_df.loc[latest_df['Currency'] == source_currency, 'Rate'].values
    dest_rate = latest_df.loc[latest_df['Currency'] == dest_currency, 'Rate'].values

    if len(source_rate) == 0 or len(dest_rate) == 0:
        return "Invalid currency selection"

    dest_amnt = (source_amount*dest_rate[0])/source_rate[0]

    return round(dest_amnt, 2);

def change_rate():
    df = etl_process()

    latest_date = latest_date = df['Date'].max()
    prev_date = latest_date - timedelta(days=1)

    new_df = df[(df['Date'] == latest_date) | (df['Date'] == prev_date)]

    new_df = new_df.sort_values(by = ['Currency', 'Date'])

    new_df['change_rate'] = new_df.groupby('Currency')['Rate'].pct_change()*100
    new_df = new_df[new_df['Date'] == latest_date]
    new_df = new_df.dropna()
    new_df = new_df.sort_values(by = ['change_rate'])
    new_df['change_rate'] = new_df['change_rate'].round(3)
    top_loss = new_df.head(5)
    top_gain = new_df.tail(5).sort_values(by = ['change_rate'], ascending = False)

    return top_gain, top_loss;



def show_chart(source_currency, dest_currency):
    df = etl_process();
    source_df = df[df['Currency']== source_currency]
    source_df = source_df.rename(columns = {"Currency": "Source currency", "Rate" : "Source rate"})
    dest_df =  df[df['Currency']== dest_currency]
    dest_df = dest_df.rename(columns = {"Currency": "Dest currency", "Rate" : "Dest rate"})
    
    plotting_df = source_df.merge(dest_df[['Date', 'Dest currency', 'Dest rate']], on = ['Date'], how = 'inner')
    plotting_df['Final rate'] = plotting_df['Dest rate']/plotting_df['Source rate']

    chart_label = str(1 ) + source_currency
    
    fig = px.line(plotting_df, x = 'Date', y = 'Final rate', labels = {"Final rate" : chart_label},
    title=f'Trends Between {source_currency} and {dest_currency}',
    )

    fig.update_layout(
        yaxis_title = dest_currency
    )
    return plotting_df, fig;


def forecast(source_currency, dest_currency):
    df, fig = show_chart(source_currency, dest_currency)

    df_prophet = df.rename(columns = {"Date": "ds", "Final rate": "y"})

    model = Prophet()
    model.fit(df_prophet)

    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)

    
    forecast = forecast.rename(columns = {"ds": "Date", "yhat": "Final rate"})
    forecast = forecast[['Date', 'Final rate']]

    forecasting_date = forecast['Date'].max() - timedelta(days = 30)
    forecast = forecast[forecast['Date'] >= forecasting_date]
    fig = px.line(forecast, x = 'Date', y = 'Final rate', title=f'Trends Between {source_currency} and {dest_currency}')
    return forecast, fig;