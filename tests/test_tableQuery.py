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
        self.tq=None
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
    
    def getTableQuery(self):
        if self.tq is not None:
            return self.tq
        wikiId="smw"
        # make sure wiki user is available
        TestTableQuery.getSMW_WikiUser(wikiId)
        self.askQueries=[{
                "name":"eventseries",
                "ask":"[[SMWCon]]|mainlabel='pageTitle'"
            }, {
                "name":"events",
                "ask":"""{{#ask: [[isA::Conference]][[Has Wikidata item ID::+]]|mainlabel='pageTitle'
|?Has Wikidata item ID=wikidataid
|?Has planned finish=endDate
|?Has planned start=startDate
|format=table
}}"""
            }]
        self.tq=TableQuery()
        self.tq.fromAskQueries(wikiId=wikiId,askQueries=self.askQueries)
        return self.tq

    def testTableQuery(self):
        '''
        test table query handling
        '''
        tq=self.getTableQuery()
        self.assertEqual(2,len(tq.queries))
        self.assertFalse(tq.tableEditing is None)
        lods=tq.tableEditing.lods
        self.assertEqual(2,len(lods))
        debug=self.debug
        for askQuery in self.askQueries:
            name=askQuery["name"]
            self.assertTrue(name in lods)
            lod=lods[name]
            if debug:
                print(len(lod))
                print(lod)
            if name=="events":
                self.assertTrue(len(lod)>=18)
        
    def testSpreadSheetFromTableQuery(self):
        '''
        test creating a spreadSheet from a table Query
        '''
        tq=self.getTableQuery()
        name="testSMWCon"
        s=tq.tableEditing.toSpreadSheet(spreadSheetType=SpreadSheetType.EXCEL,name=name)
        self.assertTrue(s is not None)
        debug=self.debug
        if debug:
            print(type(s))
        # TODO add test
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()