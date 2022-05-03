import justpy as jp
from spreadsheet.googlesheet import GoogleSheet

from lodstorage.lod import LOD
from lodstorage.sparql import SPARQL
import pandas as pd
import datetime
import re
import os
import pprint
import sys
import traceback

from jp.widgets import MenuButton
from jp.widgets import MenuLink

from spreadsheet.version import Version
from spreadsheet.wikidata import Wikidata
from spreadsheet.wbquery import WikibaseQuery

DEBUG = 0
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

class WikidataGrid():
    '''
    the tabular data to work with
    '''
    def __init__(self,wbQueries):
        '''
        constructor
        
        wbQueries(dict): the WikibaseQueries
        df(Dataframe): the pandas dataframe to initialize this grid with
        '''
        self.wbQueries=wbQueries
        
    def setDataFrame(self,df):
        self.df=df
        self.viewDf=pd.DataFrame(df).copy()
        self.lod=df.to_dict('records')
        
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
        for columnIndex,column in enumerate(self.df.columns):
            # check whether there is metadata for the column
            if column in wbQuery.propertiesByColumn:
                propRow=wbQuery.propertiesByColumn[column]
                propType=propRow["Type"]
                if not propType or propType=="extid" or propType=="url":
                    htmlColumns.append(columnIndex)
        return htmlColumns    

