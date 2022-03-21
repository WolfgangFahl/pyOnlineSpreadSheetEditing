'''
Created on 2022-03-21

@author: wf
'''
from fb4.widgets import Widget
from wtforms import SelectField,SubmitField
from flask_wtf import FlaskForm
from onlinespreadsheet.pareto import Pareto

class PropertySelectorForm(FlaskForm):
    """
    form to select properties
    """                   
    paretoSelect=SelectField('pareto')
    tabularButton=SubmitField("tabular")
    
    def __init__(self, *args, **kwargs):
        self.propertySelector=None
        for _name in kwargs.keys():
            pass
        super(FlaskForm, self).__init__(*args, **kwargs)
        
    def setPropertyList(self,propertyList):
        self.propertySelector=PropertySelector(propertyList)
     
    def setParetoChoices(self):
        '''
        set the pareto choices
        '''
        self.paretoSelect.choices=[]
        for level in range(1,10):
            pareto=Pareto(level)
            choice=(f"{pareto.level}",pareto.asText(long=True))
            self.paretoSelect.choices.append(choice)
        pass 

class PropertySelector(Widget):
    '''
    select properties
    '''


    def __init__(self, propertyList:list):
        '''
        Constructor
        
        Args:
            propertyList(list): the list of properties to show
        '''
        self.propertyList=propertyList
        
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
        