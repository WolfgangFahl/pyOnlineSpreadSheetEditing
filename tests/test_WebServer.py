'''
Created on 13.12.2021

@author: wf
'''
import unittest
from tests.basetest import BaseTest
import warnings
from io import BytesIO
import os
from onlinespreadsheet.editconfig import EditConfig
from onlinespreadsheet.webserver import WebServer
from onlinespreadsheet.spreadsheet import SpreadSheet, ExcelDocument
import re

class TestWebServer(BaseTest):
    """Test the WebServers RESTful interface"""
    
    def setUp(self) -> None:
        BaseTest.setUp(self)
        self.ws,self.app, self.client=TestWebServer.getApp()
        pass
    
    @staticmethod
    def getApp():
        warnings.simplefilter("ignore", ResourceWarning)
        editConfigPath="/tmp/.ose"
        os.makedirs(editConfigPath, exist_ok=True)
        ws=WebServer(withUsers=False,editConfigPath=editConfigPath)
        app=ws.app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        #hostname=socket.getfqdn()
        #app.config['SERVER_NAME'] = "http://"+hostname
        app.config['DEBUG'] = False
        client = app.test_client()
        return ws, app,client
    
    def getResponse(self,query:str):
        '''
        get a response from the app for the given query string
        
        Args:
            query(str): the html query string to fetch the response for
        '''
        response=self.client.get(query)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data is not None)
        return response
    
    def getResponseHtml(self,query:str):
        '''
        get a response from the app for the given query string
        
        Args:
            query(str): the html query string to fetch the response for
        '''
        response=self.getResponse(query)
        html=response.data.decode()
        if self.debug:
            print(html)
        return html 

    def testWebServerHome(self):
        '''
        test the home page of the Webserver
        '''
        html=self.getResponseHtml("/")
        self.assertTrue("https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing" in html)
        pass
    
    def testDownload(self):
        '''
        test downloading 
        '''
        ecm=self.ws.editConfigurationManager
        if not "FCT" in ecm.editConfigs:
            editConfig=EditConfig("FCT")
            ecm.add(editConfig)
        # https://stackoverflow.com/a/26364642/1497139
        response=self.getResponse("/download/FCT")
        d = response.headers['content-disposition']
        fileName = re.findall("filename=(.+)", d)
        buffer=BytesIO(response.data)
        buffer.name=fileName[0]
        spreadSheet=SpreadSheet.load(buffer)
        self.assertTrue(spreadSheet is not None)
        self.assertEqual(type(spreadSheet),ExcelDocument)
        pass
        
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()