class GoogleSheetWikidataImport():
    '''
    reactive google sheet display to be used for wikidata import of the content
    '''
    def __init__(self,url,sheetNames:list,pk:str,endpoint:str,lang:str="en",debug:bool=False):
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
        self.debug=debug
        self.url=url
        self.sheetNames=sheetNames
        self.sheetName=sheetNames[0]
        self.pk=pk
        self.endpoint=endpoint
        self.lang=lang
        # @TODO make configurable
        self.wd=Wikidata("https://www.wikidata.org",debug=True)
        self.wd.login()
        self.agGrid=None
        self.wdgrid=None
        
    def handleException(self,ex):
        '''
        handle the given exception
        
        Args:
            ex(Exception): the exception to handle
        '''
        print(str(ex))
        if self.debug:
            print(traceback.format_exc())
            
    def load(self,url:str,sheetName:str):
        '''
        load my googlesheet, wikibaseQueries and dataframe
        
        Args:
            url(str): the url to load the spreadsheet from
            sheetName(str): the sheetName of the sheet/tab to load
        '''
        wbQueries=WikibaseQuery.ofGoogleSheet(url, "Wikidata", debug=self.debug)
        self.gs=GoogleSheet(url)    
        self.gs.open([sheetName])  
        df=self.gs.dfs[sheetName]
        self.wdgrid=WikidataGrid(wbQueries)
        self.wdgrid.setDataFrame(df)
            
    def onCheckWikidata(self,msg=None):
        '''
        check clicked - check the wikidata content
        
        Args:
            msg(dict): the justpy message
        '''
        if self.debug:
            print(msg)
        try:
            itemRows=self.gs.asListOfDicts(self.sheetName)
            wbQuery,pkColumn,pkType,pkProp=self.wdgrid.getColumnTypeAndVarname(self.sheetName,self.pk)
            itemsByPk,_dup=LOD.getLookup(itemRows,pkColumn)
            if self.debug:
                print(itemsByPk.keys())
            lang="en" if pkType =="text" else None
            valuesClause=wbQuery.getValuesClause(itemsByPk.keys(),pkProp,propType=pkType,lang=lang)
            sparqlQuery=wbQuery.asSparql(filterClause=valuesClause,orderClause=f"ORDER BY ?{pkProp}",pk=self.pk)
            if self.debug:
                print(sparqlQuery)
            sparql=SPARQL(self.endpoint)
            rows=sparql.queryAsListOfDicts(sparqlQuery)
            if self.debug:
                pprint.pprint(rows)
            self.markGrid(rows)
        except Exception as ex:
            self.handleException(ex)
            
    def createLink(self,url,text):
        '''
        create a link from the given url and text
        
        Args:
            url(str): the url to create a link for
            text(str): the text to add for the link
        '''
        link=f"<a href='{url}' style='color:blue'>{text}</a>"
        return link
    
    def checkCell(self,df,pkColumn,pkValue,column,value,propVarname,propType,propLabel,propUrl:str=None):
        '''
        update the cell value for the given 
        
        Args:    
            df(Dataframe): the dataframe to check 
            pkColumn(str): primary key column
            pkValue(str): primary key value
            value(object): the value to set for the cell
            propVarName(str): the name of the property Variable set in the SPARQL statement
            propType(str): the abbreviation for the property Type
            propLabel(str): the propertyLabel (if any)
            propUrl(str): the propertyUrl (if any)
        '''
        dfCell=df.loc[df[pkColumn]==pkValue,column]
        dfValue=dfCell.values[0] if len(dfCell.values)>0 else None
        valueType=type(value)
        print(f"{column}({propVarname})={value}({propLabel}{propUrl}:{valueType})⮂{dfValue}")
        # overwrite empty cells
        overwrite=not dfValue
        if dfValue:
            # overwrite values with links
            if not propType and dfValue==value:
                overwrite=True
            if propType=="extid" and dfValue==value:
                overwrite=True
        if overwrite and value:
            doadd=True
            # create links for item  properties
            if not propType:
                value=self.createLink(value, propLabel)
            elif propType=="extid":
                value=self.createLink(propUrl,value)
            if valueType==str:
                pass    
            elif valueType==datetime.datetime:
                value=value.strftime('%Y-%m-%d')   
            else:
                doadd=False
                print(f"{valueType} not added")   
            if doadd:                         
                df.loc[df[pkColumn]==pkValue,column]=value
                
    def linkWikidataItems(self,itemColumn:str="item"):
        '''
        link the wikidata entries in the given item column if containing Q values
        
        Args:
            itemColumn(str): the name of the column to handle
        '''
        df=self.wdgrid.viewDf
        for index,row in df.iterrows():
            item=row[itemColumn]
            if re.match(r"Q[0-9]+",item):
                itemLink=self.createLink(f"https://www.wikidata.org/wiki/{item}", item)
                df.loc[index,itemColumn]=itemLink
        
    def markGrid(self,rows:list):
        '''
        mark my grid with the given rows
        
        Args:
            rows(list): a list of dict with the query result
        '''
        df=self.wdgrid.viewDf
        wbQuery,pkColumn,_pkType,pkProp=self.wdgrid.getColumnTypeAndVarname(self.sheetName,self.pk)
        # get my table data indexed by the primary key
        lodByPk,_dup=LOD.getLookup(self.wdgrid.lod, pkColumn)
        # now check the rows
        for row in rows:
            # get the primary key value
            pkValue=row[pkProp]
            pkValue=re.sub(r"http://www.wikidata.org/entity/(Q[0-9]+)", r"\1",pkValue)
            # if we have the primary key then we mark the whole row
            if pkValue in lodByPk:
                if self.debug:
                    print(pkValue)
                #https://stackoverflow.com/a/17071908/1497139
                lodRow=lodByPk[pkValue]
                df.loc[df[pkColumn]==pkValue,"item"]=self.createLink(row["item"],row["itemLabel"])
                itemDescription=row.get("itemDescription","")
                self.checkCell(df,pkColumn,pkValue,"description",itemDescription,propVarname="itemDescription",propType="string",propLabel="")
                for propVarname,value in row.items():
                    # remap the property variable name to the original property description
                    if propVarname in wbQuery.propertiesByVarname:
                        propRow=wbQuery.propertiesByVarname[propVarname]
                        column=propRow["Column"]
                        propType=propRow["Type"]
                        if not propType:
                            propLabel=row[f"{propVarname}Label"]
                        else:
                            propLabel=""
                        if propType=="extid":
                            propUrl=row[f"{propVarname}Url"]
                        else:
                            propUrl=""
                        if column in lodRow:
                            self.checkCell(df,pkColumn,pkValue,column,value,propVarname,propType,propLabel,propUrl)
                       
        self.reloadAgGrid(df)      
        
    def reloadAgGrid(self,df,showLimit=10):
        '''
        reload the agGrid
        '''
        self.agGrid.load_pandas_frame(df)
        if self.debug:
            lod=df.to_dict('records')
            pprint.pprint(lod[:showLimit])
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
         
    def reload(self,_msg=None):
        '''
        reload the table content from myl url and sheet name
        '''
        self.load(self.url,self.sheetName)
        df=self.wdgrid.viewDf
        # is there already agrid?
        if self.agGrid is None:
            # set up the aggrid
            grid_options={
                'enableCellTextSelection':True,
                # enable sorting on all columns by default
                'defaultColDef': {
                    'sortable': True
                },
            }
            self.agGrid = jp.AgGrid(a=self.container,options=grid_options)
        self.linkWikidataItems()
        self.reloadAgGrid(df)
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
        try:
            self.reload()
        except Exception as ex:
            self.handleException(ex)
     
    def onRowSelected(self, msg):
        '''
        row selection event handler
        
        Args:
            msg(dict): row selection information
        '''
        df=self.wdgrid.viewDf
        if self.debug:
            print(msg)
        if msg.selected:
            self.rowSelected = msg.rowIndex
            write=True
            label=msg.data["label"]
            try:
                mapDict=self.wbQueries[self.sheetName].propertiesById
                qid,errors=self.wd.addDict(msg.data, mapDict,write=write)
                if qid is not None:
                    # set item link
                    link=self.createLink(f"https://www.wikidata.org/wiki/{qid}", f"{label}")
                    df.iloc[msg.rowIndex,0]=link
                    
                    self.agGrid.load_pandas_frame(df)
                    self.refreshGridSettings()
                if len(errors)>0:
                    self.errors.text=errors
                    print(errors)
            except Exception as ex:
                self.handleException(ex)

    def gridForDataFrame(self):
        '''
        show aggrid for the given data frame
        '''
        self.wp = jp.QuasarPage()
        self.container=jp.Div(a=self.wp)
        self.header=jp.Div(a=self.container)
        self.reloadButton=MenuButton(a=self.header,text='reload',icon="refresh",click=self.reload)
        self.checkButton=MenuButton(a=self.header,text='check',icon='check_box',click=self.onCheckWikidata)
        MenuLink(a=self.header,text="docs",icon="description",href='https://wiki.bitplan.com/index.php/PyOnlineSpreadSheetEditing')
        MenuLink(a=self.header,text='github',icon='forum', href="https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing")
        jp.Br(a=self.header)
        # url
        jp.Label(a=self.header,text="Google Spreasheet Url:")
        self.urlInput=jp.Input(a=self.header,placeholder="google sheet url",size=80,value=self.url,change=self.onChangeUrl)
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
        self.errors=jp.Span(a=self.container,style='color:red')
        try:
            self.reload()
        except Exception as ex:
            self.handleException(ex)
        return self.wp
    
    def start(self):
        '''
        start the reactive justpy webserver
        '''
        jp.justpy(self.gridForDataFrame)

def main(argv=None): # IGNORE:C0111
    '''main program.'''

    if argv is None:
        argv=sys.argv[1:]
        
    program_name = os.path.basename(__file__)
    program_version = "v%s" % Version.version
    program_build_date = str(Version.updated)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = "Wikidata Import from google spreadsheet"
    user_name="Wolfgang Fahl"
    program_license = '''%s

  Created by %s on %s.
  Copyright 2022 contributors. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc,user_name, str(Version.date))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-d", "--debug", dest="debug",   action="store_true", help="set debug [default: %(default)s]")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        parser.add_argument('--endpoint',help="the endpoint to use [default: %(default)s]",default="https://query.wikidata.org/sparql")
        parser.add_argument('--dryrun', action="store_true", dest='dryrun', help="dry run only")
        parser.add_argument('--url')
        parser.add_argument('--sheets',nargs="+",required=True)
        parser.add_argument('--pk')
        args = parser.parse_args(argv)
        gswdi=GoogleSheetWikidataImport(args.url,args.sheets,pk=args.pk,endpoint=args.endpoint,debug=args.debug)
        gswdi.start()
     
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 1
    except Exception as e:
        if DEBUG:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        print(traceback.format_exc())
        return 2     

if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    sys.exit(main())