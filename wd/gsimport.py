import justpy as jp
from spreadsheet.googlesheet import GoogleSheet
from spreadsheet.wikidata import Wikidata
from spreadsheet.version import Version
from lodstorage.lod import LOD
import os
import sys
import traceback

DEBUG = 0
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

class GoogleSheetWikidataImport():
    '''
    reactive google sheet display to be used for wikidata import of the content
    '''
    def __init__(self,url,spreadSheetName,debug:bool=False):
        '''
        constructor
        
        Args:
            url(str): the url of the google spreadsheet
            spreadSheetName(str): the name of the sheet to import data from
            debug(bool): if True show debug information
        '''
        self.debug=debug
        self.url=url
        self.spreadSheetName=spreadSheetName
        self.wd=Wikidata("https://www.wikidata.org",debug=True)
        self.wd.login()
        
    def handleException(self,ex):
        '''
        handle the given exception
        
        Args:
            ex(Exception): the exception to handle
        '''
        print(str(ex))
        print(traceback.format_exc())
      
    def reload(self,_msg=None):
        '''
        reload clicked
        '''
        self.gs=GoogleSheet(self.url)    
        spreadSheetNames=[self.spreadSheetName,"Wikidata"] 
        self.gs.open(spreadSheetNames)  
        self.df=self.gs.dfs[self.spreadSheetName]
        mapRows=self.gs.asListOfDicts("Wikidata")
        self.mapDict,_dup=LOD.getLookup(mapRows, "PropertyId", withDuplicates=False)
        
        grid = self.df.jp.ag_grid(a=self.container)
        grid.row_data_div = self.row_data_div
        grid.on('rowSelected', self.row_selected)
        grid.options.columnDefs[0].checkboxSelection = True
      

    def row_selected(self, msg):
        '''
        row selection event handler
        
        Args:
            msg(dict): row selection information
        '''
        print(msg)
        if msg.selected:
            self.row_selected = msg.rowIndex
            write=True
            label=msg.data["label"]
            try:
                qid,errors=self.wd.addDict(msg.data, self.mapDict,write=write)
                if qid is not None:
                    self.link.href=f"https://www.wikidata.org/wiki/{qid}"
                    self.link.text=f"{label}"
                if len(errors)>0:
                    self.errors.text=errors
                    print(errors)
            except Exception as ex:
                self.handleException(ex)
      
        elif self.row_selected == msg.rowIndex:
            self.row_data_div.text = ''

    def gridForDataFrame(self):
        '''
        show aggrid for the given data frame
        '''
        self.wp = jp.WebPage()
        self.container=jp.Div(a=self.wp)
        # link to the wikidata item currently imported
        button_classes = 'w-24 mr-2 mb-2 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full'
        self.reloadButton=jp.Button(a=self.container,text='reload',classes=button_classes,click=self.reload)
        self.link=jp.A(a=self.container,href="https://www.wikidata.org/",text="wikidata")
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
        parser.add_argument('--dryrun', action="store_true", dest='dryrun', help="")
        parser.add_argument('url')
        parser.add_argument('sheet')
        args = parser.parse_args(argv)
        gswdi=GoogleSheetWikidataImport(args.url,args.sheet)
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