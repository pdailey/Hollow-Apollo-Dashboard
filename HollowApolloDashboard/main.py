# TODO: remove duplicates from SQL DB

from os.path import dirname, join
from pathlib import Path

import os

import tkinter as tk
from tkinter import filedialog

import numpy as np
import pandas.io.sql as psql
import pandas as pd
import sqlite3 as sql

from bokeh.plotting import figure
from bokeh.layouts import layout, widgetbox, column
from bokeh.models import ColumnDataSource, HoverTool, Div, DataRange1d
from bokeh.models.glyphs import Patch
from bokeh.models.widgets import Slider, Select, TextInput, Button, MultiSelect, RadioButtonGroup, CheckboxButtonGroup
from bokeh.io import curdoc
import bokeh.palettes as bp


# TODO: if exists, else create new
table = join(dirname(__file__), "sql_table.db")
sql_conn = sql.connect(table)
c = sql_conn.cursor()


def browseFiles(filetype=[("CSV", "*.csv")]):
    '''Opens a tk window to browse for files. Returns a
    list of files with full path'''

    root = tk.Tk()
    root.withdraw()
    root.update()
    files = filedialog.askopenfilenames(
            parent = root,
            title='Choose CSV files to import',
            filetypes=filetype)
    files = root.tk.splitlist(files)
    root.update()

    print("The following files were selected:")
    for f in files:
        #f = Path(f)
        print(f)

    return files


def renameCols(df):
    # convert unix time to datetime
    df['datetime'] = pd.to_datetime(df['datetime'],unit='s')

    # Rename columns.
    #Some sensors are not correctly addressed in the hardware itself.
    df.rename(columns={' Fan Current L': 'Fan R', ' Fan Currrent R': 'Fan L'}, inplace=True)
    df.rename(columns={' T_L': 'T_R', ' T_R': 'T_L'}, inplace=True)
    df.rename(columns={' RH_L': 'RH_R', ' RH_R': 'RH_L'}, inplace=True)
    df.rename(columns={' T_Out': 'T_Out', ' RH_Out': 'RH_Out'}, inplace=True)

    return df


def addLocationCol(df, _file):
    p = Path(_file)
    filename = p.name

    # get location from the filename
    if "US" in filename:
        loc = "US"
    elif "BJ" in filename:
        loc = "BJ"
    elif "SZ" in filename:
        loc = "SZ"
    else:
        print("ERROR, no location found, data from {} not appended.".format(filename))
        loc = "unknown"

    # add a location column
    df["location"] = loc
    return df

def removeDuplicateRows():
    '''Reads a SQL table, searches for duplicate rows and removes them'''
    # get the query and use it to open df
    query = open(join(dirname(__file__), 'query.sql')).read()
    df = psql.read_sql(query, sql_conn)
    df.fillna(0, inplace=True)  # just replace missing values with zero
    prev_len = len(df.index)

    # remove duplace rows
    df = df.drop_duplicates()
    curr_len = len(df.index)
    diff = prev_len - curr_len

    # replace the SQL table with the new df
    df.to_sql("my_table", sql_conn, if_exists='replace')
    print("\nSQL table had {} rows. \n{} duplicate rows found and removed.".format(prev_len, diff))


def clickBrowse():
    files = browseFiles()

    if len(files)==0:
        print("No files selected.")
        return
    else:
        print("Imported " + str(len(files)) + " data files.")

    for f in files:
        f = Path(f)
        print("file:{}, dir:{}".format(f.name, f.parent))

    # TODO: Save files in hidden dir

    # convert each file to a df, append that df to the master df
    for i, f in enumerate(files):
        #TODO: Verify incoming data
        df = pd.read_csv(f, index_col=False)
        df = renameCols(df)
        df = addLocationCol(df, f)

        # check is we have already created the master df
        if(i == 0):
            df_main = df
        else:
            df_main.append(df)

    # append data to SQL DB
    df_main.to_sql("my_table", sql_conn, if_exists='append')

    # remove duplicates from the SQL table
    # TODO: Unexpected behavior
    #removeDuplicateRows()

query = open(join(dirname(__file__), 'query.sql')).read()
readings = psql.read_sql(query, sql_conn)

readings.fillna(0, inplace=True)  # just replace missing values with zero


