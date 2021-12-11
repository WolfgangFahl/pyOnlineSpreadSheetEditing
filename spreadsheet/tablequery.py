'''
Created on 2021-12-09

@author: wf
'''
from lodstorage.query import Query
from wikibot.wikiuser import WikiUser
from wikibot.wikiclient import WikiClient
from wikibot.smw import SMWClient
#from wikibot.wikipush import WikiPush
from spreadsheet.tableediting import TableEditing

class SmwWikiAccess:
    '''
    Access to Semantic MediaWiki
    '''
    # TODO move to general project
    
    def __init__(self,wikiId:str,showProgress=False,queryDivision=1,debug=False,lenient=True):
        '''
        constructor
        
        
        '''
        self.debug=debug
        self.wikiUser = WikiUser.ofWikiId(wikiId,lenient=lenient)
        self.wikiClient = WikiClient.ofWikiUser(self.wikiUser)
        self.smwClient=SMWClient(self.wikiClient.getSite(),showProgress=showProgress, queryDivision=queryDivision,debug=self.debug)
        # self.wikiPush = WikiPush(fromWikiId=self.wikiUser.wikiId)

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
        self.tableEditing=TableEditing()
        
    def addQuery(self,query:Query):
        '''
        add the query with the given name to my queries
        
        query(Query): the query to add
        '''
        self.queries[query.name]=query
        
    def fetchQueryResults(self):
        '''
        fetch the QueryResults 
        
        '''
        for _name,query in self.queries.items():
            lod=None
            if query.lang=="ask":
                if not hasattr(query, "wikiAccess") or query.wikiAccess is None:
                    raise(f"wikiAccess needs to be configured for Semantic MediaWiki ask query '{query.name}'")
                lod=query.wikiAccess.smwClient.query(query.query)
            elif query.lang.lower()=="sparql":
                if not hasattr(query,"endpoint") or query.endpoint is None:
                    raise(f"endpoint needs to be configured for SPARQL query '{query.name}'")
                lod=query.endpoint.query(query.query)
            if lod is not None:
                self.tableEditing.addLoD(query.name, lod)
        
        
    def fromAskQueries(self,wikiId:str,askQueries:list):
        '''
        initialize me from the given Queries
        '''
        if wikiId not in self.wikiAccessMap:
            self.wikiAccessMap[wikiId] = SmwWikiAccess(wikiId)
        wikiAccess=self.wikiAccessMap[wikiId]
        for askQuery in askQueries:
            name=askQuery["name"]
            ask=askQuery["ask"]
            title=askQuery["title"] if "title" in askQuery else None
            description=askQuery["description"] if "description" in askQuery else None
            query=Query(name=name,query=ask,lang='ask',title=title,description=description,debug=self.debug)
            query.wikiAccess=wikiAccess
            self.addQuery(query)
        self.fetchQueryResults()
            
            