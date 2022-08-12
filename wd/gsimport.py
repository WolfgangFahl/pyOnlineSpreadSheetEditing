import justpy as jp
from spreadsheet.googlesheet import GoogleSheet
from lodstorage.lod import LOD
from lodstorage.sparql import SPARQL
from markupsafe import Markup
import copy
import datetime
import re
import pprint
import sys
import onlinespreadsheet.version as version
from jpwidgets.widgets import LodGrid, QPasswordDialog
from jpwidgets.bt5widgets import App, Alert, IconButton, Switch
from spreadsheet.wikidata import Wikidata
from spreadsheet.wbquery import WikibaseQuery

class WikidataGrid():
    '''
    the tabular data to work with
    '''
    def __init__(self,wbQueries):
        '''
        constructor
        
        wbQueries(dict): the WikibaseQueries
        '''
        self.wbQueries=wbQueries
        
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
            raise Exception("Empty List of dicts is not valid")
        self.columns=self.lod[0].keys()
        for index,row in enumerate(self.lod):
            row["lodRowIndex"]=index
        self.viewLod=copy.deepcopy(self.lod)
        
    def getColumnTypeAndVarname(self,entityName,propName):
        '''
        slightly modified getter to account for "item" special case
        '''
        wbQuery=self.wbQueries[entityName]
        if propName=="item":
            column="item"
            propType=""
            varName="item"
        else:
            column,propType,varName=wbQuery.getColumnTypeAndVarname(propName)
        return wbQuery,column,propType,varName
    
    def getHtmlColums(self,entityName):
        '''
        get the columns that have html content(links) for the given entityName
        
        entityName(str): the name of the entity
        '''
        htmlColumns=[0]
        # loop over columns of dataframe
        wbQuery=self.wbQueries[entityName]
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
    
class GridSync():
    '''
    allow syncing the grid with data from wikibase
    '''
    def __init__(self,wdgrid,sheetName,pk,debug:bool=False):
        self.wdgrid=wdgrid
        self.sheetName=sheetName
        self.pk=pk
        self.debug=debug
        self.itemRows=wdgrid.lod
        self.wbQuery,self.pkColumn,self.pkType,self.pkProp=wdgrid.getColumnTypeAndVarname(sheetName,pk)
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

