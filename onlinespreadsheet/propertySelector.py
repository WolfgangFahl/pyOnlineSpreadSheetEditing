'''
Created on 2022-03-21

@author: wf
'''
from fb4.widgets import Widget, Link
from wtforms import SelectField,SubmitField
from flask_wtf import FlaskForm
from onlinespreadsheet.pareto import Pareto
import copy

class PropertySelectorForm(FlaskForm):
    """
    form to select properties
    """                   
    paretoSelect=SelectField('pareto',coerce=int, validate_choice=False)
    tabularButton=SubmitField("tabular")
    
    def __init__(self, *args, **kwargs):
        self.propertySelector=None
        for _name in kwargs.keys():
            pass
        super(FlaskForm, self).__init__(*args, **kwargs)
        
    def setPropertyList(self,propertyList:list,total:int,paretoList:list):
        '''
        prepare the property list based on the given total
        '''
        self.propertySelector=PropertySelector(propertyList,total,paretoList)
        self.propertyList=self.propertySelector.propertyList
        self.lodKeys=list(self.propertyList[0].keys())
        self.tableHeaders=self.lodKeys
     
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

class PropertySelector(Widget):
    '''
    select properties
    '''

    def __init__(self, propertyList:list,total:int,paretoLevels:list):
        '''
        Constructor
        
        Args:
            propertyList(list): the list of properties to show
        '''
        self.propertyList=copy.deepcopy(propertyList)
        for prop in self.propertyList:
            propLabel=prop.pop("propLabel")
            url=prop.pop("prop")
            prop["property"]=Link(url,propLabel)
            ratio=int(prop["count"])/total
            level=0
            for pareto in reversed(paretoLevels):
                if pareto.ratioInLevel(ratio):
                    level=pareto.level
            prop["%"]=f'{ratio*100:.1f}'
            prop["pareto"]=level
        
        
    def tableRow(self,property):
        html="""<tr>
</tr>"""
        return html

        
    def render(self):
        '''
        show a table 
        '''
        tableRows=""
        for record in self.propertyList:
            tableRows+=self.tableRow(record)
        html=f"""<div class="row">
    <div class="col-12">
      <table class="table table-bordered">
        <thead>
          <tr>
            <th scope="col">Property</th>
            <th scope="col">Count</th>
          </tr>
        <thead>
        <tbody>
{tableRows}
        </tbody>
      </table>
    </div>
</div>"""
        return html          
        