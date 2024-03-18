"""
Created on 2021-12-31

@author: wf
"""
import os
from pathlib import Path
from dataclasses import field
from lodstorage.yamlable import lod_storable
from typing import Dict,Optional
from onlinespreadsheet.tablequery import QueryType, TableQuery

@lod_storable
class EditConfig:
    """
    Edit and Query Configuration.

    Attributes:
        name (str): The name of the configuration.
        sourceWikiId (Optional[str]): The source Wiki ID.
        targetWikiId (Optional[str]): The target Wiki ID.
        queries (Dict[str, str]): The queries dictionary.
        format (Optional[str]): The format of the output.
    """
    name:str
    sourceWikiId: Optional[str] = None
    targetWikiId: Optional[str] = None
    queries: Dict[str, str] = field(default_factory=dict)
    format: Optional[str] = None


    def addQuery(self, name: str, query: str):
        self.queries[name] = query
        return self

    def toTableQuery(self) -> TableQuery:
        """
        convert me to a TableQuery

        Returns:
            TableQuery: the table query for my queries
        """
        tq = TableQuery()
        for name, query in self.queries.items():
            queryType = TableQuery.guessQueryType(query)
            if queryType is QueryType.INVALID:
                raise Exception(f"unknown / invalid query Type for query {name}")
            elif queryType is QueryType.ASK:
                tq.addAskQuery(self.sourceWikiId, name, query)
            elif queryType is QueryType.RESTful:
                tq.addRESTfulQuery(name=name, url=query)
            elif queryType is queryType.SPARQL:
                tq.addSparqlQuery(name=name, query=query)
            else:
                raise Exception(f"unimplemented query type {queryType}")
        return tq


@lod_storable
class EditConfigs:
    """
    manager for edit configurations
    """
    editConfigs: Dict[str, EditConfig] = field(default_factory=dict)

    @classmethod
    def get_yaml_path(cls):
        home = str(Path.home())
        path = f"{home}/.ose"
        yamlFileName = "editConfigs.yaml"
        yaml_path = f"{path}/{yamlFileName}"
        return yaml_path

    def add(self, editConfig):
        """
        add a editConfiguration
        """
        self.editConfigs[editConfig.name] = editConfig

    def save(self,yaml_path:str=None):
        if yaml_path is None:
            yaml_path=EditConfigs.get_yaml_path()
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
        self.save_to_yaml_file(yaml_path)
        
    @classmethod
    def load(cls,yaml_path:str=None):
        if yaml_path is None:
            yaml_path=EditConfigs.get_yaml_path()
        edit_configs=cls.load_from_yaml_file(yaml_path)
        return edit_configs
        