class GoogleSheetWikidataImport(App):
    '''
    reactive google sheet display to be used for wikidata import of the content
    '''
    
    def __init__(self,version):
        '''
        constructor
        
        Args:
            url(str): the url of the google spreadsheet
            sheetNames(list): the name of the sheets to import data from
            pk(str): the primary key property to use for wikidata queries
            endpoint(str): the url of  the endpoint to use
            lang(str): the languate to use for labels
            debug(bool): if True show debug information
        '''
        App.__init__(self, version,title="Google Spreadsheet Wikidata Import")
        # url,sheetNames:list,pk:str,endpoint:str,lang:str="en",debug:bool=False
        # @TODO make configurable
        self.metaDataSheetName="WikidataMetadata"
        self.wd=Wikidata("https://www.wikidata.org",debug=True)
        self.agGrid=None
        self.wdgrid=None
        self.dryRun=True
        self.ignoreErrors=False
        self.addMenuLink(text='Home',icon='home', href="/")
        self.addMenuLink(text="docs",icon="file-document",href='https://wiki.bitplan.com/index.php/PyOnlineSpreadSheetEditing')
        self.addMenuLink(text='github',icon='github', href="https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing")
    
            
    def load(self,url:str,sheetName:str,metaDataSheetName="WikidataMetadata"):
        '''
        load my googlesheet, wikibaseQueries and dataframe
        
        Args:
            url(str): the url to load the spreadsheet from
            sheetName(str): the sheetName of the sheet/tab to load
        '''
        wbQueries=WikibaseQuery.ofGoogleSheet(url, metaDataSheetName, debug=self.debug)
        self.wdgrid=WikidataGrid(wbQueries)
        self.gs=GoogleSheet(url)    
        self.gs.open([sheetName])  
        self.wdgrid.setLod(self.gs.asListOfDicts(sheetName))
            
    def onCheckWikidata(self,msg=None):
        '''
        check clicked - check the wikidata content
        
        Args:
            msg(dict): the justpy message
        '''
        if self.debug:
            print(msg)
        try:
            self.clearErrors()
            # prepare syncing the table results with the wikibase query result
            gridSync=GridSync(self.wdgrid,self.sheetName,self.pk,debug=self.debug)
            # query based on table content
            gridSync.query(self.sparql)
            # get the view copy to insert result as html statements
            viewLod=self.wdgrid.viewLod
            gridSync.markViewLod(viewLod)
            # reload the AG Grid with the html enriched content
            self.reloadAgGrid(viewLod)
        except Exception as ex:
            self.handleException(ex)
           
    def reloadAgGrid(self,viewLod:list,showLimit=10):
        '''
        reload the agGrid with the given list of Dicts
        
        Args:
            viewLod(list): the list of dicts for the current view
        '''
        self.agGrid.load_lod(viewLod)
        if self.debug:
            pprint.pprint(viewLod[:showLimit])
        self.refreshGridSettings()
        
    def refreshGridSettings(self):
        '''
        refresh the ag grid settings e.g. enable the row selection event handler
        enable row selection event handler
        '''
        self.agGrid.on('rowSelected', self.onRowSelected)
        self.agGrid.options.columnDefs[0].checkboxSelection = True
        # set html columns according to types that have links
        self.agGrid.html_columns = self.wdgrid.getHtmlColums(self.sheetName)
         
    def reload(self,_msg=None,clearErrors=True):
        '''
        reload the table content from myl url and sheet name
        '''
        if clearErrors:
            self.clearErrors()
        self.load(self.url,self.sheetName,self.metaDataSheetName)
        # is there already agrid?
        if self.agGrid is None:
            self.agGrid = LodGrid(a=self.rowC)
        viewLod=self.wdgrid.viewLod
        self.wdgrid.linkWikidataItems(viewLod)
        self.reloadAgGrid(viewLod)
        # set up the primary key selector
        self.pkSelect.delete_components()
        self.pkSelect.add(jp.Option(value="item",text="item"))
        wbQuery=self.wdgrid.wbQueries[self.sheetName]
        for propertyName,row in wbQuery.propertiesByName.items():
            columnName=row["Column"]
            if columnName:
                self.pkSelect.add(jp.Option(value=propertyName,text=columnName))
      
    def onChangeSheet(self, msg:dict):
        '''
        handle selection of a different sheet 
        
        Args:
            msg(dict): the justpy message
        '''
       
        if self.debug:
            print(msg)
        self.sheetName=msg.value
        try:
            self.reload()
        except Exception as ex:
            self.handleException(ex)
        
    def onChangePk(self, msg:dict):
        '''
        handle selection of a different primary key
        
        Args:
            msg(dict): the justpy message
        '''
        if self.debug:
            print(msg)
        self.pk=msg.value
        try:
            self.reload()
        except Exception as ex:
            self.handleException(ex)
        
    def onChangeUrl(self,msg:dict):
        '''
        handle selection of a different url
        
        Args:
            msg(dict): the justpy message
        '''
        if self.debug:
            print(msg)
        self.url=msg.value
        self.gsheetUrl.href=self.url
        self.gsheetUrl.text=self.url
        try:
            self.reload()
        except Exception as ex:
            self.handleException(ex)
            
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
            
    def loginUser(self,user):
        self.loginButton.text=f"{user}"
        self.loginButton.iconName="logout"
        self.dryRunButton.disable=False
        
    def onloginViaDialog(self,_msg):
        '''
        handle login via dialog
        '''
        user=self.passwordDialog.userInput.value
        password=self.passwordDialog.passwordInput.value
        self.wd.loginWithCredentials(user, password)
        if self.wd.user is not None:
            self.loginUser(self.wd.user)
        
    def onLogin(self,msg:dict):
        '''
        handle Login
        Args:
            msg(dict): the justpy message
        '''
        if self.debug:
            print(msg)
        try:    
            self.clearErrors()
            if self.wd.user is None:
                self.wd.loginWithCredentials()
                if self.wd.user is None:
                    self.passwordDialog.loginButton.on("click",self.onloginViaDialog)
                    self.passwordDialog.value=True
                else:
                    self.loginUser(self.wd.user)
            else:
                self.wd.logout()
                self.dryRunButton.value=True
                self.dryRunButton.disable=True
                self.loginButton.text="login"
                self.loginButton.iconName   ="chevron_right"
        except Exception as ex:
                self.handleException(ex)
     
    def onRowSelected(self, msg):
        '''
        row selection event handler
        
        Args:
            msg(dict): row selection information
        '''
        if self.debug:
            print(msg)
        self.clearErrors()
        if msg.selected:
            self.rowSelected = msg.rowIndex
            write=not self.dryRun
            label=msg.data["label"]
            try:
                mapDict=self.wdgrid.wbQueries[self.sheetName].propertiesById
                rowData=msg.data
                # remove index
                rowData.pop("lodRowIndex")
                qid,errors=self.wd.addDict(msg.data, mapDict,write=write,ignoreErrors=self.ignoreErrors)
                if qid is not None:
                    # set item link
                    link=self.wdgrid.createLink(f"https://www.wikidata.org/wiki/{qid}", f"{label}")
                    self.wdgrid.viewLod[msg.rowIndex]["item"]=link
                    self.agGrid.load_lod(self.wdgrid.viewLod)
                    self.refreshGridSettings()
                if len(errors)>0:
                    self.errors.text=errors
                    print(errors)
                if self.dryRun:
                    prettyData=pprint.pformat(msg.data)
                    html=Markup(f"<pre>{prettyData}</pre>")
                    alert=Alert(text=html)
                    
            except Exception as ex:
                self.handleException(ex)

    def setup(self):
        self.url=self.args.url
        self.sheetNames=self.args.sheets
        self.sheetName=self.sheetNames[0]
        self.pk=self.args.pk
        self.endpoint=self.args.endpoint
        self.sparql=SPARQL(self.endpoint)
        self.lang="en" # @TODO Make configurable self.args.lang
        
    async def content(self):
        '''
        show aggrid for the given data frame
        '''
        self.setup()
        # select endpoint
        head="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">
