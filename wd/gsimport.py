import typing

import justpy as jp
from spreadsheet.googlesheet import GoogleSheet
from lodstorage.sparql import SPARQL
import sys
import onlinespreadsheet.version as version
from jpwidgets.widgets import QPasswordDialog
from jpwidgets.bt5widgets import App, IconButton, Switch
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
        # url,sheetNames:list,pk:str,endpoint:str,lang:str="en",debug:bool=False
        # @TODO make configurable
        self.metaDataSheetName="WikidataMetadata"
        self.wdgrid: WikidataGrid = None
        self.addMenuLink(text='Home',icon='home', href="/")
        self.addMenuLink(text="docs",icon="file-document",href='https://wiki.bitplan.com/index.php/PyOnlineSpreadSheetEditing')
        self.addMenuLink(text='github',icon='github', href="https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing")

    def load_items_from_selected_sheet(self) -> typing.List[dict]:
        """
        Extract the records from the selected sheet and returns them as LoD

        Returns:
            List of dicts containing the sheet content
        """
        self.wbQueries = WikibaseQuery.ofGoogleSheet(self.url, self.metaDataSheetName, debug=self.debug)
        self.gs = GoogleSheet(self.url)
        self.gs.open([self.sheetName])
        items = self.gs.asListOfDicts(self.sheetName)
        return items

    def setup_aggrid_post_reload(self):
        viewLod = self.wdgrid.viewLod
        gridSync = self.get_GridSync()
        self.wdgrid.agGrid.html_columns = gridSync.getHtmlColumns()
        self.wdgrid.linkWikidataItems(viewLod)
        self.pkSelect.delete_components()
        self.pkSelect.add(jp.Option(value="item", text="item"))
        wbQuery = self.get_wbQuery_of_selected_sheet()
        for propertyName, row in wbQuery.propertiesByName.items():
            columnName = row["Column"]
            if columnName:
                self.pkSelect.add(jp.Option(value=propertyName, text=columnName))


    async def reload(self,_msg=None,clearErrors=True):
        '''
        reload the table content from my url and sheet name
        '''
        await self.wdgrid.reload()

    def get_wbQuery_of_selected_sheet(self) -> typing.Union[None, WikibaseQuery]:
        """
        get the wikibase Query for the currently selected sheet
        
        Returns:
            WikibaseQuery: could be none if the current sheetName is not valid
        """
        return self.wbQueries.get(self.sheetName, None)

    def onCheckWikidata(self, msg=None):
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
            gridSync = self.get_GridSync()
            # query based on table content
            gridSync.query(self.sparql)
            # get the view copy to insert result as html statements
            viewLod = self.wdgrid.viewLod
            gridSync.markViewLod(viewLod)
            # reload the AG Grid with the html enriched content
            self.wdgrid.reloadAgGrid(viewLod)
        except Exception as ex:
            self.handleException(ex)

    def get_GridSync(self) -> GridSync:
        wbQuery = self.get_wbQuery_of_selected_sheet()
        return GridSync(self.wdgrid, self.sheetName, self.pk, wbQuery=wbQuery, debug=self.debug)

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
        await self.reload()
     
    async def onChangePk(self, msg:dict):
        '''
        handle selection of a different primary key
        
        Args:
            msg(dict): the justpy message
        '''
        if self.debug:
            print(msg)
        self.pk=msg.value
        try:
            await self.reload()
        except Exception as ex:
            self.handleException(ex)
        
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
            
    def loginUser(self,user):
        self.loginButton.text=f"{user}"
        self.loginButton.iconName="logout"
        self.wdgrid.dryRunButton.disable=False
        
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
            wd=self.wdgrid.wd
            if wd.user is None:
                wd.loginWithCredentials()
                if wd.user is None:
                    self.passwordDialog.loginButton.on("click",self.onloginViaDialog)
                    self.passwordDialog.value=True
                else:
                    self.loginUser(wd.user)
            else:
                wd.logout()
                self.wdgrid.dryRunButton.value=True
                self.wdgrid.dryRunButton.disable=True
                self.loginButton.text="login"
                self.loginButton.iconName="chevron_right"
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
        self.wdgrid = WikidataGrid(
                app=self,
                entityName=self.sheetName,
                entityPluralName=None,
                source=self.url,
                getLod=self.load_items_from_selected_sheet,
                additional_reload_callback=self.setup_aggrid_post_reload,
                row_selected_callback=self.handle_row_selected
        )

    def handle_row_selected(self, **kawrgs):
        """
        Row selected callback to add selected row to wikidata
        """
        grid_sync = self.get_GridSync()
        return grid_sync.handle_row_selected_add_record_to_wikidata(**kawrgs)
        
    async def content(self):
        '''
        show the gsimport content
        '''
        self.setup()
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
        self.toolbar=jp.QToolbar(a=self.rowB, classes="flex flex-row gap-2")
        # for icons see  https://quasar.dev/vue-components/icon
        # see justpy/templates/local/materialdesignicons/iconfont/codepoints for available icons    
        self.reloadButton=IconButton(a=self.toolbar,text='',title="reload",iconName="refresh-circle",click=self.reload,classes="btn btn-primary btn-sm col-1")
        self.checkButton=IconButton(a=self.toolbar,text='',title="check",iconName='check',click=self.onCheckWikidata,classes="btn btn-primary btn-sm col-1")
        self.loginButton=IconButton(a=self.toolbar,title="login",iconName='login',text="",click=self.onLogin,classes="btn btn-primary btn-sm col-1")
        self.passwordDialog=QPasswordDialog(a=self.wp)
        #jp.Br(a=self.header)
        # url
        urlLabelText="Google Spreadsheet Url"
        self.url_div = jp.Div(a=self.header, classes="m-2 p-2 gap-4 flex flex-row")
        self.gsheetUrl=jp.A(a=self.url_div,href=self.url, text=self.url,target="_blank",title=urlLabelText)
        self.linkIcon=jp.QIcon(a=self.url_div,name="link",size="md")
        self.urlInput=jp.Input(a=self.url_div,placeholder=f"Enter new {urlLabelText}",size=80,change=self.onChangeUrl)
        self.wdgrid.setup(a=self.rowC)
        # link to the wikidata item currently imported
        selectorClasses='w-32 m-2 p-2 bg-white'
        # select for sheets
        self.sheetSelect = jp.Select(classes=selectorClasses, a=self.header, value=self.sheetName,
            change=self.onChangeSheet)
        for sheetName in self.sheetNames:
            self.sheetSelect.add(jp.Option(value=sheetName, text=sheetName))
        # selector for column/property
        self.pkSelect=jp.Select(classes=selectorClasses,a=self.header,value=self.pk,
            change=self.onChangePk)
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