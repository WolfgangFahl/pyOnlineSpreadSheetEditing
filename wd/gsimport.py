import justpy as jp
from onlinespreadsheet.googlesheet import GoogleSheet
from onlinespreadsheet.wikidata import Wikidata
from onlinespreadsheet.version import Version
from lodstorage.lod import LOD
import os
import sys

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
        self.gs=GoogleSheet(url)    
        spreadSheetNames=[spreadSheetName,"Wikidata"] 
        self.gs.open(spreadSheetNames)  
        self.df=self.gs.dfs[spreadSheetName]
        mapRows=self.gs.asListOfDicts("Wikidata")
        self.mapDict,_dup=LOD.getLookup(mapRows, "PropertyId", withDuplicates=False)
        self.wd=Wikidata("https://www.wikidata.org",debug=True)
        self.wd.login()

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
                qid=self.wd.addDict(msg.data, self.mapDict,write=write)
                if qid is not None:
                    self.link.href=f"https://www.wikidata.org/wiki/{qid}"
                    self.link.text=f"{label}"
            except Exception as ex:
                print(str(ex))
      
        elif self.row_selected == msg.rowIndex:
            self.row_data_div.text = ''

    def gridForDataFrame(self):
        '''
        show aggrid for the given data frame
        '''
        wp = jp.WebPage()
        self.row_data_div = jp.Div(a=wp)
        # link to the wikidata item currently imported
        self.link=jp.A(a=self.row_data_div,href="https://www.wikidata.org/",text="wikidata")
        grid = self.df.jp.ag_grid(a=wp)
        grid.row_data_div = self.row_data_div
        grid.on('rowSelected', self.row_selected)
        grid.options.columnDefs[0].checkboxSelection = True
        return wp
    
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
        return 2     

if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    sys.exit(main())