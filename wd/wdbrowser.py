'''
Created on 2022-07-24

@author: wf
'''
import sys
import justpy as jp
from jpwidgets.bt5widgets import App
import onlinespreadsheet.version as version
from lodstorage.query import EndpointManager

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
        
    def getParser(self):
        '''
        get my parser
        '''
        parser=super().getParser()
        parser.add_argument('-en', '--endpointName', default="wikidata", help=f"Name of the endpoint to use for queries. Available by default: {EndpointManager.getEndpointNames()}")
        return parser
        
    def onChangeEndpoint(self,msg:dict):
        '''
        handle selection of a different endpoint
        
        Args:
            msg(dict): the justpy message
        '''
       
        if self.debug:
            print(msg)
        self.endPointName=msg.value
        
    def browse(self):
        '''
        browse
        '''
        head="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">"""
        wp=self.getWp(head)
        row1=jp.Div(classes="row",a=self.contentbox)
        col1=jp.Div(classes="col-2",a=row1)
        col2=jp.Div(classes="col-10",a=row1)
        
        self.endpointName=self.args.endpointName
        self.endpointSelect = jp.Select(a=col1,classes="form-select",value=self.endpointName,
            change=self.onChangeEndpoint)
        for name in EndpointManager.getEndpointNames():
            self.endpointSelect.add(jp.Option(value=name, text=name))
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