'''
Created on 2022-07-24

@author: wf
'''
import sys
import traceback
import justpy as jp
from jpwidgets.bt5widgets import App
import onlinespreadsheet.version as version
from lodstorage.query import EndpointManager
from wd.wdsearch import WikidataSearch

class WikiDataBrowser(App):
    '''
    browser for Wikidata
    '''

    def __init__(self,version):
        '''
        Constructor
        
        Args:
            version(Version): the version info for the app
        '''
        App.__init__(self, version,title="Wikidata browser")
        self.addMenuLink(text='Home',icon='home', href="/")
        self.addMenuLink(text='github',icon='github', href="https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing")
        self.addMenuLink(text='Documentation',icon='file-document',href="https://wiki.bitplan.com/index.php/PyOnlineSpreadSheetEditing")
        self.endpoints=EndpointManager.getEndpoints()
        self.wdSearch=WikidataSearch()
        
    def getParser(self):
        '''
        get my parser
        '''
        parser=super().getParser()
        parser.add_argument('-en', '--endpointName', default="wikidata", help=f"Name of the endpoint to use for queries. Available by default: {EndpointManager.getEndpointNames()}")
        return parser
    
        
    def handleException(self,ex):
        '''
        handle the given exception
        
        Args:
            ex(Exception): the exception to handle
        '''
        errorMsg=str(ex)
        trace=""
        if self.debug:
            trace=traceback.format_exc()
        errorMsgHtml=f"{errorMsg}<pre>{trace}</pre>"
        self.errors.inner_html=errorMsgHtml
        print(errorMsg)
        if self.debug:
            print(trace)
        
    def onChangeEndpoint(self,msg:dict):
        '''
        handle selection of a different endpoint
        
        Args:
            msg(dict): the justpy message
        '''
       
        if self.debug:
            print(msg)
        self.endPointName=msg.value
        
        
    def onItemChange(self,msg:dict):
        '''
        rect on changes in the item input
        '''
        try:
            searchFor=msg.value
            self.feedback.text = searchFor
            srlist=self.wdSearch.search(searchFor)
            if srlist is not None:
                # remove current Selection
                self.itemSelect.delete_components()
                for sr in srlist:
                    qid=sr["id"]
                    itemLabel=sr["label"]
                    desc=""
                    if "display" in sr:
                        display=sr["display"]
                        desc=display["description"]["value"]
                    text=f"{itemLabel}({qid}){desc}"
                    if self.debug:
                        print(sr)
                    self.itemSelect.add(jp.Option(value="qid",text=text))
        except Exception as ex:
            self.handleException(ex)
            
    def createSelect(self,text,value,change,a):
        _selectorLabel=jp.Label(text=text,a=a,classes="form-label")
        select=jp.Select(a=a,classes="form-select",value=value,change=change)
        return select
    
    def createInput(self,text,a,placeholder,change):
        _selectorLabel=jp.Label(text=text,a=a,classes="form-label")
        jpinput=jp.Input(a=a,classes="form-input",placeholder=placeholder)
        jpinput.on('input', change)
        jpinput.on('change', change)   
        return jpinput
    
    async def browse(self):
        '''
        browse
        '''
        head="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">"""
        wp=self.getWp(head)
        rowA=jp.Div(classes="row",a=self.contentbox)
        colA1=jp.Div(classes="col-3",a=rowA)
        colA2=jp.Div(classes="col-9",a=rowA)
        rowB=jp.Div(classes="row",a=self.contentbox)
        colB1=jp.Div(classes="col-3",a=rowB)
        colB2=jp.Div(classes="col-3",a=rowB)
        rowC=jp.Div(classes="row",a=self.contentbox)
        self.endpointName=self.args.endpointName
        self.endpointSelect=self.createSelect("Endpoint", self.endpointName, a=colA1,change=self.onChangeEndpoint)
        for name in EndpointManager.getEndpointNames():
            self.endpointSelect.add(jp.Option(value=name, text=name))
        self.item=self.createInput(text="Wikidata item", a=colB1, placeholder='Please type here to search ...',change=self.onItemChange) 
        self.itemSelect=jp.Select(classes="form-select",a=colB2)
        self.feedback=jp.Div(a=rowC)
        self.errors=jp.Span(a=rowC,style='color:red')
        return wp
        
def main(argv=None): # IGNORE:C0111
    '''main program.'''

    if argv is None:
        argv=sys.argv[1:]
        
    wdBrowser=WikiDataBrowser(version.Version)
    wdBrowser.cmdLine(argv,wdBrowser.browse)

    
DEBUG = 0
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    sys.exit(main())