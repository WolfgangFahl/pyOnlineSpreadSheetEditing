'''
Created on 09.12.2021

@author: wf
'''
import unittest
from tests.basetest import BaseTest
from spreadsheet.tablequery import TableQuery
from spreadsheet.tableediting import SpreadSheetType
from wikibot.wikiuser import WikiUser
import os
import getpass

class TestTableQuery(BaseTest):
    '''
    test table query handling
    '''

    @classmethod
    def setUpClass(cls):
        super(TestTableQuery, cls).setUpClass()
        cls.user=getpass.getuser()

    def setUp(self):
        BaseTest.setUp(self)
        
        pass
    
    @classmethod
    def getSMW_WikiUser(cls,wikiId="smw"):
        '''
        get semantic media wiki users for SemanticMediawiki.org and openresearch.org
        
        Args:
            wikiId(str): the wikiId to get the Semantic MediaWiki user for
        '''
        iniFile=WikiUser.iniFilePath(wikiId)
        wikiUser=None
        if not os.path.isfile(iniFile):
            wikiDict=None
            if wikiId=="smwcopy":
                wikiDict={"wikiId": wikiId,"email":"webmaster@bitplan.com","url":"http://smw.bitplan.com","scriptPath":"/","version":"MediaWiki 1.35.0"}
            if wikiId=="smw":
                wikiDict={"wikiId": wikiId,"email":"webmaster@semantic-mediawiki.org","url":"https://www.semantic-mediawiki.org","scriptPath":"/w","version":"MediaWiki 1.31.16"}
            if wikiId=="or":
                wikiDict={"wikiId": wikiId,"email":"webmaster@openresearch.org","url":"https://www.openresearch.org","scriptPath":"/mediawiki/","version":"MediaWiki 1.31.1"}   
            wikiDict["user"]=f"{cls.user}"
            if wikiDict is None:
                raise Exception(f"{iniFile} missing for wikiId {wikiId}")
            else:
                wikiUser=WikiUser.ofDict(wikiDict, lenient=True)
                if BaseTest.inPublicCI():
                    wikiUser.save()
        else: 
            wikiUser=WikiUser.ofWikiId(wikiId,lenient=True)
        return wikiUser

    def testTableQuery(self):
        '''
        test table query handling
        '''
        wikiId="smw"
        # make sure wiki user is available
        TestTableQuery.getSMW_WikiUser(wikiId)
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
        tq.fromAskQueries(wikiId=wikiId,askQueries=askQueries)
        self.assertEqual(2,len(tq.queries))
        self.assertFalse(tq.tableEditing is None)
        lods=tq.tableEditing.lods
        self.assertEqual(2,len(lods))
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