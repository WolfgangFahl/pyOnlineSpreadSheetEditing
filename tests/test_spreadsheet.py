'''
Created on 2021-12-29

@author: wf
'''
import unittest
from tests.basetest import BaseTest
from onlinespreadsheet.spreadsheet import SpreadSheetType

class TestSpreadsheet(BaseTest):
    '''
    test the spread sheet handling
    '''

    def setUp(self):
        BaseTest.setUp(self)
        pass


    def testFormat(self):
        '''
        test the different formats
        '''
        for stype in SpreadSheetType:
            print (f"{stype.name}:{stype.getPostfix()}:{stype.getMimeType()}")
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()