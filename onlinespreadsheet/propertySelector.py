'''
Created on 2022-03-21

@author: wf
'''
from fb4.widgets import Widget, Link
from wtforms import SelectField,SubmitField,Field
from flask_wtf import FlaskForm
from onlinespreadsheet.pareto import Pareto
import copy
from markupsafe import Markup

    
class PropertySelector(Widget):
    '''
    select properties
    '''
    def __init__(self):
        self.propertyList=None
        pass

    def prepare(self, propertyList:list,total:int,paretoLevels:list,alignMap:dict={"right":["count","%","pareto"],"center":["select"]}):
        '''
        Constructor
        
        Args:
            propertyList(list): the list of properties to show
            total(int): the total number of records
            paretoLevels(list): the pareto Levels to use
            alignMap(dict): how to align the html table columns
        '''
        self.alignMap=alignMap
        self.propertyList=copy.deepcopy(propertyList)
        self.checkBoxName="selectedWikiDataProperty"
        for prop in self.propertyList:
            propLabel=prop.pop("propLabel")
            url=prop.pop("prop")
            itemId=url.replace("http://www.wikidata.org/entity/","")
            prop["property"]=Link(url,propLabel)
            ratio=int(prop["count"])/total
            level=0
            for pareto in reversed(paretoLevels):
                if pareto.ratioInLevel(ratio):
                    level=pareto.level
            prop["%"]=f'{ratio*100:.1f}'
            prop["pareto"]=level
            prop["select"]=f'<input name="{self.checkBoxName}" id="{itemId}" type="checkbox">'
        pass
                
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
        html=self.render()
        return Markup(html)
        
    def render(self,indent="  "):
        '''
        show a table 
        '''
        if not self.propertyList:
            return ""
        tableRows=""
        for record in self.propertyList:
            tableRows+=self.tableRow(record,indent+"        ")
        tableHead= f"{indent}      <thead>\n"
        tableHead+=f"{indent}        <tr>\n"
        if len(self.propertyList)>0:
            for key in self.propertyList[0].keys():
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
    
class WtPropertySelector(Field):
    widget=PropertySelector()
    
    def __init__(self, *args, **kwargs):
        '''
        constructor
        '''
        super().__init__(*args,**kwargs)
    
    def available(self):
        isAvailable=self.widget.propertyList is not None
        return isAvailable

class PropertySelectorForm(FlaskForm):
    """
    form to select properties
    """                   
    tabularButton=SubmitField("tabular")
    paretoSelect=SelectField('pareto',coerce=int, validate_choice=False)
    wtPropertySelector=WtPropertySelector(label='')
    
    def __init__(self, *args, **kwargs):
        #self.propertySelector=None
        for _name in kwargs.keys():
            pass
        super(FlaskForm, self).__init__(*args, **kwargs)
        
    def setPropertyList(self,propertyList:list,total:int,paretoList:list):
        '''
        prepare the property list based on the given total
        '''
        propertySelector=self.wtPropertySelector.widget
        propertySelector.prepare(propertyList,total,paretoList)
        self.propertyList=propertySelector.propertyList
        #self.lodKeys=list(self.propertyList[0].keys())
        #self.tableHeaders=self.lodKeys
     
    def setParetoChoices(self,topLevel:int=9)->list:
        '''
        set the pareto choices and return the pareto list
        
        Args:
            topLevel(int): the maximum pareto Level
            
        Returns:
            list: a list of pareto choices
        '''
        self.paretoSelect.choices=[]
        paretoLevels=[]
        for level in range(1,topLevel+1):
            pareto=Pareto(level)
            paretoLevels.append(pareto)
            self.paretoSelect.choices.append((pareto.level,pareto.asText(long=True)))
        return paretoLevels