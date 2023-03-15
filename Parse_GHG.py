import zipfile
from datetime import datetime
import configparser
import pandas as pd
from io import TextIOWrapper
from Read_co2app import read_file as Read_co2Cal

class read_GHG():

    def __init__(self,root,name):
        # Sections in the ghg file
        # I think we can ignore the "file description"
        self.metadata_Tags = ['Site','Station','Timing','Instruments']#,'FileDescription'
        
        # Important values in the data file
        self.data_Means = ['CO2 Absorptance', 'H2O Absorptance','CO2 (mmol/m^3)', 'H2O (mmol/m^3)',
        'Block Temperature (C)', 'Total Pressure (kPa)','Box Pressure (kPa)', 'Head Pressure (kPa)', 'Aux 1 - U (m/s)',
        'Aux 2 - V (m/s)', 'Aux 3 - W (m/s)', 'Aux 4 - SOS (m/s)','Cooler Voltage (V)', 'Chopper Cooler Voltage (V)',
        'Dew Point (C)','Cell Temperature (C)', 'Temperature In (C)','Temperature Out (C)', 'Average Signal Strength',
        'Flow Rate (lpm)','Flow Pressure (kPa)', 'Flow Power (V)', 'Flow Drive (%)',
        'CH4 (umol/mol)','CH4 Temperature', 'CH4 Pressure','CH4 Signal Strength']

        # Diagnostic values in the data file
        # Require a bit of work for interpretation
        self.data_Diagnostics = ['Diagnostic Value','Diagnostic Value 2', 'CH4 Diagnostic Value']

        # LI-7700 Status variables we care about
        self.status_Means = ['OPTICSTEMP', 'OPTICSRH']

        self.config = configparser.ConfigParser()
        # Reading the zipped data without extracting saves a bit of time
        with zipfile.ZipFile(root+'\\'+name+'.ghg', 'r') as zip_ref:
            self.config.read_file(TextIOWrapper(zip_ref.open(name+'.metadata'), 'utf-8'))
            self.Parse_Metadata()
            Data = pd.read_csv(zip_ref.open(name+'.data'),delimiter='\t',skiprows=7)
            Data_Summary = self.Summarize_Data(Data,self.data_Means,self.data_Diagnostics)
            Status = pd.read_csv(zip_ref.open(name+'-li7700.status'),delimiter='\t',skiprows=7)
            Status_Summary = self.Summarize_Data(Status,self.status_Means)
            co2app = Read_co2Cal(zip_ref.open('system_config/co2app.conf').read().decode("utf-8"))
            self.co2app_Tags = co2app.Summary.columns

        self.Summary = pd.concat(
            [self.MetaData,Data_Summary,Status_Summary,co2app.Summary],
            axis=0,
            ignore_index=True).set_index('Attribute').T
        # # Get the file timestamp
        TimeStamp = datetime.strptime(name.split('_')[0],'%Y-%m-%dT%H%M%S')
        self.Summary['TimeStamp'] = TimeStamp
        self.Summary['filename'] = name+'.ghg'
        # return(config,Summary)

    
    def Parse_Metadata(self):
       
        self.MetaData = pd.concat(
            [pd.DataFrame(data={'Attribute':self.config[key].keys(),
                                'Value':self.config[key].values()}) for key in self.metadata_Tags],
                                axis=0,
                                ignore_index=True
                            )
        self.MetaData_Tags = self.MetaData['Attribute'].values


    def Summarize_Data(self,Data,means,diagnostics=None):

        Data_Summary = Data[means].mean().to_frame().reset_index()
        Data_Summary.columns=['Attribute','Value']
        if diagnostics is not None:
            Count = pd.DataFrame(data={'Attribute':'N_Samples',
            'Value':Data['Nanoseconds'].count()},index=[0])
            # Temporary implementation that should be expanded if we actually want diagnostics
            # Need to sort out more appropriate approach
            # Storing as an array of unique values may be better?
            data_Diagnostics = Data[diagnostics].mode().T.reset_index()
            if len(data_Diagnostics.columns)>2:
                print(data_Diagnostics)
            data_Diagnostics.columns=['Attribute','Value']
            Data_Summary = pd.concat(
                                [Data_Summary,data_Diagnostics,Count],
                                axis=0,
                                ignore_index=True                            
                                )
        return (Data_Summary)
