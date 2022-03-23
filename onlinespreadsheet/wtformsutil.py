'''
Created on 2022-03-23

@author: wf
'''

class WtFormsUtils(object):
    '''
    helper functions for WtForms
    '''

    def __init__(self):
        '''
        Constructor
        '''
    
    def setInputDisabled(self,inputField,disabled:bool=True):
        '''
        disable the given input
        
        Args:
            inputField(Input): the WTForms input to disable
            disabled(bool): if true set the disabled attribute of the input 
        '''
        if inputField.render_kw is None:
            inputField.render_kw={}
        if disabled:
            inputField.render_kw["disabled"]= "disabled"
        else:
            inputField.render_kw.pop("disabled")
            
    def setRenderKw(self,inputField,key,value):
        '''
        set a render keyword dict entry for the given input field with the given key and value
        
        Args:
            inputField(Input): the field to modify
            key(str): the key to use
            value(str): the value to set
        '''
        if inputField.render_kw is None:
            inputField.render_kw={}
        inputField.render_kw[key]=value
        
    def enableButtonsOnInput(self,buttons:list,inputField):
        '''
        enable the given list of buttons on input in the given inputField
        using a javascript oninput trigger
        
        Args:
            inputField(Input): the inputField to set the input trigger
            buttons(list): the list of buttons to enable
        '''
        script=""
        for button in buttons:
            script+=f"document.getElementById('{button.id}').disabled = false;"
        self.setRenderKw(inputField,"oninput",script)