<link rel="stylesheet" href="/static/css/pygments.css">
"""
        # extend the justpy Webpage with the given head parameters
        self.wp=self.getWp(head)
        self.rowA=jp.Div(classes="row",a=self.contentbox)
        self.rowB=jp.Div(classes="row",a=self.contentbox)
        self.rowC=jp.Div(classes="row",a=self.contentbox)
        self.rowD=jp.Div(classes="row",a=self.contentbox)
        self.errors=jp.Span(a=self.rowD,style='color:red')
        self.header=jp.Div(a=self.rowA)
        self.toolbar=jp.QToolbar(a=self.rowB)
        # for icons see  https://quasar.dev/vue-components/icon
        # see justpy/templates/local/materialdesignicons/iconfont/codepoints for available icons    
        self.reloadButton=IconButton(a=self.toolbar,text='',iconName="refresh-circle",click=self.reload,classes="btn btn-primary btn-sm col-1")
        self.checkButton=IconButton(a=self.toolbar,text='',iconName='check',click=self.onCheckWikidata,classes="btn btn-primary btn-sm col-1")
        self.loginButton=IconButton(a=self.toolbar,iconName='login',text="",click=self.onLogin,classes="btn btn-primary btn-sm col-1")
        self.passwordDialog=QPasswordDialog(a=self.wp)
        #jp.Br(a=self.header)
        # url
        urlLabelText="Google Spreadsheet Url"
        self.gsheetUrl=jp.A(a=self.header,href=self.url,target="_blank",title=urlLabelText)
        self.linkIcon=jp.QIcon(a=self.gsheetUrl,name="link",size="md")
        self.urlInput=jp.Input(a=self.header,placeholder=urlLabelText,size=80,value=self.url,change=self.onChangeUrl)
        self.dryRunButton=Switch(a=self.header,labelText="dry run",checked=True,disable=True)
        self.dryRunButton.on("input",self.onChangeDryRun)
        self.ignoreErrorsButton=Switch(a=self.header,labelText="ignore errors",checked=self.ignoreErrors)
        self.ignoreErrorsButton.on("input",self.onChangeIgnoreErrors)
        jp.Br(a=self.header)
        # link to the wikidata item currently imported
        selectorClasses='w-32 m-4 p-2 bg-white'
        # select for sheets
        self.sheetSelect = jp.Select(classes=selectorClasses, a=self.header, value=self.sheetName,
            change=self.onChangeSheet)
        for sheetName in self.sheetNames:
            self.sheetSelect.add(jp.Option(value=sheetName, text=sheetName))
        # selector for column/property
        self.pkSelect=jp.Select(classes=selectorClasses,a=self.header,value=self.pk,
            change=self.onChangePk)
        jp.Br(a=self.header)
        try:
            self.reload()
        except Exception as ex:
            self.handleException(ex)
        return self.wp
        
    def getParser(self):
        '''
        get the argument parser
        '''
        parser=App.getParser(self)
        parser.add_argument('--endpoint',help="the endpoint to use [default: %(default)s]",default="https://query.wikidata.org/sparql")
        #parser.add_argument('--dryrun', action="store_true", dest='dryrun', help="dry run only")
        parser.add_argument('--url')
        parser.add_argument('--sheets',nargs="+",required=True)
        parser.add_argument('--pk')
        return parser
     
DEBUG = 1
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    gsimport=GoogleSheetWikidataImport(version.Version)
    sys.exit(gsimport.mainInstance())