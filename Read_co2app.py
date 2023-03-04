# import os
import re
# import time
# import zipfile
from datetime import datetime
# import configparser
import pandas as pd
import numpy as np
# from io import TextIOWrapper

# from ipywidgets import FloatProgress
# from IPython.display import display

# def Parse_Cal(key,string):
#     # Get Calibration metadata from co2app file
#     Cal_Info = re.search(r''+key+'(.*?)\)\)', string).group(1)
#     Cal_Date = Cal_Info.split('(Date ')[-1].replace(' at ',' ')
#     Cal_Stats = Cal_Info.split('(Date ')[0]
#     Cal_Stats = re.search(r'\((.*)\)', Cal_Stats).group(1).replace(')(',' ')
#     Cal_Stats = pd.DataFrame(np.array([v for v in Cal_Stats.split(' ')]).reshape(-1,2))
#     Cal_Stats = Cal_Stats.rename(columns={0:'Attribute',1:'Value'})
#     Cal_Stats['Attribute']=key+'_'+Cal_Stats['Attribute'].astype(str)
#     try:
#         timestamp = datetime.strptime(Cal_Date,'%b %d %Y %H:%M:%S')
#     except:
#         timestamp = pd.Timestamp('nat')
#         pass
#     Cal_Stats = pd.concat(
#         [Cal_Stats,pd.DataFrame(data={'Attribute':[key+'_Timestamp'],'Value':[timestamp]},index=[0])],
#         axis=0,
#         ignore_index=True
#     )
#     return(Cal_Stats)

# def Parse_Coef(key,string):
#     # Get Calibration coefficients from co2app file
#     Coef_Info = re.search(r''+key+'\((.*?)\)\)', string).group(1).replace(')(',' ')
#     Coef_Info = pd.DataFrame(np.array([v for v in Coef_Info.split(' ')]).reshape(-1,2))
#     Coef_Info = Coef_Info.rename(columns={0:'Attribute',1:'Value'})
#     Coef_Info['Attribute']=key.replace(' ','')+'_'+Coef_Info['Attribute'].astype(str)
#     return(Coef_Info)

# def Read_co2app(co2app):
    # Parse the system_config\co2app.conf file to get calibration settings
    # Only an option for co2/h2o for now
    # Does not appear the ch4 calibration values are saved anywhere?
    # Coef = re.search(r'Coef(.*?)\)\)\)', co2app).group(0)
    # Coef_Keys =  ['CO2 ','H2O ','Pressure ','MaxRef']
    # Coef_Summary = pd.concat(
    #     [Parse_Coef(Val,Coef) for Val in Coef_Keys],
    #     axis=0,
    #     ignore_index=True)#.set_index('Key')

    # Calibrate = re.search(r'Calibrate(.*?)\)\)\)', co2app).group(0)
    # Calibrate_Keys =  ['ZeroCO2','SpanCO2','ZeroH2O','SpanH2O'] # Span2CO2 & Span2H2O not needed
    # Calibrate_Summary = pd.concat(
    #     [Parse_Cal(Val,Calibrate) for Val in Calibrate_Keys],
    #     axis=0,
    #     ignore_index=True)

    # Calibrate_Summary = pd.concat(
    #     [Calibrate_Summary,Coef_Summary],
    #     axis=0)

    # return(Calibrate_Summary)

class read_file():
    # Parse the system_config\co2app.conf file from the 7200 to get calibration settings
    # Only an option for co2/h2o the ch4 calibration values are only saved on the LI-7000

    def __init__(self,co2app_file):
        self.Coef = re.search(r'Coef(.*?)\)\)\)', co2app_file).group(0)
        Coef_Keys =  ['CO2 ','H2O ','Pressure ','MaxRef']
        Coef_Summary = pd.concat(
            [self.Parse_Coef(Val) for Val in Coef_Keys],
            axis=0,
            ignore_index=True)

        self.Calibrate = re.search(r'Calibrate(.*?)\)\)\)', co2app_file).group(0)
        Calibrate_Keys =  ['ZeroCO2','SpanCO2','ZeroH2O','SpanH2O'] # Span2CO2 & Span2H2O not needed
        Calibrate_Summary = pd.concat(
            [self.Parse_Cal(Val) for Val in Calibrate_Keys],
            axis=0,
            ignore_index=True)

        self.Summary = pd.concat(
            [Calibrate_Summary,Coef_Summary],
            axis=0)

        # return(Calibrate_Summary)
    
    def Parse_Coef(self,key):
        # Get Calibration coefficients from co2app file
        Coef_Info = re.search(r''+key+'\((.*?)\)\)', self.Coef).group(1).replace(')(',' ')
        Coef_Info = pd.DataFrame(np.array([v for v in Coef_Info.split(' ')]).reshape(-1,2))
        Coef_Info = Coef_Info.rename(columns={0:'Attribute',1:'Value'})
        Coef_Info['Attribute']=key.replace(' ','')+'_'+Coef_Info['Attribute'].astype(str)
        return(Coef_Info)
    
    
    def Parse_Cal(self,key):
        # Get Calibration metadata from co2app file
        Cal_Info = re.search(r''+key+'(.*?)\)\)', self.Calibrate).group(1)
        Cal_Date = Cal_Info.split('(Date ')[-1].replace(' at ',' ')
        Cal_Stats = Cal_Info.split('(Date ')[0]
        Cal_Stats = re.search(r'\((.*)\)', Cal_Stats).group(1).replace(')(',' ')
        Cal_Stats = pd.DataFrame(np.array([v for v in Cal_Stats.split(' ')]).reshape(-1,2))
        Cal_Stats = Cal_Stats.rename(columns={0:'Attribute',1:'Value'})
        Cal_Stats['Attribute']=key+'_'+Cal_Stats['Attribute'].astype(str)
        try:
            timestamp = datetime.strptime(Cal_Date,'%b %d %Y %H:%M:%S')
        except:
            timestamp = pd.Timestamp('nat')
            pass
        Cal_Stats = pd.concat(
            [Cal_Stats,pd.DataFrame(data={'Attribute':[key+'_Timestamp'],'Value':[timestamp]},index=[0])],
            axis=0,
            ignore_index=True
        )
        return(Cal_Stats)