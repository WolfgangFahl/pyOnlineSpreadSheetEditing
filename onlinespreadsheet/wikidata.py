'''
Created on 2022-04-18

@author: wf
'''
from pathlib import Path
import json
import os
from wikidataintegrator import wdi_core, wdi_login
from lodstorage.sparql import SPARQL
import pprint

class Wikidata:
    '''
    wikidata access
    
    see http://learningwikibase.com/data-import/
    '''
    
    def __init__(self,baseurl,debug:bool=False):
        self.baseurl=baseurl
        self.debug=debug
        self.apiurl=f"{self.baseurl}/w/api.php"
        pass
    
    def getCredentials(self):
        '''
        get my credentials
        '''
        user=None
        pwd=None
        home = str(Path.home())
        configFilePath=f"{home}/.config/wikibase-cli/config.json"
        if os.path.isfile(configFilePath):
            with open(configFilePath, mode="r") as f:
                wikibaseConfigJson = json.load(f)
                credentials=wikibaseConfigJson["credentials"]
                if not self.baseurl in credentials:
                    raise Exception(f"no credentials available for {self.baseurl}")
                credentialRow=credentials[self.baseurl]
                user=credentialRow["username"]
                pwd=credentialRow["password"]
                pass
        return user,pwd
            
    def login(self):
        user,pwd=self.getCredentials()
        if user is not None:
            self.login = wdi_login.WDLogin(user=user, pwd=pwd, mediawiki_api_url=self.apiurl)
            
    def addItem(self,ist,label,description,lang:str="en",write:bool=True):
        '''
        Args:
            ist(list): item statements
            label(str): the english label
            description(str): the english description
            lang(str): the label language
            write(bool): if True do actually write
        '''
        wbPage=wdi_core.WDItemEngine(data=ist,mediawiki_api_url=self.apiurl)
        wbPage.set_label(label, lang=lang)
        wbPage.set_description(description, lang=lang)
        if self.debug:
            pprint.pprint(wbPage.get_wd_json_representation())
        if write:
            wbPage.write(self.login) # edit_summary=
            
    def getItemByName(self,itemName:str,itemType:str,lang:str="en"):
        '''
        get an item by Name
        
        Args:
            itemName(str): the item to look for
            itemType(str): the type of the item
            lang(str): the language of the itemName
        '''
        itemLabel=f'"{itemName}"@{lang}'
        sparqlQuery="""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX wd: <http://www.wikidata.org/entity/>
    
    SELECT ?item ?itemLabel
    WHERE {
      {
        ?item wdt:P31 wd:%s.
        ?item rdfs:label ?itemLabel.
        ?item wdt:P1813 %s
        FILTER(LANG(?itemLabel)= "%s" )
      } UNION {
        ?item wdt:P31 wd:Q3624078.
        ?item rdfs:label ?itemLabel.
        FILTER(?itemLabel= %s )
      }
    }""" % (itemType,itemLabel,lang,itemLabel)
        endpointUrl="https://query.wikidata.org/sparql"
        sparql=SPARQL(endpointUrl)
        itemRows=sparql.queryAsListOfDicts(sparqlQuery)
        item=None
        if len(itemRows)>0:
            item=itemRows[0]["item"].replace("http://www.wikidata.org/entity/","")
        return item
            
    def addDict(self,row:dict,mapDict:dict,lang:str="en",write:bool=False):
        '''
        add the given row mapping with the given map Dict
        
        Args:
            row(dict): the data row to add
            mapDict(dict): the mapping dictionary to use
            write(bool): if True do actually write
            lang(str): the language for lookups
        '''
        ist=[]
        for propId in mapDict.keys():
            propMap=mapDict[propId]
            column=propMap["Column"]
            colType=propMap["Type"]
            lookup=propMap["Lookup"]
            colValue=None
            if column:
                if column in row:
                    colValue=row[column]
            else:
                colValue=propMap["Value"]
            if colValue:
                if lookup:
                    colValue=self.getItemByName(colValue, lookup, lang)
            if colValue:
                if colType=="year":
                    yearString=f"+{colValue}-01-01T00:00:00Z"
                    ist.append(wdi_core.WDTime(yearString,prop_nr=propId,precision=9))
                elif colType=="text":
                    ist.append(wdi_core.WDMonolingualText(value=colValue,prop_nr=propId))
                else:
                    ist.append(wdi_core.WDItemID(value=colValue,prop_nr=propId))
        label=row["label"]
        description=row["description"]
        self.addItem(ist,label,description,write=write)
        
        
            
                