import justpy as jp
import json
import os
from lodstorage.query import Query,QuerySyntaxHighlight, Endpoint
from jpwidgets.bt5widgets import Alert,Collapsible, IconButton
from spreadsheet.spreadsheet import SpreadSheetType, SpreadSheet
import spreadsheet
from tabulate import tabulate
from urllib.error import HTTPError

class QueryDisplay():
    '''
    display queries
    '''

    def __init__(self,app,name:str,a,filenameprefix,text,sparql,endpointConf:Endpoint):
        '''
        Args:
            name(str): the name of the display and query
            a(jp.Component): an ancestor component
            filenameprefix(str): the filename prefix to use
            text(str)=the text to display
            endpointConf(Endpoint): SPARQL endpoint configuration to use

        '''
        self.app=app
        self.name=name
        self.filenameprefix=filenameprefix
        self.text=text
        self.a=a
        self.sparql=sparql
        self.endpointConf=endpointConf
        self.queryHideShow=Collapsible(name,a=a)
        self.queryHideShow.btn.classes+="btn-sm col-3"
        self.queryDiv=jp.Div(a=self.queryHideShow.body)
        self.queryBar=jp.Div(a=a,classes="row",name=f"{self.name}QuerBar")
        self.queryTryIt=jp.Div(a=self.queryBar,classes="col-1")
        self.downloadFormat="excel"
        pass
    
    def generateDownloadFromLod(self,lod) -> str:
        """
        generate a download from the given List of Dicts
        
        Args:
            lod(list): the list of Dicts
        """  
        # prepare static are of webserver to allow uploading files
        static_dir = os.path.dirname(os.path.realpath(__file__))
        qres_dir = f"{static_dir}/qres"
        
        os.makedirs(qres_dir, exist_ok=True)
        if self.downloadFormat in ["excel","ods","csv"]:
            # convert qres to requested format
            spreadsheetFormat=SpreadSheetType[self.downloadFormat.upper()]
            spreadsheet = SpreadSheet.create(spreadsheetFormat, self.filenameprefix)        
            filename = f"{self.filenameprefix}{spreadsheet.FILE_TYPE}"
            spreadsheet.addTable(name=self.name, lod=lod)
            spreadsheet.saveToFile(dir_name=qres_dir, fileName=filename)
        else:
            # tabulate 
            tablefmt=self.downloadFormat
            if self.downloadFormat=="json":
                tableResult=json.dumps(lod)
            else:
                tableResult=tabulate(lod,headers="keys",tablefmt=tablefmt)
            filename= f"{self.filenameprefix}.{tablefmt}"
            filepath = f"{qres_dir}/{filename}"
            print(tableResult,  file=open(filepath, 'w'))
        return filename
    
    async def onChangeDownloadFormat(self,msg:dict):
        '''
        handle the download format change
        '''
        self.downloadFormat = msg.value
    
    async def onDownloadButtonClick(self,_msg):
        '''
        handle the clicking of the download button
        '''
        try:
            alert = Alert(a=self.queryBar, text=f"Query {self.name} for {self.text} started ... please wait a few seconds")
            await self.app.wp.update()
            query = getattr(self, "sparqlQuery")
            if isinstance(query, Query):
                lod = self.sparql.queryAsListOfDicts(query.query)
                filename = self.generateDownloadFromLod(lod)
                setattr(alert, "text", "Download:")
                jp.A(text=f"{filename}",
                      classes="",
                      a=alert,
                      href=f"/static/qres/{filename}",
                      download=filename,
                      disabled=True)
        except (BaseException,HTTPError) as ex:
            self.app.handleException(ex)
        await self.app.wp.update()
    
    def showDownload(self):
        if getattr(self, "downloadButton", None) is None:
            self.downloadButton = IconButton(iconName="download",
                                                classes="btn btn-primary btn-sm col-1",
                                                a=self.queryBar,
                                                click=self.onDownloadButtonClick,
                                                disabled=False)
            self.selectContainer=jp.Div(a=self.queryBar,classes="col-3")
            self.downloadFormatSelect = self.app.createSelect("format",
                                                              value=self.downloadFormat,
                                                              change=self.onChangeDownloadFormat,
                                                              a=self.selectContainer)
            for downloadFormat in ["csv","excel","github","html","json","latex","mediawiki","ods"]:
                self.downloadFormatSelect.add(jp.Option(value=downloadFormat,text=downloadFormat))


    def showSyntaxHighlightedQuery(self,sparqlQuery,withDownload:bool=True):
        '''
        show a syntax highlighted Query

        sparqQuery(str): the query to show
        queryDiv(jp.Div): the div to use for displaying
        queryTryIt(jp.Div): the div for the tryIt button
        '''
        self.sparqlQuery=sparqlQuery
        if withDownload:
            self.showDownload()
        qs=QuerySyntaxHighlight(sparqlQuery)
        queryHigh=qs.highlight()
        tryItUrlEncoded=sparqlQuery.getTryItUrl(baseurl=self.endpointConf.website,database=self.endpointConf.database)
        self.queryDiv.inner_html=queryHigh
        # clear div for try It
        self.queryTryIt.delete_components()
        self.tryItLink=jp.Link(href=tryItUrlEncoded,text="try it!",title="try out with wikidata query service",a=self.queryTryIt,target="_blank")
   