# Data

# Create Column Data Source that will be used by the plot
source = ColumnDataSource(data=dict(x=[],
                                    TC_1=[], TC_2=[], TC_3=[], TC_4=[],
                                    TC_5=[], TC_6=[], TC_7=[], TC_8=[],
                                    Fan_L=[], Fan_R=[],
                                    T_L=[], T_R=[], T_Out=[],
                                    RH_L=[], RH_R=[], RH_Out=[]))


# Event Handling
def select_readings():
    list(readings)
    # Select data from only one location specified by the button group
    loc = radio_location.labels[radio_location.active]
    print("LOCATION")
    print(loc)
    selected = readings[readings.location.str.contains(loc) == True]

    return selected

def datetime(x):
        return np.array(x, dtype=np.datetime64)

def update_data(new=None):
    print("UPDATE DATA")
    df = select_readings()
    df =  df.sort_values( "datetime" )
    print(df["datetime"])

    source.data = dict(
        x = datetime(df["datetime"]),
        TC_1=df[" TC_1"],
        TC_2=df[" TC_2"],
        TC_3=df[" TC_3"],
        TC_4=df[" TC_4"],
        TC_5=df[" TC_5"],
        TC_6=df[" TC_6"],
        TC_7=df[" TC_7"],
        TC_8=df[" TC_8"],
        Fan_L=df["Fan L"],
        Fan_R=df["Fan R"],
        T_L=df["T_L"],
        T_R=df["T_R"],
        T_Out=df["T_Out"],
        RH_L=df["RH_L"],
        RH_R=df["RH_R"],
        RH_Out=df["RH_Out"]
    )

def update_tc_plot(new):
    print("UPDATE TC PLOT")
    for i, line in enumerate(tc_lines):
        if i in tcs.active:
            tc_lines[i].visible=True
        else:
            tc_lines[i].visible=False

def update_fan_plot(new):
    print("UPDATE FAN PLOT")
    for i, line in enumerate(fan_lines):
        if i in fans.active:
            fan_lines[i].visible=True
        else:
            fan_lines[i].visible=False

def update_env_plot(new):
    print("UPDATE ENV PLOT")
    for i, line in enumerate(env_lines):
        if i in env.active:
            env_lines[i].visible=True
        else:
            env_lines[i].visible=False

# Plot

plot_config = dict(tools="pan, xwheel_zoom, box_select, save",
                   x_axis_type ="datetime", plot_width=800)

plt_tc = figure(
        plot_height=400,
        y_axis_label='Thermocouple Temperature, C',
        y_range=[0, 120],
        #x_range=x_range,
        **plot_config
        )

colors = bp.brewer['RdBu'][11]
l_tc1= plt_tc.line("x", "TC_1", source=source, legend = " TC_1", color=colors[0])
l_tc2= plt_tc.line("x", "TC_2", source=source, legend = " TC_2", color=colors[1])
l_tc3= plt_tc.line("x", "TC_3", source=source, legend = " TC_3", color=colors[2])
l_tc4= plt_tc.line("x", "TC_4", source=source, legend = " TC_4",color=colors[3])
l_tc5= plt_tc.line("x", "TC_5", source=source, legend = " TC_5",color=colors[7])
l_tc6= plt_tc.line("x", "TC_6", source=source, legend = " TC_6",color=colors[8])
l_tc7= plt_tc.line("x", "TC_7", source=source, legend = " TC_7",color=colors[9])
l_tc8= plt_tc.line("x", "TC_8", source=source, legend = " TC_8",color=colors[10])

tc_lines = [ l_tc1, l_tc2, l_tc3, l_tc4, l_tc5, l_tc6, l_tc7, l_tc8 ]


#TODO:add shaded region using glyphs and patches
plt_fan = figure(
        plot_height = 150,
        y_axis_label='Fan Current, mA',
        y_range=[-20, 80],
        x_range=plt_tc.x_range,
        **plot_config)

colors = bp.brewer['RdBu'][4]
l_fl= plt_fan.line("x", "Fan_L", source=source, legend = " Left Fan", color=colors[0])
l_fr= plt_fan.line("x", "Fan_R", source=source, legend = " Right Fan", color=colors[3])

