"""CSC110 Fall 2021 Group Project :)

===============================
For visualizing covid data and hpi data on an HTML page.
===============================

This file is copyright free.
"""

###########
# Imports #
###########

# For reading data files
import csv
import json

# For creating dataframes
import pandas

# For plot and map
import plotly.express as px

# For displaying stuff on html page
import dash
from dash import html
from dash import dcc
from dash.dependencies import Input, Output


def convert_day(date: str) -> tuple[int, int, int]:
    """
    Converts the date from any data to a list of two integers representing a specific month.
    Because the format from different csv files varies, this function checks for what format is used

    >>> convert_day('2018-05')
    (2018, 5, 1)

    >>> convert_day('2003-05-17')
    (2003, 5, 17)

    >>> convert_day('1/31/2020')
    (2020, 1, 31)
    """
    if '/' in date:
        day = date.split('/')
        return int(day[2]), int(day[0]), int(day[1])
    else:
        day = date.split('-')
        if len(day) == 2:
            day.append('1')
        return int(day[0]), int(day[1]), int(day[2])


# Function for loading data
def load_data() -> list[dict]:
    """
    This function loads the two csv files that are placed in the same folder as this python file
    and turns the csv files into a list of dictionaries, allowing it to be loaded into one dataframe.
    """

    # data_dict a placeholder, for ease of combining two datasets
    data_dict = {}

    with open(covid_filename) as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skips first row

        for row in reader:
            # Filters out Canada and Repatriated Travellers entries
            if row[1] in provinces:
                if provinces[row[1]] not in data_dict:
                    data_dict[provinces[row[1]]] = {}
                data_dict[provinces[row[1]]][convert_day(row[3])] = [float(row[17]), float(row[26]), 0]
                # row 17 is the total # of cases + deaths per 100k population
                # row 26 is the current active # of cases per 100k population

    with open(nhpi_filename) as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skips first row

        for row in reader:
            if row[1] in provinces and row[3] == 'House only':
                # Some entries are empty
                if row[10] == '':
                    value = 0
                else:
                    value = float(row[10])
                date = convert_day(row[0])
                for day in range(1, days_in_month[date[1]] + 1):
                    ddd = (date[0], date[1], day)
                    if ddd in data_dict[provinces[row[1]]]:
                        data_dict[provinces[row[1]]][ddd][2] = value
                    else:
                        data_dict[provinces[row[1]]][ddd] = [0, 0, value]

    # This turns the nested dictionaries into a list of dictionaries.
    data = []
    for province in data_dict:
        for date in data_dict[province]:
            placeholder = data_dict[province][date]
            data.append({
                'cartodb_id': province,
                'date': date,
                'string_date': '-'.join(map(str, date)),
                'hpi': placeholder[2],
                'total_per_100k': placeholder[0],
                'active_per_100k': placeholder[1]
            })

    return data


