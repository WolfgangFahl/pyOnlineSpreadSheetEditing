'''
Created on 23.03.2022

@author: wf
'''
from fb4.widgets import Widget
from wtforms import Field
from markupsafe import Markup

class TableRowSelector(Widget):    
    '''
    allows selecting rows from tables
    '''
    
    def __init__(self,lod:list=None,checkBoxName:str="selectedRow",alignMap:dict={},indent="    "):
        '''
        constructor
        
        Args:
            lod(list): the list of dicts representing the table
            checkBoxName(str): the name of the checkboxes for row selection
            alignMap(dict): how to align the html table columns - each key represents a possible align e.g. right/left/center 
                and each value a dict key/column name to be aligned that way
            indent(str): the identation to use when rendering
        '''
        self.lod=lod
        self.checkBoxName=checkBoxName
        self.indent=indent
        self.alignMap=alignMap
    
    def orderDicts(self,keys:list):
        '''
        order my dicts with the given keys
        '''
        # @TODO implement
                
    def tableRow(self,record:dict,indent:str)->str:
        '''
        get a html  table row for the given record as 
        
        Args:
            record(dict): the dict
            indent(str): how much to indent the html code
            alignMap(dict): how to align the html table columns
        Returns:
            str: the tr element
        '''
        html=f"{indent}<tr>\n"
        for key in record.keys():
            align=""
            for alignValue in self.alignMap:
                alignList=self.alignMap[alignValue]
                if key in alignList:
                    align=f"align='{alignValue}'"
            html+=f"{indent}  <td {align}>{record[key]}</td>\n"
        html+=f"{indent}</tr>\n"
        return html
    
    def __call__(self, field, **kwargs):
        '''
        see https://wtforms.readthedocs.io
        '''
        html=self.render()
        return Markup(html)
        
    def render(self,indent:str=None):
        '''
        show a table 
        '''
        if not self.lod:
            return ""
        if indent is None:
            indent=self.indent
        tableRows=""
        for record in self.lod:
            tableRows+=self.tableRow(record,indent+"        ")
        tableHead= f"{indent}      <thead>\n"
        tableHead+=f"{indent}        <tr>\n"
        if len(self.lod)>0:
            for key in self.lod[0].keys():
                if key=="select":
                    tableHead+=f"""{indent}          <th scope="col">
{indent}            <button type="button" value="all" class="main" onclick="setAllCheckBoxes('{self.checkBoxName}',true)">all</button>
{indent}            <button type="button" value="non" class="main" onclick="setAllCheckBoxes('{self.checkBoxName}',false)">none</button>"""
                else:
                    tableHead+=f'{indent}          <th scope="col">{key}</th>\n'
        tableHead+=f"{indent}        </tr>\n"
        tableHead+=f"{indent}      </thead>"
        html=f"""{indent}<div class="row">
{indent}  <div class="col-md-12">
{indent}    <table class="table table-bordered">
{tableHead}      
{indent}      <tbody>
{tableRows}
{indent}      </tbody>
{indent}    </table>
{indent}  </div>
{indent}</div>
"""
        return html     
    
class TableRowSelectorField(Field):
    '''
    WtForms compatible Field for a tableRowSelector
    '''
    widget=TableRowSelector()
    
    def __init__(self, *args, **kwargs):
        '''
        constructor
        '''
        super().__init__(*args,**kwargs)
    
    def available(self):
        isAvailable=self.widget.lod is not None
        return isAvailable
    
    def process_formdata(self, valuelist):
        '''
        process the given value list
        
        Override default behavior which would only get the first
        item in the list
        '''
        self.data=valuelist