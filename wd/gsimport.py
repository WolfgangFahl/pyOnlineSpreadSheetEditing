import justpy as jp
from spreadsheet.googlesheet import GoogleSheet

from spreadsheet.version import Version
from lodstorage.lod import LOD
from lodstorage.sparql import SPARQL
import datetime
import os
import pprint
import sys
import traceback
from spreadsheet.wikidata import Wikidata
from spreadsheet.wbquery import WikibaseQuery


DEBUG = 0
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter


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
        self.wd=Wikidata("https://www.wikidata.org",debug=True)
        self.wd.login()
        self.grid=None
        
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
        self.wbQueries=WikibaseQuery.ofGoogleSheet(url, "Wikidata", debug=self.debug)
        self.gs=GoogleSheet(url)    
        self.gs.open([sheetName])  
        self.df=self.gs.dfs[sheetName]
        self.refreshLod()
            
    def onCheckWikidata(self,msg=None):
        '''
        check clicked - check the wikidata content
        '''
        if self.debug:
            print(msg)
        try:
            wbQuery=self.wbQueries[self.sheetName]
            itemRows=self.gs.asListOfDicts(self.sheetName)
            pkColumn,pkType,pkProp=wbQuery.getColumnTypeAndVarname(self.pk)
            itemsByPk,_dup=LOD.getLookup(itemRows,pkColumn)
            if self.debug:
                print(itemsByPk.keys())
            lang="en" if pkType =="text" else None
            valuesClause=wbQuery.getValuesClause(itemsByPk.keys(),pkProp,lang=lang)
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
    
    def checkCell(self,pkColumn,pkValue,column,value,propVarname,propType,propLabel):
        dfCell=self.df.loc[self.df[pkColumn]==pkValue,column]
        dfValue=dfCell.values[0]
        valueType=type(value)
        print(f"{column}({propVarname})={value}({propLabel}:{valueType})⮂{dfValue}")
        # overwrite empty cells
        if not dfValue:
            doadd=True
            if not propType:
                value=self.createLink(value, propLabel)
            if valueType==str:
                pass    
            elif valueType==datetime.datetime:
                value=value.strftime('%Y-%m-%d')   
            else:
                doadd=False
                print(f"{valueType} not added")   
            if doadd:                         
                self.df.loc[self.df[pkColumn]==pkValue,column]=value
        
    def markGrid(self,rows):
        '''
        mark my grid with the given rows
        
        Args:
            rows(list): a list of dict with the query result
        '''
        wbQuery=self.wbQueries[self.sheetName]
        pkColumn,_pkType,pkProp=wbQuery.getColumnTypeAndVarname(self.pk)
        # get my table data indexed by the primary key
        lodByPk,_dup=LOD.getLookup(self.lod, pkColumn)
        # now check the rows
        for row in rows:
            # get the primary key value
            pkValue=row[pkProp]
            # if we have the primary key then we mark the whole row
            if pkValue in lodByPk:
                if self.debug:
                    print(pkValue)
                #https://stackoverflow.com/a/17071908/1497139
                lodRow=lodByPk[pkValue]
                self.df.loc[self.df[pkColumn]==pkValue,"item"]=self.createLink(row["item"],row["itemLabel"])
                self.checkCell(pkColumn,pkValue,"description",row["itemDescription"],propVarname="itemDescription",propType="string",propLabel="")
                for propVarname,value in row.items():
                    # remap the property variable name to the original property description
                    if propVarname in wbQuery.propertiesByVarname:
                        propRow=wbQuery.propertiesByVarname[propVarname]
                        if self.debug:
                            column=propRow["Column"]
                            propType=propRow["Type"]
                            if not propType:
                                propLabel=row[f"{propVarname}Label"]
                            else:
                                propLabel=""
                            if column in lodRow:
                                self.checkCell(pkColumn,pkValue,column,value,propVarname,propType,propLabel)
                           
        self.grid.load_pandas_frame(self.df)
        self.refreshLod()
        self.refreshGridSettings()
        
    def refreshLod(self):
        self.lod=self.df.to_dict('records')
        
    def refreshGridSettings(self):
        # enable row selection event handler
        self.grid.row_data_div = self.row_data_div
        self.grid.on('rowSelected', self.onRowSelected)
        self.grid.options.columnDefs[0].checkboxSelection = True
        self.grid.html_columns = [0,8,9]
         
    def reload(self,_msg=None):
        '''
        reload clicked
        '''
        self.load(self.url,self.sheetName)
        if self.grid is None:
            grid_options={
                'enableCellTextSelection':True
            }
            grid = self.df.jp.ag_grid(a=self.container,options=grid_options)
            self.grid=grid
        else:
            self.grid.load_pandas_frame(self.df)
            self.refreshLod()
        
        self.refreshGridSettings()
        self.pkSelect.delete_components()
        wbQuery=self.wbQueries[self.sheetName]
        for propertyName,row in wbQuery.propertiesByName.items():
            columnName=row["Column"]
            if columnName:
                self.pkSelect.add(jp.Option(value=propertyName,text=columnName))
      
    def onChangeSheet(self, msg):
        '''
        handle selection of a different sheet 
        '''
        if self.debug:
            print(msg)
        self.sheetName=msg.value
        self.reload()
        
    def onChangePk(self, msg):
        '''
        handle selection of a different primary key
        '''
        if self.debug:
            print(msg)
        self.pk=msg.value
        self.reload()
        
    def onChangeUrl(self,msg):
        '''
        handle selection of a different url
        '''
        if self.debug:
            print(msg)
        self.url=msg.value
        self.reload()
    
    def onRowSelected(self, msg):
        '''
        row selection event handler
        
        Args:
            msg(dict): row selection information
        '''
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
                    self.link.href=f"https://www.wikidata.org/wiki/{qid}"
                    self.link.text=f"{label}"
                if len(errors)>0:
                    self.errors.text=errors
                    print(errors)
            except Exception as ex:
                self.handleException(ex)
      
        elif self.rowSelected == msg.rowIndex:
            self.row_data_div.text = ''

    def gridForDataFrame(self):
        '''
        show aggrid for the given data frame
        '''
        self.wp = jp.WebPage()
        self.container=jp.Div(a=self.wp)
        self.header=jp.Div(a=self.container)
        # url
        jp.Label(a=self.header,text="Google Spreasheet Url:")
        self.urlInput=jp.Input(a=self.header,placeholder="google sheet url",size=80,value=self.url,change=self.onChangeUrl)
        jp.Br(a=self.header)
        # link to the wikidata item currently imported
        button_classes = 'w-24 mr-2 mb-2 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full'
        self.reloadButton=jp.Button(a=self.header,text='reload',classes=button_classes,click=self.reload)
        self.checkButton=jp.Button(a=self.header,text='check',classes=button_classes,click=self.onCheckWikidata)
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
        self.link=jp.A(a=self.header,href="https://www.wikidata.org/",text="wikidata")
        self.row_data_div = jp.Div(a=self.container)
        self.errors=jp.Span(a=self.container,style='color:red')
        self.reload()
        return self.wp
    
    def start(self):
        '''
        start the reactive webserver
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