# Main Block
if __name__ == '__main__':

    # Name of Data Files
    nhpi_filename = "18100205.csv"
    covid_filename = "covid19-download.csv"

    # List of Province Names (and territories)
    provinces = {'Ontario': 11, 'British Columbia': 6, 'Quebec': 1, 'Manitoba': 10, 'Nova Scotia': 2,
                 'Newfoundland and Labrador': 5, 'New Brunswick': 7, 'Saskatchewan': 3, 'Yukon': 9,
                 'Alberta': 4, 'Prince Edward Island': 8, 'Northwest Territories': 13, 'Nunavut': 12}

    global prov

    # Useful dictionaries
    month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul',
                   8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

    days_in_month = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                     7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

    # Month Slider Stuff
    m_slider_marks = {}
    day_count = 0
    for month in range(1, 13):
        day_count += days_in_month[month]
        m_slider_marks[day_count] = month_names[month]

    # Loading data into dataframe
    dataset = load_data()
    df = pandas.DataFrame(dataset)

    # Defining plotly figures
    choropleth_map = px.choropleth()
    total_graph = px.line()
    active_graph = px.line()
    hpi_graph = px.line()

    # Loading GeoJSON
    with open("canada_provinces.geojson") as geo:
        canada = json.load(geo)

    # List of Possible Years for Slider
    possible_years = sorted({item['date'][0] for item in dataset})

    # Defining the DASH app
    app = dash.Dash(__name__)

    # HTML app layout
    app.layout = html.Div([

        html.H1("COVID and HPI data visualization"),

        dcc.RadioItems(
            id='data_select',
            options=[
                {'label': 'Total Cases', 'value': 'total_per_100k'},
                {'label': 'Active Cases', 'value': 'active_per_100k'},
                {'label': 'HPI', 'value': 'hpi'}
            ],
            value='active_per_100k'
        ),

        dcc.Slider(
            id='year_slider',
            min=possible_years[0],
            max=possible_years[-1],
            step=1,
            value=possible_years[-1],
            marks={year: str(year) for year in possible_years}
        ),

        dcc.Slider(
            id='month_slider',
            min=1,
            max=365,
            step=1,
            value=1,
            marks=m_slider_marks
        ),

        html.Div(children=[
            html.Div(children=(html.Div(children=[dcc.Graph(id='choro_map', figure=choropleth_map),
                               dcc.Graph(id='total_graph', figure=total_graph)])),
                     style={'width': '49%', 'display': 'inline-block'}
                     ),
            html.Div(children=(html.Div(children=[dcc.Graph(id='hpi_graph', figure=hpi_graph),
                               dcc.Graph(id='active_graph', figure=active_graph)])),
                     style={'width': '49%', 'float': 'right', 'display': 'inline-block'}
                     )
        ], className='row')

    ])

    # Callback that updates the map after slider change
    @app.callback(
        Output('choro_map', 'figure'),
        [Input('year_slider', 'value'),
         Input('month_slider', 'value'),
         Input('data_select', 'value')])
    def update_map(year, day, datatype):
        month = 1
        while day > days_in_month[month]:
            day -= days_in_month[month]
            month += 1
        dff = df[df['date'] == (year, month, day)]

        global scale_color
        global color_range
        if datatype == 'active_per_100k':
            scale_color = 'Reds'
            color_range = [0, 1000]
        elif datatype == 'total_per_100k':
            scale_color = 'amp'
            color_range = [0, 10000]
        elif datatype == 'hpi':
            scale_color = 'PuBu'
            color_range = [30, 150]

        # Figure
        choropleth_map = px.choropleth(dff, geojson=canada,
                                       locations='cartodb_id',
                                       featureidkey="properties.cartodb_id",
                                       color=datatype,
                                       color_continuous_scale=scale_color,
                                       range_color=color_range,
                                       scope='north america',
                                       labels={'active_per_100k': 'Active Cases Per 100k Population',
                                               'total_per_100k': 'Total Cases Per 100k Population',
                                               'hpi': 'Housing Price Index'},
                                       fitbounds='geojson',
                                       width=800,
                                       height=400
                                       )
        return choropleth_map

    # Callback that updates graph after click on map
    @app.callback(
        [Output('total_graph', 'figure'),
         Output('active_graph', 'figure'),
         Output('hpi_graph', 'figure')],
        Input('choro_map', 'clickData')
    )
    def update_graph(clicked):
        if None is clicked:
            prov = 1
        else:
            prov = clicked["points"][0]["location"]

        # Finding province name
        province_name = ''
        for name in provinces:
            if provinces[name] == prov:
                province_name = name

        # Filtering dataset by province clicked
        dff1 = df[(df['cartodb_id'] == prov) & (df['string_date'] > '2019-06-01')]
        dff1 = dff1.sort_values(by='date')

        total_graph = px.line(dff1, x='string_date', y='total_per_100k',
                              title='Total Cases Per 100k Population in ' + province_name)
        active_graph = px.line(dff1, x='string_date', y='active_per_100k',
                               title='Active Cases Per 100k Population in ' + province_name)

        # Same as above, different date range for graph
        dff2 = df[(df['cartodb_id'] == prov) & (df['string_date'] > '2000-01-01')]
        dff2 = dff2.sort_values(by='date')
        hpi_graph = px.line(dff2, x='string_date', y='hpi',
                            title='Housing Price Index in ' + province_name)

        return total_graph, active_graph, hpi_graph

    app.run_server()
