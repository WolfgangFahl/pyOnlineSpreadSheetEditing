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
        
    def searchOptions(self,searchFor:str,limit:int=9)->list:
        '''
        search and yield a list of qid,itemLabel description tuples
        
        Args:
            searchFor(str): the string to search for
            limit(int): the maximum amount of results to search for
        '''
        srlist=self.search(searchFor, limit)
        if srlist is None:
            return
        for sr in srlist:
            qid=sr["id"]
            itemLabel=sr["label"]
            desc=""
            if "display" in sr:
                display=sr["display"]
                if "description" in display:
                    desc=display["description"]["value"]
            yield qid,itemLabel,desc

    def search(self,searchFor:str,limit:int=9):
        '''
        
        Args:
            searchFor(str): the string to search for
            limit(int): the maximum amount of results to search for
        '''
        try:
            apiurl=f"https://www.wikidata.org/w/api.php?action=wbsearchentities&language={self.language}&format=json&limit={limit}&search="
            apisearch=apiurl+html.escape(searchFor)
            with urllib.request.urlopen(apisearch,timeout=self.timeout) as url:
                searchResult = json.loads(url.read().decode())
            return searchResult["search"]
        except Exception as _error:
            return None