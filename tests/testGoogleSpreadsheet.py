'''
Created on 2022-04-18

@author: wf
'''
from sl.googlesheet import GoogleSheet
from tests.basetest import BaseTest

class TestGoogleSpreadsheet(BaseTest):


    def testWorldPrayerDays(self):
        url="https://docs.google.com/spreadsheets/d/1AZ4tji1NDuPZ0gwsAxOADEQ9jz_67yRao2QcCaJQjmk"
        gs=GoogleSheet(url)
        gs.open()
        lod=gs.asListOfDicts()
        debug=self.debug
        debug=True
        if debug:
            print(lod)
        self.assertTrue(len(lod)>90)
      
        pass


