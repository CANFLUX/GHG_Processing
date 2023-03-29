import os
import zipfile
import linecache
import configparser
import numpy as np
import pandas as pd
from datetime import datetime
from io import TextIOWrapper
from Read_co2app import read_file as Read_co2Cal

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
        self.Calibration = self.ini['CO2app']['Calibrate'].split(',')
        self.Coefficients = self.ini['CO2app']['Coef'].split(',')
        self.dpath = self.ini['highfreq']['path']
        self.Metadata = configparser.ConfigParser()
        self.Headerdata = configparser.ConfigParser()
        self.raw_dir = self.dpath+self.Site+'\\raw\\'+self.Year+'\\'
        self.meta_dir = self.dpath+self.Site+'\\metadata\\'+self.Year+'\\'
        if not os.path.exists(self.meta_dir):
            os.mkdir(self.meta_dir)

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
                        co2app = Read_co2Cal(zip_ref.open(name).read().decode("utf-8"))
                        self.co2app_Tags = co2app.Summary.columns
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
    #         for key in self.ini[tag].keys():
    #             if self.ini[tag][key] == 'True':
    #                 self.dynamicMetadata.loc[self.TimeStamp,key]=self.Metadata[tag][key]
    #     self.header_rows = int(self.Metadata['FileDescription']['header_rows'])
    
    # def Get_Header(self,file):
    #     print(linecache.getline(file, 4))
        # self.header_rows-1

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

