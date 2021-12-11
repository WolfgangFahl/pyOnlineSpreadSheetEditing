'''
Created on 09.12.2021

@author: wf
'''
import unittest
from tests.basetest import Basetest
from spreadsheet.tablequery import TableQuery
from spreadsheet.tableediting import SpreadSheetType

class TestTableQuery(Basetest):
    '''
    test table query handling
    '''


    def setUp(self):
        Basetest.setUp(self)
        pass


    def testTableQuery(self):
        '''
        test table query handling
        '''
        askQueries=[{
                "name":"eventseries",
                "ask":"[[SMWCon]]"
            }, {
                "name":"events",
                "ask":"""{{#ask: [[isA::Conference]] 
|?Has Wikidata item ID=wikidataid
|?Has planned finish=endDate
|?Has planned start=startDate
|format=table
}}"""
            }]
        tq=TableQuery()
        tq.fromAskQueries(wikiId="smw",askQueries=askQueries)
        self.assertEqual(2,len(tq.queries))
        # TODO check tables/LoDs
        
    def testSpreadSheetFromTableQuery(self):
        '''
        '''
       
        #te.toSpreadSheet(spreadSheetType=SpreadSheetType.EXCEL)
        # TODO add test
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()