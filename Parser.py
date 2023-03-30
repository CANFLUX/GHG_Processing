import os
import zipfile
import re
import configparser
import numpy as np
import pandas as pd
from datetime import datetime
from io import TextIOWrapper
# from Read_co2app import read_file as Read_co2Cal

class read_GHG():

    def __init__(self,ini_file,Site,Year):
        self.Year = str(Year)
        self.Site = Site
        self.ini = configparser.ConfigParser()
        self.ini.read_file(open(ini_file))
        self.data_Means = self.ini['DATA']['Means'].split(',')
        self.EP_Data_Channels =  self.ini['DATA']['Channels'].split(',')
        self.data_Diagnostics = self.ini['DATA']['Diagnostics'].split(',')
        self.status_Means = self.ini['STATUS']['Means'].split(',')
        # self.Calibration = self.ini['CO2APP']['Calibrate'].split(',')
        # self.Coefficients = self.ini['CO2APP']['Coef'].split(',')
        self.dpath = self.ini['highfreq']['path']
        self.Metadata = configparser.ConfigParser()
        self.Headerdata = configparser.ConfigParser()
        self.raw_dir = self.dpath+self.Site+'\\raw\\'+self.Year+'\\'
        self.meta_dir = self.dpath+self.Site+'\\metadata\\'+self.Year+'\\'
        if not os.path.exists(self.meta_dir):
            os.mkdir(self.meta_dir)
        self.read_co2app = read_LI_Config(ini_file,format='co2app')

    def find_ghg (self):
        # Find every .ghg file in the raw data folder
        all_files = []
        for (root, dir, files) in os.walk(self.raw_dir):
            if root != self.raw_dir:
                for file in files:
                    name, tag = file.split('.')
                    # .ghg files are located at the end of each directory tree
                    # Avoids reading any that might be misplaced elsewhere
                    if tag == 'ghg' and len(dir)==0:
                        # Use the filename as the index
                        all_files.append(name)

        df = pd.DataFrame(data={
                'filename':all_files,
                })
        
        # Get the timestamp from the filename
        df['timestamp'] = pd.to_datetime(df['filename'].str.split('_').str[0])
        df = df.set_index('timestamp')

        # Exclude any files that fall off half hourly intervals ie. maintenance
        df.loc[((df.index.minute!=30)&(df.index.minute!=0)),'filename'] = np.nan
        # Resample to 30 min intervals - missing filenames will be null
        df = df.resample('30T').first()
        # Save the list of files
        df.to_csv(self.meta_dir+'All_Complete_GHG_Files.csv')

    def Read(self,reset=False):
        self.files = pd.read_csv(self.meta_dir+'All_Complete_GHG_Files.csv',
                                 parse_dates=['timestamp'],
                                 index_col='timestamp'
                                 )

        # Sort so that newest files get processed first
        self.files = self.files.sort_index(ascending=False)
        
        if reset is False and os.path.isfile(self.meta_dir+'dynamicMetadata.csv'):
            self.dataRecords = pd.read_csv(self.meta_dir+'Records.csv',
                                 parse_dates=['timestamp'],
                                 index_col='timestamp')
            self.dynamicMetadata = pd.read_csv(self.meta_dir+'dynamicMetadata.csv',
                                 parse_dates=['timestamp'],
                                 index_col='timestamp')
            self.Headers = pd.read_csv(self.meta_dir+'Headers.csv',
                                 parse_dates=['timestamp'],
                                 index_col='timestamp')
            self.Channels = pd.read_csv(self.meta_dir+'Channels.csv',
                                 parse_dates=['timestamp'],
                                 index_col='timestamp')
        else:
            self.dataRecords = pd.DataFrame()
            self.dataRecords.index.name='timestamp'
            self.dynamicMetadata = pd.DataFrame()
            self.dynamicMetadata.index.name='timestamp'
            self.Headers = pd.DataFrame()
            self.Headers.index.name='timestamp'
            self.Channels = pd.DataFrame()
            self.Channels.index.name='timestamp'

        i = 0
        for ts,row in self.files.dropna().iterrows():
            name = row['filename']
            self.ghg = self.raw_dir+'\\'+"{:02d}".format(ts.month)+'\\'+name+'.ghg'
            self.TimeStamp = datetime.strptime(name.split('_')[0],'%Y-%m-%dT%H%M%S')
            
            if i <= 50:
                if self.TimeStamp not in self.dataRecords.index:
                    self.extract_ghg()
                    i += 1
            if i % 25 == 0 and i > 0:
                self.dataRecords.to_csv(self.meta_dir+'Records.csv')
                self.dynamicMetadata.to_csv(self.meta_dir+'dynamicMetadata.csv')
                self.Headers.to_csv(self.meta_dir+'Headers.csv')
                self.Channels.to_csv(self.meta_dir+'Channels.csv')
              
    def extract_ghg(self):
        with zipfile.ZipFile(self.ghg, 'r') as zip_ref:
            files = zip_ref.namelist()
            # Read metadata first
            md = [i for i in files if 'metadata' in i]
            if len(md) == 1:
                self.Parse_Metadata(TextIOWrapper(zip_ref.open(md[0]), 'utf-8'))
                files.remove(md[0])
                self.head = ''
                for name in files:
                    if name.split('.')[-1] == 'data':
                        with zip_ref.open(name) as input_file:
                            self.head = self.head + '[DATA]\n'+''.join(next(input_file).decode('utf-8') for _ in range(self.header_rows-1))+'\n'
                        Data = pd.read_csv(
                            zip_ref.open(name),
                            delimiter='\t',
                            skiprows=self.header_rows-1)
                        self.dataRecords.loc[self.TimeStamp,self.data_Means] = Data[self.data_Means].mean()
                        self.dataRecords.loc[self.TimeStamp,'n'] = Data[self.data_Diagnostics].shape[0]
                        # Temporary implementation, should do something better if we need these
                        self.dataRecords.loc[self.TimeStamp,self.data_Diagnostics] = Data[self.data_Diagnostics].max()
                        self.Get_Channels(Data.columns)
                    elif name.split('.')[-1] == 'status':
                        with zip_ref.open(name) as input_file:
                            self.head = self.head + '[STATUS]\n'+''.join(next(input_file).decode('utf-8') for _ in range(self.header_rows-1))+'\n'
                        Status = pd.read_csv(
                            zip_ref.open(name),
                            delimiter='\t',
                            skiprows=self.header_rows-1)
                        self.dataRecords.loc[self.TimeStamp,self.status_Means] = Status[self.status_Means].mean()
                    elif name.split('.')[-1] == 'conf':
                        # co2app = Read_co2Cal(zip_ref.open(name).read().decode("utf-8"))
                        # self.co2app = read_LI_Config(zip_ref.open(name).read().decode("utf-8"))
                        self.read_co2app.parse(zip_ref.open(name).read().decode("utf-8"))
                        # self.co2app_Tags = co2app.Summary.columns
                self.Parse_Headerdata()
            else:
                print('Warning - invalid metadata - skipping file')

    def Parse_Metadata(self,meta_file):
        self.Metadata.read_file(meta_file)
        for tag in self.ini['METADATA']['read_section'].split(','):
            for key in self.ini[tag].keys():
                if self.ini[tag][key] == 'True':
                    self.dynamicMetadata.loc[self.TimeStamp,key]=self.Metadata[tag][key]
        self.header_rows = int(self.Metadata['FileDescription']['header_rows'])

    def Parse_Headerdata(self):
        self.Headerdata.read_string(self.head)

        for tag in self.Headerdata.keys():
            if tag !='DEFAULT':
                model = self.Headerdata[tag]['Model'].split(' ')[0]
                for key in self.ini[tag]['Headers'].split(','):
                    if key != 'Timezone':
                        self.Headers.loc[self.TimeStamp,key+'_'+model] = self.Headerdata[tag][key]
                    else:
                        self.Headers.loc[self.TimeStamp,key] = self.Headerdata[tag][key]

    def Get_Channels(self,cols):
        # Col_Pos = {}
        for v in self.EP_Data_Channels:
            col_num = np.where(cols==v)[0]
            if len(col_num)==0:
                channel = None
            elif len(col_num)>1:
                print('Warning!  Duplicate Column Headers')
                channel = int(col_num[0])
            else:
                channel = int(col_num[0])
            self.Channels.loc[self.TimeStamp,v] = channel


