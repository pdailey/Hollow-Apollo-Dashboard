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
from bokeh.models import ColumnDataSource, HoverTool, Div, Paragraph, DataRange1d
from bokeh.models.glyphs import Patch
from bokeh.models.widgets import Slider, Select, TextInput, Button, MultiSelect, RadioButtonGroup, CheckboxButtonGroup
from bokeh.io import curdoc
import bokeh.palettes as bp

width_text = 400
width_plots = 800

sql_db = join(dirname(__file__), "database.db")
sql_table = 'the_table'
struct_table = '''( 'index' INTEGER, 'datetime' TEXT, ' TC_4' REAL, ' TC_3' REAL, ' TC_2' REAL, ' TC_1' REAL, ' TC_8' REAL, ' TC_7' REAL, ' TC_6' REAL, ' TC_5' REAL, 'Fan R' REAL, 'Fan L' REAL, 'T_R' REAL, 'RH_R' REAL, 'T_L' REAL, 'RH_L' REAL, 'T_Out' REAL, 'RH_Out' REAL, 'location' TEXT )'''

def createSQLTable(db, table, struct_table, erase_existing=False):
    '''Creates a blank SQL table with specified structure in the
    specified SQL database. Creates and opens a cursor to access the
    database. If the database does not exist, it will be created.
    If erase existing is set to true, an existing table will be written'''
    #TODO:Untested
    conn = sql.connect(db)
    cc = conn.cursor()

    if erase_existing:
        try:
            cc.execute('''DROP TABLE {}'''.format(table))
        except:
            pass


    # Create the table
    # Will throw an error if the table already exists
    cc.execute('''CREATE TABLE {} {}'''.format(table, struct_table))

    # Save the changes and close the connection
    conn.commit()
    conn.close()

#createSQLTable(sql_db, sql_table, struct_table, erase_existing=True)

def updateReadingsFromSQL():
    # Open the connection and create a cursor
    conn = sql.connect(sql_db)
    cc = conn.cursor()

    '''Update the pandas df used for graphing with latest data from the SQL db'''
    query = open(join(dirname(__file__), 'query.sql')).read()
    readings = psql.read_sql(query, conn)

    # Save the changes and close the connection
    conn.commit()
    conn.close()

    readings.fillna(0, inplace=True)  # replace missing values with zero
    return readings


def writeDataframeToSQL(df, sql_db, sql_table):
    conn = sql.connect(sql_db)
    cc = conn.cursor()

    df.to_sql(sql_table, conn, if_exists='append', index=False)

    # Save the changes and close the connection
    conn.commit()
    conn.close()

def browseFiles(filetype=[("CSV", "*.csv")]):
    '''Opens a tk window to browse for files of a specified filetype.
    Returns a list of files with full path'''

    root = tk.Tk()
    root.withdraw()
    root.update()

    # Bring window to front
    root.lift()
    root.focus_force()
    files = filedialog.askopenfilenames(
            parent = root,
            title='Choose files to import',
            filetypes=filetype)
    files = root.tk.splitlist(files)
    root.update()

    print("The following files were selected:")
    for f in files:
        print(f)

    return files


def renameCols(df):
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

# TODO: Untested
def removeDuplicateRows():
    '''Reads a SQL table, searches for duplicate rows and removes them'''
    conn = sql.connect(sql_db)
    cc = conn.cursor()

    query = open(join(dirname(__file__), 'query.sql')).read()
    df = psql.read_sql(query, conn)

    print("Before")
    print(df.describe(percentiles=None))
    print(df.info())
    #prev_len = len(df.index)

    # remove duplace rows
    df.drop_duplicates(subset=["datetime","location"], keep="last", inplace=True)
    #curr_len = len(df.index)
    #diff = prev_len - curr_len

    print("After")
    print(df.describe(percentiles=None))
    print(df.info())
    # replace the SQL table with the new df
    df.to_sql(sql_table, conn, index=False, if_exists='replace')
    #print("\nSQL table had {} rows. \n{} duplicate rows found and removed.".format(prev_len, diff))

    # Save the changes and close the connection
    conn.commit()
    conn.close()

def clickDelete():
    print("Clearing all records from DB...")
    createSQLTable(sql_db, sql_table, struct_table, erase_existing=True)
    print("...Done")

def clickBrowse():
    # Select file(s) using a tk window
    files = browseFiles()

    if len(files)==0:
        print("No files selected.")
        return
    else:
        print("Imported " + str(len(files)) + " data files.")

    # convert each file to a df, append that the SQL DB
    for i, f in enumerate(files):
        print("Processing {}....".format(f))
        df = pd.read_csv(f, index_col=False)
        # convert unix time to datetime
        df['datetime'] = pd.to_datetime(df['datetime'],unit='s')

        df = renameCols(df)
        # use filename to determine test location
        df = addLocationCol(df, f)

        # append data to SQL DB
        print("\tappending data to sql...")
        writeDataframeToSQL(df, sql_db, sql_table)

        # TODO: may be unnecessary...
        print("\tupdatting Readings from SQL...")
        readings = updateReadingsFromSQL()
        print("...Done.")

    # remove duplicates from the SQL table
    removeDuplicateRows()



