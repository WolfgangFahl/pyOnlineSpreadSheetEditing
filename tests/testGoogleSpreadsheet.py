'''
Created on 2022-04-18

@author: wf
'''
from sl.googlesheet import GoogleSheet
from tests.basetest import BaseTest

class TestGoogleSpreadsheet(BaseTest):
    '''
    test the google spreadsheet access
    '''

    def testWorldPrayerDays(self):
        '''
        test the world prayer days table
        '''
        url="https://docs.google.com/spreadsheets/d/1AZ4tji1NDuPZ0gwsAxOADEQ9jz_67yRao2QcCaJQjmk"
        gs=GoogleSheet(url)
        sheetNames=["WorldPrayerDays","Wikidata"]
        gs.open(sheetNames)
        expected={"WorldPrayerDays":90,"Wikidata":3}
        for sheetName in sheetNames:
            lod=gs.asListOfDicts(sheetName)
            debug=self.debug
            debug=True
            if debug:
                print(lod)
            self.assertTrue(len(lod)>=expected[sheetName])
      
        pass


