'''
Created on 24.07.2022

@author: wf
'''
from wd.wdsearch import WikidataSearch
from tests.basetest import BaseTest


class TestWikidataSearch(BaseTest):
    '''
    test the WikidataSearch
    '''
    
    def testWikidataSearch(self):
        '''
        test Wikidata Search
        '''
        wds=WikidataSearch()
        sr=wds.search("abc")
        self.assertTrue(sr is not None)
        debug=True
        if debug:
            print(len(sr))
        print(sr)