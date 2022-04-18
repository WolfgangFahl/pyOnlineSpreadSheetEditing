from tests.basetest import BaseTest
from onlinespreadsheet.wikidata import Wikidata
from sl.googlesheet import GoogleSheet
from wikidataintegrator import wdi_core
from lodstorage.sparql import SPARQL

class TestWikidata(BaseTest):
    '''
    test the Wikidata access
    '''
    
    def getCountry(self,countryName:str,lang:str="en"):
        countryLabel=f'"{countryName}"@{lang}'
        sparqlQuery="""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>

SELECT ?country ?countryLabel
WHERE {
  {
    ?country wdt:P31 wd:Q3624078.
    ?country rdfs:label ?countryLabel.
    ?country wdt:P1813 %s
    FILTER(LANG(?countryLabel)= "en" )
  } UNION {
    ?country wdt:P31 wd:Q3624078.
    ?country rdfs:label ?countryLabel.
    FILTER(?countryLabel= %s )
  }
}""" % (countryLabel,countryLabel)
        endpointUrl="https://query.wikidata.org/sparql"
        sparql=SPARQL(endpointUrl)
        countryRows=sparql.queryAsListOfDicts(sparqlQuery)
        country=None
        if len(countryRows)>0:
            country=countryRows[0]["country"].replace("http://www.wikidata.org/entity/","")
        return country
    
    def testCountryLookup(self):
        '''
        lookup countries
        '''
        country=self.getCountry("Korea")
        print(country)
        
    def testAddItem(self):
        '''
        test the wikidata access
        '''
        # http://learningwikibase.com/data-import/
        # https://github.com/SuLab/scheduled-bots/blob/main/scheduled_bots/wikipathways/bot.py
        wd=Wikidata("https://www.wikidata.org",debug=True)
        url="https://docs.google.com/spreadsheets/d/1AZ4tji1NDuPZ0gwsAxOADEQ9jz_67yRao2QcCaJQjmk"
        self.gs=GoogleSheet(url)   
        spreadSheetName="WorldPrayerDays" 
        self.gs.open([spreadSheetName])  
        rows=self.gs.asListOfDicts(spreadSheetName)
        # 1933
        row=rows[6]
        print(row)

        write=not BaseTest.inPublicCI()
        #write=False
        if write:
            wd.login()
        ist=[]
        #ist.append(wdi_core.WDItem())
        title=row["Theme"]
        year=row["Year"]
        country=row["MainWriterCountry"]
        countryQid=self.getCountry(country)
        # instance of
        ist.append(wdi_core.WDItemID(value="Q27968055",prop_nr="P31"))
        # country 
        if countryQid is not None:
            ist.append(wdi_core.WDItemID(value=countryQid,prop_nr="P17"))
        # title
        ist.append(wdi_core.WDMonolingualText(title,prop_nr="P1476"))
        # part of the series
        ist.append(wdi_core.WDItemID(value="Q352581",prop_nr="P179"))
        yearString=f"+{year}-01-01T00:00:00Z"
        ist.append(wdi_core.WDTime(yearString,prop_nr="P585",precision=9))
        label=row["label"]
        description=row["description"]
        wd.addItem(ist,label,description,write=write)
        pass