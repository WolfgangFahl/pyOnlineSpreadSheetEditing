'''
Created on 13.12.2021

@author: wf
'''
import unittest
from tests.basetest import BaseTest
import warnings
from spreadsheet.webserver import WebServer

class TestWebServer(BaseTest):
    """Test the WebServers RESTful interface"""
    
    def setUp(self) -> None:
        BaseTest.setUp(self)
        self.ws,self.app, self.client=TestWebServer.getApp()
        pass
    
    @staticmethod
    def getApp():
        warnings.simplefilter("ignore", ResourceWarning)
        ws=WebServer()
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
        html=response.data.decode()
        if self.debug:
            print(html)
        return html 

    def testWebServerHome(self):
        '''
        test the home page of the Webserver
        '''
        html=self.getResponse("/")
        self.assertTrue("https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing" in html)
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()