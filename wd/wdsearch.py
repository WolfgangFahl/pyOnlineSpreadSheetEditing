'''
Created on 24.07.2022

@author: wf
'''
import html
import urllib.request, json

class WikidataSearch(object):
    '''
    Wikidata Search
    '''

    def __init__(self,language='en',timeout=2.0):
        '''
        Constructor
        
        Args:
            language(str): the language to use e.g. en/fr
            timeout(float): maximum time to wait for result
        '''
        self.language=language
        self.timeout=timeout
        
    def search(self,searchFor:str,limit=9):
        '''
        
        Args:
            searchFor(str): the string to search for
        '''
        try:
            apiurl=f"https://www.wikidata.org/w/api.php?action=wbsearchentities&language={self.language}&format=json&limit={limit}&search="
            apisearch=apiurl+html.escape(searchFor)
            with urllib.request.urlopen(apisearch,timeout=self.timeout) as url:
                searchResult = json.loads(url.read().decode())
            return searchResult["search"]
        except Exception as _error:
            return None