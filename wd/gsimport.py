import typing

import justpy as jp
from spreadsheet.googlesheet import GoogleSheet
from lodstorage.sparql import SPARQL
import sys
import onlinespreadsheet.version as version
from jpwidgets.bt5widgets import App
from spreadsheet.wbquery import WikibaseQuery
from wd.wdgrid import WikidataGrid, GridSync

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
        self.jp=jp
        self.wdgrid: WikidataGrid = None
        self.gridSync: GridSync= None
        
        self.addMenuLink(text='Home',icon='home', href="/")
        self.addMenuLink(text="docs",icon="file-document",href='https://wiki.bitplan.com/index.php/PyOnlineSpreadSheetEditing')
        self.addMenuLink(text='github',icon='github', href="https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing")

    def load_items_from_selected_sheet(self) -> typing.List[dict]:
        """
        Extract the records from the selected sheet and returns them as LoD

        Returns:
            List of dicts containing the sheet content
        """
        self.wbQueries = WikibaseQuery.ofGoogleSheet(self.url, self.mappingSheetName, debug=self.debug)
        if len(self.wbQueries)==0:
            print(f"Warning Wikidata mapping sheet {self.mappingSheetName} not defined!" )
        self.gs = GoogleSheet(self.url)
        self.gs.open([self.sheetName])
        items = self.gs.asListOfDicts(self.sheetName)
        wbQuery=self.wbQueries.get(self.sheetName, None)
        self.gridSync.wbQuery=wbQuery
        return items

    async def onChangeSheet(self, msg:dict):
        '''
        handle selection of a different sheet 
        
        Args:
            msg(dict): the justpy message
        '''
        if self.debug:
            print(msg)
        # get the sheetName, entity Name
        self.sheetName=msg.value
        self.wdgrid.setEntityName(self.sheetName)
        await self.reload()
        
    async def onChangeUrl(self,msg:dict):
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
        self.urlInput.value = ""
        try:
            await self.reload()
        except Exception as ex:
            self.handleException(ex)
            
    def initSelf(self):
        """
        initialize my self. variables
        """
        self.url=self.args.url
        self.sheetNames=self.args.sheets
        if len(self.sheetNames)<1:
            raise Exception("need at least one sheetName in sheets argument")
        self.sheetName=self.sheetNames[0]
        self.mappingSheetName=self.args.mappingSheet
        self.endpoint=self.args.endpoint
        self.sparql=SPARQL(self.endpoint)
        self.lang=self.args.lang

    def setup(self):
        """
        setup the HTML Components
        """
        # link to the wikidata item currently imported
        selectorClasses='w-32 m-2 p-2 bg-white'
        # select for sheets
        self.sheetSelect = jp.Select(classes=selectorClasses, a=self.header, value=self.sheetName,
            change=self.onChangeSheet)
        for sheetName in self.sheetNames:
            self.sheetSelect.add(jp.Option(value=sheetName, text=sheetName))
  
        self.wdgrid = WikidataGrid(
                app=self,
                entityName=self.sheetName,
                entityPluralName=None, # make configurable
                source=self.url,
                getLod=self.load_items_from_selected_sheet,
        )
        self.gridSync=GridSync(wdgrid=self.wdgrid, entityName=self.sheetName, pk=self.args.pk,sparql=self.sparql,debug=self.debug)

    async def content(self):
        '''
        show the gsimport content
        '''
        self.initSelf()
        # select endpoint
        head="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">
<link rel="stylesheet" href="/static/css/pygments.css">
"""
        # extend the justpy Webpage with the given head parameters
        self.wp=self.getWp(head)
        self.rowA=jp.Div(classes="row",a=self.contentbox)
        self.colA1=jp.Div(classes="col-12",a=self.rowA)
        self.rowB=jp.Div(classes="row",a=self.contentbox)
        self.rowC=jp.Div(classes="row",a=self.contentbox)
        self.rowD=jp.Div(classes="row",a=self.contentbox)
        self.errors=jp.Span(a=self.rowD,style='color:red')
        self.header=self.colA1
        #jp.Br(a=self.header)
        # url
        urlLabelText="Google Spreadsheet Url"
        self.url_div = jp.Div(a=self.header, classes="m-2 p-2 gap-4 flex flex-row")
        self.gsheetUrl=jp.A(a=self.url_div,href=self.url, text=self.url,target="_blank",title=urlLabelText)
        self.linkIcon=jp.QIcon(a=self.url_div,name="link",size="md")
        self.urlInput=jp.Input(a=self.url_div,placeholder=f"Enter new {urlLabelText}",size=80,change=self.onChangeUrl)
        self.setup()
        self.gridSync.setup(a=self.rowB,header=self.header)
        self.wdgrid.setup(a=self.rowC)
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
        parser.add_argument('--mappingSheet',default="WikidataMapping")
        parser.add_argument('--pk')
        parser.add_argument('-l','--lang','--language',default="en",help="language to use")
        return parser
     
DEBUG = 1
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    gsimport=GoogleSheetWikidataImport(version.Version)
    sys.exit(gsimport.mainInstance())