# Data

# Create Column Data Source that will be used by the plot
source = ColumnDataSource(data=dict(x=[],
                                    TC_1=[], TC_2=[], TC_3=[], TC_4=[],
                                    TC_5=[], TC_6=[], TC_7=[], TC_8=[],
                                    Fan_L=[], Fan_R=[],
                                    T_L=[], T_R=[], T_Out=[],
                                    RH_L=[], RH_R=[], RH_Out=[]))


# Event Handling
def select_readings(readings):
    '''Filters data from the main pandas dataframe based upon the current widget
       states. returns a filtered dataframe.'''

    # Get location that is currently selected
    loc = radio_location.labels[radio_location.active]

    print("SELECTING FROM LOCATION: {}".format(loc))
    # Select data from only one location specified by the button group
    selected = readings[readings.location.str.contains(loc) == True]
    return selected


def select_chamber(new):
    '''On selecting a chamber, all the plots are updated to only show
       information from sensors in selected chamber'''
    chamber = radio_chamber.labels[radio_chamber.active]
    print("SELECTED CHAMBER: {}".format(chamber))

    if chamber == "Left":
        tcs.active = [0, 1, 2, 3]
        fans.active = [0]
        env.active = [0, 2, 3, 5]
    elif chamber == "Right":
        tcs.active = [4, 5, 6, 7]
        fans.active = [1]
        env.active = [1, 2, 4, 5]
    elif chamber == "Both":
        tcs.active = [0, 1, 2, 3, 4, 5, 6, 7]
        fans.active = [0, 1]
        env.active = [0, 1, 2, 3, 4, 5]
    elif chamber == "None":
        tcs.active = []
        fans.active = []
        env.active = []


def update_location(new=None):
    print("UPDATE LOCATION")
    readings = updateReadingsFromSQL()
    df = select_readings(readings)
    df =  df.sort_values( "datetime" )

    source.data = dict(
        x = pd.to_datetime(df["datetime"]),
        # x = datetime(df["datetime"]),
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
readings = updateReadingsFromSQL()

plot_config = dict(tools="pan, xwheel_zoom, box_select, save",
                   x_axis_type ="datetime", plot_width=width_plots)

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

fan_lines = [l_fl, l_fr]

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
# Descriptions
pars = ["Add csv files to the database:",
	"Select test location:",
	"Select Chamber:",
	"Thermocouples:",
	"Fan Currents:",
	"Chamber Temperature and Relative Humidity:",
	"Remove ALL data From the database. Useful if Program is slowing down due to too much data. WARNING! CANNOT BE UNDONE."
       ]

desc =[]
for p in pars:
    desc.append(Paragraph(text=p))


# Buttons
btn_browse = Button(label="Add Data", button_type="success")
btn_browse.on_change('clicks', lambda attr, old, new: clickBrowse())

btn_del = Button(label="Clear Database", button_type="warning")
btn_del.on_change('clicks', lambda attr, old, new: clickDelete())

# Radio Buttons
# Active is intentionally out of range to force user to make selection
radio_location = RadioButtonGroup(labels = ["US", "BJ", "SZ"], active=3 )
radio_location.on_click(update_location)
radio_chamber = RadioButtonGroup(labels = ["Left", "Right", "Both", "None"], active=3)
radio_chamber.on_click(select_chamber)


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
		labels=['T_L', 'T_R', 'T_Out', 'RH_L', 'RH_R', 'RH_Out'],
		active=[0, 1, 2, 3, 4, 5])
env.on_click(update_env_plot)



btns = [btn_browse, radio_location, radio_chamber, tcs, fans, env, btn_del]

# Weave inputs and descriptions
controls = [j for i in zip(desc, btns) for j in i]

sizing_mode = 'fixed'  # 'scale_width' also looks nice with this example
inputs = widgetbox(*controls, width=width_text, sizing_mode=sizing_mode)

desc = Div(text=open(join(dirname(__file__), "static/description.html")).read(), width=width_text)

# arrange the graphs to stack on top of each other
plots = column( plt_tc, plt_fan, plt_env )
text = column( desc, inputs )

ll = layout([
    [text, plots],
], sizing_mode=sizing_mode)

#update_location()  # initial load of the data
#update_tc_plot()  # initial load of the plots

curdoc().add_root(ll)
curdoc().title ="Hollow Apollo Dashboard"
