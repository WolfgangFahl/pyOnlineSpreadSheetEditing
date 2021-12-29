'''
Created on 2021-12-08

@author: wf
'''
from onlinespreadsheet.spreadsheet import SpreadSheet, SpreadSheetType


class TableEditing(object):
    '''
    table Editing
    
    enhancement
    onlinespreadsheet editing call
    validation
    '''
    def __init__(self,lods:dict=None):
        '''
        Constructor
        
        Args:
            lods(dict): a dict of list of dicts that represents the content of a Spreadsheet
        '''
        if lods is None:
            self.lods={}
        else:
            self.lods=lods
        self.enhanceCallbacks=[] # functions to call for enhancing
         
    def toSpreadSheet(self,spreadSheetType:SpreadSheetType,name:str)->SpreadSheet:
        '''
        convert me to the given spreadSheetType
        
        Args:
            spreadSheetType(SpreadSheetType): the type of onlinespreadsheet to create
            name(str): the name of the onlinespreadsheet
        '''
        spreadSheet=SpreadSheet.create(spreadSheetType,name=name)
        spreadSheet.tables=self.lods
        return spreadSheet
    
    def fromSpreadSheet(self, spreadSheet:SpreadSheet):
        pass
    
    def addLoD(self,name,lod):
        '''
        add the given list of dicts with the given name to my lods
        
        Args:
            name(str): the name 
            lod(list): the list of dicts to add
        '''
        self.lods[name]=lod
    
    def addEnhancer(self,callback):
        '''
        add the given enhancer callback to my callbacks
        
        Args:
            callback(func): the callback function to add
        '''
        self.enhanceCallbacks.append(callback)
    
    def enhance(self):
        '''
        enhance/enrich my list of dicts with the set callbacks
        '''
        for callback in self.enhanceCallbacks:
            callback(self)
        
        
    
        
    
        