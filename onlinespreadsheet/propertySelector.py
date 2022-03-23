'''
Created on 2022-03-21

@author: wf
'''
from onlinespreadsheet.tablerowselector import TableRowSelector,TableRowSelectorField
from fb4.widgets import Link
from wtforms import SelectField,SubmitField
from flask_wtf import FlaskForm
from onlinespreadsheet.pareto import Pareto
import copy
    
class PropertySelection():
    '''
    select properties
    '''
    def __init__(self):
        self.propertyList=None
        pass

    def prepare(self, propertyList:list,total:int,paretoLevels:list,checkBoxName:str):
        '''
        Constructor
        
        Args:
            propertyList(list): the list of properties to show
            total(int): the total number of records
            paretoLevels(list): the pareto Levels to use
        '''
        self.propertyList=copy.deepcopy(propertyList)
        for i,prop in enumerate(self.propertyList):
            # add index as first column
            prop["#"]=i+1
            #prop.move_to_end('#', last=False)
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
            prop["select"]=f'<input name="{checkBoxName}" id="{itemId}" type="checkbox">'
        pass
    

class PropertySelectorForm(FlaskForm):
    """
    form to select properties
    """                   
    tabularButton=SubmitField("tabular")
    paretoSelect=SelectField('pareto',coerce=int, validate_choice=False)
    propertySelectorField=TableRowSelectorField(label='')
    
    def __init__(self, *args, **kwargs):
        #self.propertySelector=None
        for _name in kwargs.keys():
            pass
        super(FlaskForm, self).__init__(*args, **kwargs)
        
    def setPropertyList(self,propertyList:list,total:int,paretoList:list):
        '''
        prepare the property list based on the given list, total and pareto list
        
        
        Args:
            propertyList(list): the list of properties
            total(int): the number of instances in total
            paretoList(list): a list of pareto Levels to be considered
        '''
        propertySelection=PropertySelection()
        checkBoxName="selectedWikiDataProperty"
        propertySelection.prepare(propertyList,total,paretoList,checkBoxName=checkBoxName)
        self.propertyList=propertySelection.propertyList
        propertySelector=self.propertySelectorField.widget
        propertySelector.checkBoxName=checkBoxName
        propertySelector.alignMap={"right":["#","count","%","pareto"],"center":["select"]}
        propertySelector.lod=self.propertyList
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