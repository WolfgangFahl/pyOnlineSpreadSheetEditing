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
    def __init__(self,lods:dict=None):
        '''
        Constructor
        
        Args:
            lods(dict): a dict of list of dicts that represents the content of a Spreadsheet
        '''
        self.lods=lods
        self.enhanceCallbacks=[] # functions to call for enhancing
         
    def toSpreadSheet(self,spreadSheetType:SpreadSheetType)->SpreadSheet:
        return NONE
    
    def fromSpreadSheet(self,spreadSheet:SpreadSheet):
        pass
    
    def addEnhancer(self,callback):
        self.enhanceCallbacks.append(callback)
    
    def enhance(self):
        for callback in self.enhanceCallbacks:
            callback(self)
        
        
    
        
    
        