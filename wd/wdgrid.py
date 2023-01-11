'''
Created on 2023-01-11

@author: wf
'''
import asyncio
import copy
import datetime
import pprint
import re
from markupsafe import Markup
from lodstorage.lod import LOD
from spreadsheet.wbquery import WikibaseQuery
from jpwidgets.bt5widgets import Alert, App, Switch
from jpwidgets.widgets import LodGrid
from spreadsheet.wikidata import Wikidata

class WikidataGrid():
    '''
    a grid with tabular data from wikidata to work with
    '''
    def __init__(self,app:App,entityName:str,wbQuery:WikibaseQuery,debug:bool=False):
        '''
        constructor
        
        app(App): the application context of this grid
        entityName(str): the name of the entity that this grid is for
        wbQuery(WikibaseQuery): the WikibaseQuery
        debug(bool): if True show debug information
        '''
        self.app=app
        self.agGrid=None
        self.entityName=entityName
        self.wbQuery=wbQuery
        self.debug=debug
        self.dryRun=True
        self.ignoreErrors=False
        self.app.dryRunButton.on("input",self.onChangeDryRun)
        self.app.ignoreErrorsButton.on("input",self.onChangeIgnoreErrors)
        # @TODO make configurable
        self.wd=Wikidata("https://www.wikidata.org",debug=True)
 
    def assureAgGrid(self,a):
        """
        assure there is an AgGrid instantiated
        """
        # is there already an agrid?
        if self.agGrid is None:
            self.agGrid = LodGrid(a=a)
            self.agGrid.theme="ag-theme-material"
            self.setDefaultColDef(self.agGrid)
        
    def setLodFromDataFrame(self,df):
        '''
        set my List of Dicts from the given data frame
        
        Args:
            df(Dataframe): the dataframe to set my list of dicts from
        '''
        lod=df.to_dict('records')
        self.setLod(lod)       
        
    def setLod(self,lod:list):
        '''
        set my list of dicts
        
        Args:
            lod(list): a list of dicts to work with
        '''
        self.lod=lod
        if len(lod)<1:
            msg=f"Empty List of dicts is not valid for {self.entityName}"
            raise Exception(msg)
        self.columns=self.lod[0].keys()
        for index,row in enumerate(self.lod):
            row["lodRowIndex"]=index
        self.viewLod=copy.deepcopy(self.lod)
        
    def reloadAgGrid(self,viewLod:list,showLimit=10):
        '''
        reload the agGrid with the given list of Dicts
        
        Args:
            viewLod(list): the list of dicts for the current view
        '''
        if self.agGrid is None:
            return
        self.agGrid.load_lod(viewLod)
        if self.debug:
            pprint.pprint(viewLod[:showLimit])
        self.refreshGridSettings()
        
    def setDefaultColDef(self, agGrid):
        """
        set the default column definitions
        """
        defaultColDef=agGrid.options.defaultColDef
        defaultColDef.resizable=True
        defaultColDef.sortable=True
        # https://www.ag-grid.com/javascript-data-grid/grid-size/
        defaultColDef.wrapText=True
        defaultColDef.autoHeight=True
        
    def refreshGridSettings(self):
        '''
        refresh the ag grid settings e.g. enable the row selection event handler
        enable row selection event handler
        '''
        self.agGrid.on('rowSelected', self.onRowSelected)
        self.agGrid.options.columnDefs[0].checkboxSelection = True
        # set html columns according to types that have links
        self.agGrid.html_columns = self.getHtmlColums()
        
    def getColumnTypeAndVarname(self,propName:str):
        '''
        slightly modified getter to account for "item" special case
        
        Args:
            propName(str): the name of the property
        '''
        wbQuery=self.wbQuery
        if propName=="item":
            column="item"
            propType=""
            varName="item"
        else:
            column,propType,varName=wbQuery.getColumnTypeAndVarname(propName)
        return wbQuery,column,propType,varName
    
    def getHtmlColums(self):
        '''
        get the columns that have html content(links) 
        '''
        htmlColumns=[0]
        # loop over columns of dataframe
        wbQuery=self.wbQuery
        for columnIndex,column in enumerate(self.columns):
            # check whether there is metadata for the column
            if column in wbQuery.propertiesByColumn:
                propRow=wbQuery.propertiesByColumn[column]
                propType=propRow["Type"]
                if not propType or propType=="extid" or propType=="url":
                    htmlColumns.append(columnIndex)
        return htmlColumns    
    
    def createLink(self,url,text):
        '''
        create a link from the given url and text
        
        Args:
            url(str): the url to create a link for
            text(str): the text to add for the link
        '''
        link=f"<a href='{url}' style='color:blue'>{text}</a>"
        return link
                
    def linkWikidataItems(self,viewLod,itemColumn:str="item"):
        '''
        link the wikidata entries in the given item column if containing Q values
        
        Args:
            viewLod(list): the list of dicts for the view
            itemColumn(str): the name of the column to handle
        '''
        for row in viewLod:
            if itemColumn in row:
                item=row[itemColumn]
                if re.match(r"Q[0-9]+",item):
                    itemLink=self.createLink(f"https://www.wikidata.org/wiki/{item}", item)
                    row[itemColumn]=itemLink
                    
    def addFitSizeButton(self,a):
        self.onSizeColumnsToFitButton=Switch(
            a=a,
            labelText="fit",
            checked=False
            #iconName='format-columns',
            #classes="btn btn-primary btn-sm col-1"
        )
        self.onSizeColumnsToFitButton.on("input",self.onSizeColumnsToFit)
        
    async def onSizeColumnsToFit(self,_msg:dict):   
        try:
            await asyncio.sleep(0.2)
            if self.agGrid:
                await self.agGrid.run_api('sizeColumnsToFit()', self.app.wp)
        except Exception as ex:
            self.app.handleException(ex)
            
    def onChangeDryRun(self,msg:dict):
        '''
        handle change of DryRun setting
        
        Args:
            msg(dict): the justpy message
        '''
        self.dryRun=msg.value
        
    def onChangeIgnoreErrors(self,msg:dict):
        '''
        handle change of IgnoreErrors setting
        
        Args:
            msg(dict): the justpy message
        '''
        self.ignoreErrors=msg.value    
            
    def onRowSelected(self, msg):
        '''
        row selection event handler
        
        Args:
            msg(dict): row selection information
        '''
        if self.debug:
            print(msg)
        self.app.clearErrors()
        if msg.selected:
            self.rowSelected = msg.rowIndex
            write=not self.dryRun
            label=msg.data["label"]
            try:
                mapDict=self.wbQuery.propertiesById
                rowData=msg.data
                # remove index
                rowData.pop("lodRowIndex")
                qid,errors=self.wd.addDict(msg.data, mapDict,write=write,ignoreErrors=self.ignoreErrors)
                if qid is not None:
                    # set item link
                    link=self.createLink(f"https://www.wikidata.org/wiki/{qid}", f"{label}")
                    self.wdgrid.viewLod[msg.rowIndex]["item"]=link
                    self.agGrid.load_lod(self.wdgrid.viewLod)
                    self.refreshGridSettings()
                if len(errors)>0:
                    self.app.errors.text=errors
                    print(errors)
                if self.dryRun:
                    prettyData=pprint.pformat(msg.data)
                    html=Markup(f"<pre>{prettyData}</pre>")
                    # create an alert
                    alert=Alert(text="",a=self.app.rowA)
                    alert.contentDiv.inner_html=html
                    
            except Exception as ex:
                self.app.handleException(ex)
                    
