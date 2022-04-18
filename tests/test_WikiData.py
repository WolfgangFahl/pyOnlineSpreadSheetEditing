from tests.basetest import BaseTest
from onlinespreadsheet.wikidata import Wikidata
from sl.googlesheet import GoogleSheet
from lodstorage.lod import LOD

class TestWikidata(BaseTest):
    '''
    test the Wikidata access
    '''
    
    def testItemLookup(self):
        '''
        lookup items
        '''
        debug=True
        wd=Wikidata("https://www.wikidata.org",debug=True)
        country=wd.getItemByName("USA","Q3624078")
        if debug:
            print(country)
        self.assertEqual("Q30",country)
        ecir=wd.getItemByName("ECIR","Q47258130")
        if debug:
            print(ecir)
        self.assertEqual("Q5412436",ecir)
        
    def testAddItem(self):
        '''
        test the wikidata access
        '''
        # http://learningwikibase.com/data-import/
        # https://github.com/SuLab/scheduled-bots/blob/main/scheduled_bots/wikipathways/bot.py
        wd=Wikidata("https://www.wikidata.org",debug=True)
        url="https://docs.google.com/spreadsheets/d/1AZ4tji1NDuPZ0gwsAxOADEQ9jz_67yRao2QcCaJQjmk"
        self.gs=GoogleSheet(url)   
        spreadSheetNames=["WorldPrayerDays","Wikidata"] 
        self.gs.open(spreadSheetNames)  
        rows=self.gs.asListOfDicts("WorldPrayerDays")
        mapRows=self.gs.asListOfDicts("Wikidata")
        mapDict,_dup=LOD.getLookup(mapRows, "PropertyId", withDuplicates=False)
        # 1934
        row=rows[7]
        print(row)
        print(mapDict)
       
        write=not BaseTest.inPublicCI()
        write=False
        if write:
            wd.login()
        wd.addDict(row, mapDict,write=write)
        pass