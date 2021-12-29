'''
Created on 2021-12-08

@author: wf
'''
import unittest
from tests.basetest import BaseTest
from spreadsheet.tableediting import TableEditing
from spreadsheet.spreadsheet import SpreadSheet

class TestTableEditing(BaseTest):
    '''
    test TableEditing
    '''

    def setUp(self):
        BaseTest.setUp(self)
        pass


    def fixUrls(self,s:SpreadSheet):
        '''
        fix event homepages in the given onlinespreadsheet
        '''
        events=s.lods["events"]
        for event in events:
            url=event["homepage"]
            if not url.startswith("http"):
                url=f"http://{url}"
                event["homepage"]=url
        pass
        
    def testEnhancer(self):
        '''
        '''
        lods={
            "series": [ {
                "acronym": "IRCDL",
                "title": "Italian Research Conference on Digital Libraries",
                "dblpSeries": "ircdl",
                "wikiDataId": "Q105693562",
                "wikiCfpSeries": 1655
            }
            ],
            "events": [ {
                "acronym":"IRCDL 2014",
                "series": "IRCDL",
                #|Type=Conference
                #|Field=Digital Library
                #|Start date=2014
                "homepage":"www.dis.uniroma1.it/~ircdl13/",
                #|TibKatId=819300411
                #|City=Padova
                #|State=Italy
                #|presence=presence
                }
            ]
        }
        te=TableEditing(lods)
        te.addEnhancer(self.fixUrls)
        te.enhance()
        self.assertTrue(lods["events"][0]["homepage"].startswith("http:"))
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()