class GridSync():
    '''
    allow syncing the grid with data from wikibase
    '''
    def __init__(self,wdgrid,sheetName,pk,debug:bool=False):
        """
        constructor
        
        Args:
            wdgrid(WikiDataGrid): the wikidata grid to use
            debug(bool): if True show debug information
        """
        self.wdgrid=wdgrid
        self.sheetName=sheetName
        self.pk=pk
        self.debug=debug
        self.itemRows=wdgrid.lod
        self.wbQuery,self.pkColumn,self.pkType,self.pkProp=wdgrid.getColumnTypeAndVarname(pk)
        self.itemsByPk,_dup=LOD.getLookup(self.itemRows,self.pkColumn)
        if self.debug:
            print(self.itemsByPk.keys())
            
    def query(self,sparql):
        '''
        query the wikibase instance based on the list of dict
        '''
        lang="en" if self.pkType =="text" else None
        valuesClause=self.wbQuery.getValuesClause(self.itemsByPk.keys(),self.pkProp,propType=self.pkType,lang=lang)
        self.sparqlQuery=self.wbQuery.asSparql(filterClause=valuesClause,orderClause=f"ORDER BY ?{self.pkProp}",pk=self.pk)
        if self.debug:
            print(self.sparqlQuery)
        self.wbRows=sparql.queryAsListOfDicts(self.sparqlQuery)
        if self.debug:
            pprint.pprint(self.wbRows)
            
    def checkCell(self,viewLodRow,column,value,propVarname,propType,propLabel,propUrl:str=None):
        '''
        update the cell value for the given 
        
        Args:    
            viewLodRow(dict): the row to modify
            value(object): the value to set for the cell
            propVarName(str): the name of the property Variable set in the SPARQL statement
            propType(str): the abbreviation for the property Type
            propLabel(str): the propertyLabel (if any)
            propUrl(str): the propertyUrl (if any)
        '''
        cellValue=viewLodRow[column]
        valueType=type(value)
        print(f"{column}({propVarname})={value}({propLabel}:{propUrl}:{valueType})⮂{cellValue}")
        # overwrite empty cells
        overwrite=not cellValue
        if cellValue:
            # overwrite values with links
            if propUrl and cellValue==value:
                overwrite=True
        if overwrite and value:
            doadd=True
            # create links for item  properties
            if not propType:
                value=self.wdgrid.createLink(value, propLabel)
            elif propType=="extid":
                value=self.wdgrid.createLink(propUrl,value)
            if valueType==str:
                pass    
            elif valueType==datetime.datetime:
                value=value.strftime('%Y-%m-%d')   
            else:
                doadd=False
                print(f"{valueType} not added")   
            if doadd:                         
                viewLodRow[column]=value
            
    def markViewLod(self,viewLod):
        '''
            viewLod(list): a list of dict for the mark result
        '''
        # now check the rows
        for wbRow in self.wbRows:
            # get the primary key value
            pkValue=wbRow[self.pkProp]
            pkValue=re.sub(r"http://www.wikidata.org/entity/(Q[0-9]+)", r"\1",pkValue)
            # if we have the primary key then we mark the whole row
            if pkValue in self.itemsByPk:
                if self.debug:
                    print(pkValue)
                # https://stackoverflow.com/questions/14538885/how-to-get-the-index-with-the-key-in-a-dictionary
                lodRow=self.itemsByPk[pkValue]
                rowIndex=lodRow["lodRowIndex"]
                viewLodRow=viewLod[rowIndex]
                itemLink=self.wdgrid.createLink(wbRow["item"],wbRow["itemLabel"])
                viewLodRow["item"]=itemLink
                itemDescription=wbRow.get("itemDescription","")
                self.checkCell(viewLodRow,"description",itemDescription,propVarname="itemDescription",propType="string",propLabel="")
                # loop over the result items
                for propVarname,value in wbRow.items():
                    # remap the property variable name to the original property description
                    if propVarname in self.wbQuery.propertiesByVarname:
                        propRow=self.wbQuery.propertiesByVarname[propVarname]
                        column=propRow["Column"]
                        propType=propRow["Type"]
                        if not propType:
                            propLabel=wbRow[f"{propVarname}Label"]
                        else:
                            propLabel=""
                        if propType=="extid":
                            propUrl=wbRow[f"{propVarname}Url"]
                        else:
                            propUrl=""
                        # Linked Or
                        if type(value)==str and value.startswith("http://www.wikidata.org/entity/") and f"{propVarname}Label" in wbRow:
                            propUrl=value
                            propLabel=wbRow[f"{propVarname}Label"]
                            value=propLabel
                        if column in lodRow:
                            self.checkCell(viewLodRow,column,value,propVarname,propType,propLabel,propUrl)   