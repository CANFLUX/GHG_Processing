import os
# import zipfile
# from datetime import datetime
import configparser
import pandas as pd
import numpy as np
# from io import TextIOWrapper
# from Read_co2app import read_file as Read_co2Cal

class read_GHG():

    def __init__(self,ini_file):
        ini = configparser.ConfigParser()
        ini.read_file(open(ini_file))
        self.metadata_Tags = ini['METADATA']['Sections'].split(',')
        self.data_Means = ini['DATA']['Means'].split(',')
        self.EP_Data_Channels =  ini['DATA']['Channels'].split(',')
        self.data_Diagnostics = ini['DATA']['Diagnostics'].split(',')
        self.status_Means = ini['STATUS']['Means'].split(',')
        self.Calibration = ini['CO2app']['Calibrate'].split(',')
        self.Coefficients = ini['CO2app']['Coef'].split(',')
        self.dpath = ini['highfreq']['path']

    def find_ghg (self,Site):
        self.raw_dir = self.dpath+Site+'\\raw\\'
        self.meta_dir = self.dpath+Site+'\\metadata\\'
        if not os.path.exists(self.meta_dir):
            os.mkdir(meta_dir)

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
        self.files = pd.read_csv(self.meta_dir+'All_Complete_GHG_Files.csv',parse_dates=['timestamp'])
        
        if reset is False:
            self.dynamicMetadata = pd.read_csv(self.meta_dir+'dynamicMetadata.csv')
            self.Channels = pd.read_csv(self.meta_dir+'Channels.csv')
        else:
            self.dynamicMetadata = pd.DataFrame()
            self.Channels = pd.DataFrame()

            
        # df = df.set_index('datetime')
        # return (df)
        # self.FileNames = {
        #     'Metadata':self.meta_dir+'GHGMetaData.csv',
        #     'Channels':self.meta_dir+'EP_Channels.csv',
        #     'Calibration':self.meta_dir+'Calibrate.csv',
        #     'Coefficients':self.meta_dir+'Coefficients.csv',
        # }
        
        # if os.path.isfile(meta_file) and make_new is False:
        #     self.Records = pd.read_csv(self.FileNames['Metadata'],parse_dates=['TimeStamp'])
        #     # Channels = pd.read_csv(channel_file)
        #     # FileNames = Records['filename'].tolist()
        # else:
        #     self.Records = pd.DataFrame()
            # Channels = pd.DataFrame()
            # FileNames = []


        # self.config = configparser.ConfigParser()
        # Reading the zipped data without extracting saves a bit of time
    #     with zipfile.ZipFile(root+'\\'+name+'.ghg', 'r') as zip_ref:
    #         self.config.read_file(TextIOWrapper(zip_ref.open(name+'.metadata'), 'utf-8'))
    #         self.Parse_Metadata()
    #         Data = pd.read_csv(zip_ref.open(name+'.data'),delimiter='\t',skiprows=7)
    #         Data_Summary = self.Summarize_Data(Data,self.data_Means,self.data_Diagnostics)
    #         self.Get_Channels(Data)
    #         Status = pd.read_csv(zip_ref.open(name+'-li7700.status'),delimiter='\t',skiprows=7)
    #         Status_Summary = self.Summarize_Data(Status,self.status_Means)
    #         co2app = Read_co2Cal(zip_ref.open('system_config/co2app.conf').read().decode("utf-8"))
    #         self.co2app_Tags = co2app.Summary.columns

    #     self.Summary = pd.concat(
    #         [self.MetaData,Data_Summary,Status_Summary,co2app.Summary],
    #         axis=0,
    #         ignore_index=True).set_index('Attribute').T
    #     # # Get the file timestamp
    #     TimeStamp = datetime.strptime(name.split('_')[0],'%Y-%m-%dT%H%M%S')
    #     self.Summary['TimeStamp'] = TimeStamp
    #     self.Channels['TimeStamp'] = TimeStamp
    #     self.Channels['filename'] = name+'.ghg'
    #     self.Summary['filename'] = name+'.ghg'
    #     # return(config,Summary)

    
    # def Parse_Metadata(self):
    #     self.MetaData = pd.concat(
    #         [pd.DataFrame(data={'Attribute':self.config[key].keys(),
    #                             'Value':self.config[key].values()}) for key in self.metadata_Tags],
    #                             axis=0,
    #                             ignore_index=True
    #                         )
    #     self.MetaData_Tags = self.MetaData['Attribute'].values


    # def Summarize_Data(self,Data,means,diagnostics=None):
    #     Data_Summary = Data[means].mean().to_frame().reset_index()
    #     Data_Summary.columns=['Attribute','Value']
    #     if diagnostics is not None:
    #         Count = pd.DataFrame(data={'Attribute':'N_Samples',
    #         'Value':Data['Nanoseconds'].count()},index=[0])
    #         # Temporary implementation that should be expanded if we actually want diagnostics
    #         # Need to sort out more appropriate approach
    #         # Storing as an array of unique values may be better?
    #         data_Diagnostics = Data[diagnostics].mode().T.reset_index()
    #         if len(data_Diagnostics.columns)>2:
    #             print(data_Diagnostics)
    #         data_Diagnostics.columns=['Attribute','Value']
    #         Data_Summary = pd.concat(
    #                             [Data_Summary,data_Diagnostics,Count],
    #                             axis=0,
    #                             ignore_index=True                            
    #                             )
    #     return (Data_Summary)
    
    # def Get_Channels(self,Data):
    #     Col_Pos = {}
    #     for v in self.EP_Data_Channels:
    #         Col_Pos[v] = []
    #     for v in self.EP_Data_Channels:
    #         col_num = np.where(Data.columns==v)[0]
    #         if len(col_num) != 1:
    #             if len(col_num)>1:
    #                 print('Warning!  Duplicate Column Headers')
    #                 col_num = col_num[0]
    #             else:
    #                 col_num=0
    #         else:
    #             col_num = col_num[0]
    #         Col_Pos[v].append(col_num)
    #     self.Channels = pd.DataFrame(data=Col_Pos)
