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
        
    def open(self):
        csvurl=f"{self.url}/export?format=csv"
        response=requests.get(csvurl)
        csvStr=response.content.decode('utf-8')
        self.df=pd.read_csv(StringIO(csvStr))
        
    def asListOfDicts(self):
        return self.df.to_dict('records') 
        
        
        
        
        

        