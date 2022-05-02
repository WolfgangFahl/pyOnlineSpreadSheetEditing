'''
Created on 2022-05-22

@author: wf
'''
import justpy as jp


class MenuButton(jp.QBtn):
    '''
    a menu button
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs,color='primary')
    
class MenuLink(MenuButton):
    '''
    a menu link
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs,type="a",target="_blank")
 

        