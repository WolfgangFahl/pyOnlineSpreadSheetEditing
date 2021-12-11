'''
Created on 2021-12-08

@author: wf
'''
from spreadsheet.spreadsheet import SpreadSheet, SpreadSheetType
from pickle import NONE

class TableEditing(object):
    '''
    table Editing
    
    enhancement
    spreadsheet editing call
    validation
    '''
    def __init__(self,lods:dict={}):
        '''
        Constructor
        
        Args:
            lods(dict): a dict of list of dicts that represents the content of a Spreadsheet
        '''
        self.lods=lods
        self.enhanceCallbacks=[] # functions to call for enhancing
         
    def toSpreadSheet(self,spreadSheetType:SpreadSheetType)->SpreadSheet:
        '''
        convert me to the given spreadSheetType
        '''
        return NONE
    
    def fromSpreadSheet(self,spreadSheet:SpreadSheet):
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
        
        
    
        
    
        