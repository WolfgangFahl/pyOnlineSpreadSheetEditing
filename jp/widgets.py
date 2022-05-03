'''
Created on 2022-05-22

@author: wf
'''
import justpy as jp
import pandas as pd

class LodGrid(jp.AgGrid):
    '''
    agGrid wrapper to be loaded from list of dicts
    '''
    
    def __init__(self, options:dict={},**kwargs):
        '''
        constructor
        
        Args:
            grid_options(dict): AgGrid options
        '''
        # set up the aggrid
        lodGrid_options={
            'enableCellTextSelection':True,
            # enable sorting on all columns by default
            'defaultColDef': {
                'sortable': True
            },
        }
        grid_options = {**options, **lodGrid_options}
        
        super().__init__(options=grid_options,**kwargs)
        
    def load_lod(self,lod:list):
        '''
        load the given list of dicts
        '''
        # https://stackoverflow.com/questions/20638006/convert-list-of-dictionaries-to-a-pandas-dataframe
        df=pd.DataFrame(lod)
        self.load_pandas_frame(df)
        
        
class MenuButton(jp.QBtn):
    '''
    a menu button
    '''
    def __init__(self, **kwargs):
        '''
        constructor
        '''
        super().__init__(**kwargs,color='primary')
    
class MenuLink(MenuButton):
    '''
    a menu link
    '''
    def __init__(self, **kwargs):
        '''
        constructor
        '''
        super().__init__(**kwargs,type="a",target="_blank")
 

        