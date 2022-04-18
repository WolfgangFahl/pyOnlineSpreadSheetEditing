'''
Created on 2022-04-18

@author: wf
'''
import requests
from io import StringIO
import pandas as pd

class GoogleSheet(object):
    '''
    GoogleSheet Handling
    '''

    def __init__(self, url):
        '''
        Constructor
        '''
        self.url=url
        self.dfs={}
        
    def open(self,sheetNames):
        '''
        Args:
            sheets(list): a list of sheetnames
        '''
        self.sheetNames=sheetNames
        for sheetName in sheetNames:
            #csvurl=f"{self.url}/export?format=csv"
            csvurl=f"{self.url}/gviz/tq?tqx=out:csv&sheet={sheetName}"
            response=requests.get(csvurl)
            csvStr=response.content.decode('utf-8')
            self.dfs[sheetName]=pd.read_csv(StringIO(csvStr),keep_default_na=False)
        
    def asListOfDicts(self,sheetName):
        lod=self.dfs[sheetName].to_dict('records') 
        return lod
        
        
        
        
        

        