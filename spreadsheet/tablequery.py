'''
Created on 2021-12-09

@author: wf
'''
from lodstorage.query import Query
from wikibot.wikiuser import WikiUser
from wikibot.wikiclient import WikiClient
from wikibot.wikipush import WikiPush

class WikiAccess:
    '''
    '''
    # TODO move to general project
    
    def __init__(self,wikiId:str):
        '''
        '''
        self.wikiUser = WikiUser.ofWikiId(wikiId)
        self.wikiClient = WikiClient.ofWikiUser(self.wikiUser)
        self.wikiPush = WikiPush(fromWikiId=self.wikiUser.wikiId)

class TableQuery(object):
    '''
    prepare a Spreadsheet editing 
    '''

    def __init__(self,debug=False):
        '''
        Constructor
        '''
        self.debug=debug
        self.wikiAccessMap={}
        self.queries={}
        
    def fromAskQueries(self,wikiId:str,askQueries:list):
        '''
        initialize me from the given Queries
        '''
        if wikiId not in self.wikiAccessMap:
            self.wikiAccessMap[wikiId] = WikiAccess(wikiId)
        wikiAccess=self.wikiAccessMap[wikiId]
        for askQuery in askQueries:
            name=askQuery["name"]
            ask=askQuery["ask"]
            title=askQuery["title"] if "title" in askQuery else None
            description=askQuery["description"] if "description" in askQuery else None
            query=Query(name=name,query=ask,lang='ask',title=title,description=description,debug=self.debug)
            self.queries[name]=query
            