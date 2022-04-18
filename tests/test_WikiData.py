from tests.basetest import BaseTest
from onlinespreadsheet.wikidata import Wikidata
from wikidataintegrator import wdi_core

class TestWikidata(BaseTest):
    '''
    test the Wikidata access
    '''
        
    def testAddItem(self):
        '''
        test the wikidata access
        '''
        # http://learningwikibase.com/data-import/
        # https://github.com/SuLab/scheduled-bots/blob/main/scheduled_bots/wikipathways/bot.py
        wd=Wikidata("https://www.wikidata.org",debug=True)
       
        if not BaseTest.inPublicCI():
            wd.login()
            ist=[]
            #ist.append(wdi_core.WDItem())
            title="Breaking Down Barriers"
            year="1928"
            country="USA"
            countryQid="Q30"
            # instance of
            ist.append(wdi_core.WDItemID(value="Q27968055",prop_nr="P31"))
            # country
            ist.append(wdi_core.WDItemID(value=countryQid,prop_nr="P17"))
            # title
            ist.append(wdi_core.WDMonolingualText(title,prop_nr="P1476"))
            # part of the series
            ist.append(wdi_core.WDItemID(value="Q352581",prop_nr="P179"))
            #ist.append(wdi_core.WDTime(year,prop_nr="P585"))
            label=f"World Day of Prayer {year}"
            description=f"{label}, {title}, {country}"
            wd.addItem(ist,label,description )
        pass