'''
Created on 24.07.2022

@author: wf
'''
from wd.wdsearch import WikidataSearch
from tests.basetest import BaseTest
from pprint import pprint

class TestWikidataSearch(BaseTest):
    '''
    test the WikidataSearch
    '''
    
    def testWikidataSearch(self):
        '''
        test Wikidata Search
        '''
        examples=["academic con","abc","uni"]
        expected=["Q2020153","Q169889","Q3918"]
        wds=WikidataSearch()
        limit=2
        debug=False
        for i,example in enumerate(examples):
            sr=wds.searchOptions(example)
            self.assertTrue(sr is not None)
            if debug:
                print(len(sr))
            for j,record in enumerate(sr):
                qid,qlabel,desc=record
                if j<limit and debug:
                    print(f"{j+1}:{qid} {qlabel}-{desc}")
            self.assertEqual(expected[i],sr[0][0])
            
    def testWikidataProperties(self):
        '''
        test getting wikidata Properties
        '''
        wds=WikidataSearch()
        debug=True
        props=wds.getProperties()
        if debug:
            print(f"found {len(props)} wikidata properties")
        self.assertTrue(len(props)>10000)
                    