#
plt_env = figure(
        plot_height=300,
        y_axis_label='Chamber Temperature/Relative Humidity, C/%',
        y_range=[-0, 100],
        x_range=plt_tc.x_range,
        **plot_config)

rb = bp.brewer['RdBu'][4]
grn = bp.brewer['PiYG'][6]
l_lt= plt_env.line("x", "T_L", source=source, legend="Left Inside T", color=rb[0])
l_rt= plt_env.line("x", "T_R", source=source, legend="Right Inside T", color=rb[3])
l_ot= plt_env.line("x", "T_Out", source=source, legend="Outside T", color=grn[0])
l_lh= plt_env.line("x", "RH_L", source=source, legend="Left Inside RH", color=rb[0], line_dash="4 4")
l_rh= plt_env.line("x", "RH_R", source=source, legend="Right Inside RH", color=rb[3], line_dash="4 4")
l_oh= plt_env.line("x", "RH_Out", source=source, legend="Outside RH", color=grn[0], line_dash="4 4")

env_lines = [ l_lt, l_rt, l_ot, l_lh, l_rh, l_oh  ]

# Widgets

# Buttons
btn_browse = Button(label="Add Data", button_type="success")
btn_browse.on_change('clicks', lambda attr, old, new: clickBrowse())

# Radio Buttons
radio_location = RadioButtonGroup(labels = ["US", "BJ", "SZ"], active=2 )
radio_location.on_click(update_data)
radio_chamber = RadioButtonGroup(labels = ["Left", "Right", "Both"], active=2)
radio_chamber.on_click(update_data)


# Checkbox Buttons
tcs = CheckboxButtonGroup(
        labels=['TC_1', 'TC_2', 'TC_3', 'TC_4', 'TC_5', 'TC_6', 'TC_7', 'TC_8'],
        active=[0, 1, 2, 3, 4, 5, 6, 7])
tcs.on_click(update_tc_plot)


fans= CheckboxButtonGroup(
		labels=['Fan L', 'Fan R'],
		active=[0, 1])
fans.on_click(update_fan_plot)

env = CheckboxButtonGroup(
		labels=['T_L', 'RH_L', 'T_R', 'RH_R', 'T_Out', 'RH_Out'],
		active=[0, 1, 2, 3, 4, 5])
env.on_click(update_env_plot)

controls = [btn_browse, radio_location, radio_chamber, tcs, fans, env]
sizing_mode = 'fixed'  # 'scale_width' also looks nice with this example
inputs = widgetbox(*controls, width=400, sizing_mode=sizing_mode)

desc = Div(text=open(join(dirname(__file__), "description.html")).read(), width=800)

# arrange the graphs to stack on top of each other
sub = column( plt_tc, plt_fan, plt_env )

ll = layout([
    [desc],
    [inputs, sub],
], sizing_mode=sizing_mode)

#update_data()  # initial load of the data
#update_tc_plot()  # initial load of the plots

curdoc().add_root(ll)
curdoc().title ="Hollow Apollo Dashboard"

'''

def plotChamber(side, x_range, y_range, w=600, h=450):
    #Generate Chamber Condition Plots and pass back x range for all plots
    x = df['datetime'].values

    if side == "Left":
        cols = ['T_L', 'RH_L', 'T_Out', 'RH_Out']
    else:
        cols = ['T_R', 'RH_R', 'T_Out', 'RH_Out']

    #calculate dew points
    dp = calculateDewPoint(df[cols[0]].values, df[cols[1]].values)
    dp_o = calculateDewPoint(df[cols[2]].values, df[cols[3]].values)

    p = figure(
        y_axis_label='Chamber Temperature/RH, C/%',
        x_axis_type="datetime",
        **plot_config
    )

    p.line(x, df[cols[0]].values, legend="Inside Temperature", line_color="red")
    p.line(x, df[cols[1]].values, legend="Inside RH", line_color="blue")
    p.line(x, df[cols[2]].values, legend="Outside Temperature", line_dash="4 4", line_width=1, line_color="red")
    p.line(x, df[cols[3]].values, legend="Outside RH", line_dash="4 4", line_width=1, line_color="blue")

    if x_range is None:
        x_range = p.x_range
        y_range = p.y_range
    else:
        p.x_range = x_range
        p.y_range = y_range

    return p, x_range, y_range
'''
