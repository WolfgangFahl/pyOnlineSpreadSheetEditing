'''
Created on 2021-12-31

@author: wf
'''
from pathlib import Path
import io
import os
from ruamel.yaml import YAML,YAMLObject
from onlinespreadsheet.tablequery import TableQuery, QueryType


class EditConfig(object):
    '''
    Edit and Query Configuration
    '''

    def __init__(self,name:str):
        '''
        Constructor
        
        Args:
            name(str): the name of the edit configuration
        '''
        self.name=name
        self.queries={}

    def addQuery(self, name:str, query:str):
        self.queries[name]=query
        return self
        
    def toTableQuery(self)->TableQuery:
        '''
        convert me to a TableQuery
        
        Returns:
            TableQuery: the table query for my queries
        '''
        tq = TableQuery()
        for name, query in self.queries.items():
            queryType=TableQuery.guessQueryType(query)
            if queryType is QueryType.INVALID:
                raise Exception(f"unknown / invalid query Type for query {name}")
            elif queryType is QueryType.ASK:
                tq.addAskQuery(self.sourceWikiId, name, query)
            elif queryType is QueryType.RESTful:
                tq.addRESTfulQuery(name=name, url=query)
            elif queryType is queryType.SPARQL:
                tq.addSparqlQuery(name=name,query=query)
            else:
                raise Exception(f"unimplemented query type {queryType}")
        return tq

class EditConfigManager(YAMLObject):
    '''
    manager for edit configurations
    '''
    
    def __init__(self,path=None,yamlFileName=None):
        '''
        construct me
        
        Args:
            yamlFile(str): the yamlFile to load and store me from
        '''
        self.editConfigs={}
        if path is None:
            home = str(Path.home())
            path=f"{home}/.ose"
        if not os.path.exists(path):
            os.makedirs(path)
        self.path=path     
        if yamlFileName is None:
            yamlFileName="editConfigs.yaml"
        self.yamlFile=f"{path}/{yamlFileName}" 
    
    def add(self,editConfig):
        '''
        add a editConfiguration
        '''
        self.editConfigs[editConfig.name]=editConfig
    
    def load(self,yamlFile:str=None):
        '''
        load the given yaml file or my set yamlFile if not parameter is given
        
        Args:
            yamlFile(str): the yamlFile to load
        '''
        if yamlFile is None:
            yamlFile=self.yamlFile
        if os.path.isfile(yamlFile):    
            with open(yamlFile, 'r') as stream:
                yaml=YAML(typ='safe',pure=True)
                configs = yaml.load(stream)
            for config in configs.values():
                name=config['name']
                ec=EditConfig(name)
                for key,value in config.items():
                    ec.__setattr__(key, value)
                self.add(ec)
            pass
            
    def save(self,yamlFile:str=None):
        '''
        save me to the given yaml file or my set yamlFile if not parameter is given
        
        Args:
            yamlFile(str): the yamlFile to load
        '''
        if yamlFile is None:
            yamlFile=self.yamlFile
        configs={}
        for editConfig in self.editConfigs.values():
            configs[editConfig.name]=editConfig.__dict__
        with io.open(self.yamlFile, 'w', encoding='utf-8') as stream:
            yaml=YAML(typ='safe',pure=True)
            yaml.dump(configs, stream)
        pass


        
    