class read_LI_Config():
    # Parse the system_config\co2app.conf file from the 7200 to get calibration settings
    # Only an option for co2/h2o the ch4 calibration values are only saved on the LI-7000
    def __init__(self,ini_file,format='L7X'):
        ini = configparser.ConfigParser()
        ini.read_file(open(ini_file))
        if format == 'L7X':
            self.ini=ini['L7X']
        else:   
            self.ini=ini['CO2APP']


    def parse(self,file):
        self.parsedConfig = {}
        for key in self.ini.keys():
            splits = self.ini[key].split(',')
            self.makeConfig(file.split(splits[0])[-1].split(splits[1])[0])
            self.parsedConfig[key]=self.config

    def makeConfig(self,string,pnt=False):
        all = re.findall(r'\((.+?)\)',string)
        formatted =''
        for i,v in enumerate(all):
            
            if '(' in v:
                tags = v.split('(')[:-1]
                for t in tags:
                    formatted += '\n['+t.replace(' ','')+']\n'
                formatted += v.split('(')[-1].replace(' ','=',1)
            else:
                if ' ' not in v:
                    formatted += '\n'+v+'='
                else:
                    formatted += '\n'+v.replace(' ','=',1)
        if pnt == True:
            print(formatted)
        self.config = configparser.ConfigParser()
        self.config.read_string(formatted)

    # def __init__(self,co2app_file):
    #     self.Coef = re.search(r'Coef(.*?)\)\)\)', co2app_file).group(0)
    #     Coef_Keys =  ['CO2 ','H2O ','Pressure ','MaxRef']
    #     Coef_Summary = pd.concat(
    #         [self.Parse_Coef(Val) for Val in Coef_Keys],
    #         axis=0,
    #         ignore_index=True)

    #     self.Calibrate = re.search(r'Calibrate(.*?)\)\)\)', co2app_file).group(0)
    #     Calibrate_Keys =  ['ZeroCO2','SpanCO2','ZeroH2O','SpanH2O'] # Span2CO2 & Span2H2O not needed
    #     Calibrate_Summary = pd.concat(
    #         [self.Parse_Cal(Val) for Val in Calibrate_Keys],
    #         axis=0,
    #         ignore_index=True)

    #     self.Summary = pd.concat(
    #         [Calibrate_Summary,Coef_Summary],
    #         axis=0)
    
    # def Parse_Coef(self,key):
    #     # Get Calibration coefficients from co2app file
    #     Coef_Info = re.search(r''+key+'\((.*?)\)\)', self.Coef).group(1).replace(')(',' ')
    #     Coef_Info = pd.DataFrame(np.array([v for v in Coef_Info.split(' ')]).reshape(-1,2))
    #     Coef_Info = Coef_Info.rename(columns={0:'Attribute',1:'Value'})
    #     Coef_Info['Attribute']=key.replace(' ','')+'_'+Coef_Info['Attribute'].astype(str)
    #     return(Coef_Info)
        
    # def Parse_Cal(self,key):
    #     # Get Calibration metadata from co2app file
    #     Cal_Info = re.search(r''+key+'(.*?)\)\)', self.Calibrate).group(1)
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