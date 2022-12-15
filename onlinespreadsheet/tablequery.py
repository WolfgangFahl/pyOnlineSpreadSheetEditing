'''
Created on 2021-12-09

@author: wf
'''
import re
import requests
from typing import Optional
from enum import Enum, auto
from lodstorage.query import Query
from wikibot3rd.wikiuser import WikiUser
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.smw import SMWClient
#from wikibot.wikipush import WikiPush
from spreadsheet.tableediting import TableEditing
from mwclient.errors import APIError
from lodstorage.sparql import SPARQL

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
        
    def login(self):
        self.wikiClient.login()
        
    def query(self,query:str):
        '''
        query with auto-login
        '''
        try:
            qres=self.smwClient.query(query)
        except APIError as apie:
            if "readapidenied" in str(apie):
                # retry with login
                self.login()
                qres=self.smwClient.query(query)
            else:
                raise apie   
        return qres     

class QueryType(Enum):
    """
    Query type
    """
    SQL=auto()
    RESTful=auto()
    ASK=auto()
    SPARQL=auto()
    INVALID=auto()
    
    @staticmethod
    def match(pattern:str,string:str):
        '''
        re match search for the given pattern with ignore case
        '''
        return re.search(pattern=pattern, string=string, flags=re.IGNORECASE)

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
        self.errors=[]
        
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
        for queryName,query in self.queries.items():
            qres=None
            if query.lang=="ask":
                if not hasattr(query, "wikiAccess") or query.wikiAccess is None:
                    raise(f"wikiAccess needs to be configured for Semantic MediaWiki ask query '{query.name}'")
                qres=query.wikiAccess.query(query.query)
                # workaround: undict if dict of dict is returned
                # TODO: check whether this may be fixed upstream
                if isinstance(qres,dict):
                    qres=list(qres.values())
            elif query.lang.lower()=="sparql":
                if not hasattr(query,"endpoint") or query.endpoint is None:
                    raise(f"endpoint needs to be configured for SPARQL query '{query.name}'")
                qres=query.endpoint.queryAsListOfDicts(query.query)
            elif query.lang.lower() == "restful":
                response = requests.request("GET", query.query)
                if response.status_code==200:
                    qres=response.json()
                else:
                    self.errors.append(f"{query.query} failed with status {response.status_code}")
            if qres is not None:
                if isinstance(qres, list):
                    self.tableEditing.addLoD(query.name, qres)
                elif isinstance(qres, dict):
                    for name, lod in qres.items():
                        self.tableEditing.addLoD(f"{queryName}_{name}", lod)
        
    def addAskQuery(self,wikiId:str,name,ask:str,title:str=None,description:str=None):
        '''
        add an ask query for the given wiki
        
        Args:
              wikiId(str): the id of the wiki to add
              name(str): the name of the query to add
              ask(str): the SMW ask query
              title(str): the title of the query
              description(str): the description of the query
        '''
        if wikiId not in self.wikiAccessMap:
            self.wikiAccessMap[wikiId] = SmwWikiAccess(wikiId)
        wikiAccess=self.wikiAccessMap[wikiId]
        query=Query(name=name,query=ask,lang='ask',title=title,description=description,debug=self.debug)
        query.wikiAccess=wikiAccess
        self.addQuery(query)
        
    def fromAskQueries(self,wikiId:str,askQueries:list,withFetch:bool=True):
        '''
        initialize me from the given Queries
        '''
        for askQuery in askQueries:
            name=askQuery["name"]
            ask=askQuery["ask"]
            title=askQuery["title"] if "title" in askQuery else None
            description=askQuery["description"] if "description" in askQuery else None
            self.addAskQuery(wikiId, name, ask, title, description)
        if withFetch:
            self.fetchQueryResults()

    def addRESTfulQuery(self, name:str, url:str, title:str=None, description:str=None):
        """
        add RESTFful query to the queries

        Args:
            url(str): RESTful query URL optionally with parameters
            name(str): name of the query
            title(str): title of the query
            description(str): description of the query
        """
        query = Query(name=name, query=url, lang='restful', title=title, description=description, debug=self.debug)
        self.addQuery(query)
        
    def addSparqlQuery(self,name:str,query:str,endpointUrl:str="https://query.wikidata.org/sparql",title:str=None, description:str=None):
        """
        add SPARQL query to the queries

        Args:
            name(str): name of the query
            query(str): the SPARQL query to execute
            endpointUrl(str): the url of the endpoint to use
            title(str): title of the query
            description(str): description of the query
        """
        query = Query(name=name, query=query, lang='sparql', title=title, description=description, debug=self.debug)
        query.endpoint=SPARQL(endpointUrl)
        self.addQuery(query)
            
    @staticmethod
    def guessQueryType(query:str) -> Optional[QueryType]:
        """
        Tries to guess the query type of the given query

        Args:
            query(str): query

        Returns:
            QueryType
        """
        query=query.lower().strip()
        if query.startswith("http"):
            return QueryType.RESTful
        elif query.startswith("{{#ask:"):
            return QueryType.ASK
        elif (QueryType.match(r"prefix",query) or QueryType.match(r"\s*select\s+\?",query)) or \
            QueryType.match(r"#.*SPARQL",query):
            return QueryType.SPARQL
        elif QueryType.match(r"\s*select",query) and QueryType.match(r"\s*from\s+",query):
            return QueryType.SQL
        else:
            return QueryType.INVALID

