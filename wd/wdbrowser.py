'''
Created on 2022-07-24

@author: wf
'''
import asyncio
import concurrent.futures
import collections
import html
import logging
import sys
import time
import typing

import justpy as jp
from jpwidgets.jpTable import Table, TableRow
from jpwidgets.bt5widgets import App,Link, ProgressBar
from SPARQLWrapper.SPARQLExceptions import EndPointInternalError

import onlinespreadsheet.version as version
from spreadsheet.spreadsheet import SpreadSheetType
from lodstorage.query import Query,EndpointManager
from lodstorage.trulytabular import TrulyTabular, WikidataProperty
from onlinespreadsheet.pareto import Pareto
from wd.wdsearch import WikidataSearch
from wd.querydisplay import QueryDisplay
from urllib.error import HTTPError

class PropertySelection():
    '''
    select properties
    '''
    aggregates=["min","max","avg","sample","list","count"]

    def __init__(self, inputList, total: int, paretoLevels: typing.Dict[int, Pareto], minFrequency: float):
        '''
           Constructor

        Args:
            propertyList(list): the list of properties to show
            total(int): total number of properties
            paretolLevels: a dict of paretoLevels with the key corresponding to the level
            minFrequency(float): the minimum frequency of the properties to select in percent
        '''
        self.propertyMap: typing.Dict[str, dict] = dict()
        self.headerMap={}
        self.propertyList=[]
        self.total=total
        self.paretoLevels=paretoLevels
        self.minFrequency=minFrequency
        for record in inputList:
            ratio=int(record["count"])/self.total
            level=self.getParetoLevel(ratio)
            record["%"]=f'{ratio*100:.1f}'
            record["pareto"]=level
            #if record["pareto"]<=paretoLimit:
            orecord=collections.OrderedDict(record.copy())
            self.propertyList.append(orecord)
        pass

    def getParetoLevel(self,ratio):
        level=0
        for pareto in reversed(self.paretoLevels.values()):
            if pareto.ratioInLevel(ratio):
                level=pareto.level
        return level

    def getInfoHeaderColumn(self, col: str) -> str:
        href=f"https://wiki.bitplan.com/index.php/Truly_Tabular_RDF/Info#{col}"
        info=f"{col}<br><a href='{href}'style='color:white' target='_blank'>ⓘ</a>"
        return info
    
    def hasMinFrequency(self, record: dict) -> bool:
        """
        Check if the frequency of the given property record is greater than the minimal frequency

        Returns:
            True if property frequency is greater or equal than the minFrequency. Otherwise False
        """
        ok = float(record.get("%", 0)) >= self.minFrequency
        return ok
    
    def select(self) -> typing.List[typing.Tuple[str, dict]]:
        """
        select all properties that fulfill hasMinFrequency

        Returns:
            list of all selected properties as tuple list consisting of property id and record
        """
        selected=[]
        for propertyId, propRecord in self.propertyMap.items():
            if self.hasMinFrequency(propRecord):
                selected.append((propertyId, propRecord))
        return selected

    def prepare(self):
        '''
        prepare the propertyList

        Args:
            total(int): the total number of records
            paretoLevels(list): the pareto Levels to use
        '''

        self.headerMap={}
        cols=["#","%","pareto","property","propertyId","type","1","maxf","nt","nt%","?f","?ex","✔"]
        cols.extend(PropertySelection.aggregates)
        cols.extend(["ignore","label","select"])
        for col in cols:
            self.headerMap[col]=self.getInfoHeaderColumn(col)
        for i,prop in enumerate(self.propertyList):
            # add index as first column
            prop["#"]=i+1
            prop.move_to_end('#', last=False)
            propLabel=prop.pop("propLabel")
            url=prop.pop("prop")
            itemId=url.replace("http://www.wikidata.org/entity/","")
            prop["propertyId"]=itemId
            prop["property"]=Link.create(url, propLabel)
            prop["type"]=prop.pop("wbType").replace("http://wikiba.se/ontology#","")
            prop["1"]=""
            prop["maxf"]=""
            prop["nt"]=""
            prop["nt%"]=""
            prop["?f"]=""
            prop["?ex"]=""
            prop["✔"]=""
            # workaround count being first element
            prop["count"]=prop.pop("count")
            for col in PropertySelection.aggregates:
                prop[col]=""
            prop["ignore"]=""
            prop["label"]=""
            prop["select"]=""

            self.propertyMap[itemId]=prop
             
class WikidataItemSearch():
    '''
    wikidata item search with selector or a combobox
    '''
    
    def __init__(self,app,a1,a2,a3,useComboBox:bool=False,keyStrokeTime:float=0.65):
        '''
        constructor
        
        Args:
            a1(jp.HtmlComponent): ancestor component for input
            a2(jp.HtmlComponent): ancestor component for select
            a3(jp.HtmlComponent): ancestor component for Link result
            useComboBox(bool): if True use a combobox
            keyStrokeTime(float): minimum time between keystrokes to start Wikidata Ajax Search
        '''
        self.app=app
        self.wdSearch=WikidataSearch(self.app.language)
        self.keyStrokeTime=keyStrokeTime
        self.previousKeyStrokeTime=None
        self.useComboBox=useComboBox
        if useComboBox:
            self.handleSearchResult=self.handleSearchResult4ComboBox
            self.itemInput=self.app.createComboBox(labelText="Wikidata item", a=a1,placeholder='Please type here to search ...',value=self.app.itemQid,change=self.onItemChange)
        else:
            self.handleSearchResult=self.handleSearchResult4Select
            self.itemInput=self.app.createInput(labelText="Wikidata item", a=a1, placeholder='Please type here to search ...',value=self.app.itemQid,change=self.onItemChange)
            self.itemSelect=jp.Select(classes="form-select",a=a2,change=self.onItemSelect)
        # on enter use the currently selected item 
        self.itemInput.on('change', self.onItemInput)
        self.itemLinkDiv=jp.Div(a=a3,classes="h5")
    
    def updateItemLink(self,wdItem):
        '''
        update the link
        ''' 
        itemText=wdItem.asText()
        self.itemLinkDiv.inner_html=Link.create(f"{wdItem.url}",itemText, wdItem.description, target="_blank")
         
    def onItemChange(self,msg:dict):
        '''
        react on changes in the item input
        '''
        try:
            now=time.time()
            if self.previousKeyStrokeTime is not None:
                elapsed=now-self.previousKeyStrokeTime
                if elapsed>=self.keyStrokeTime:
                    searchFor=msg.value
                    self.app.showFeedback(f"searching wikidata for {searchFor}...")
                    wdSearchResult=self.wdSearch.searchOptions(searchFor)
                    self.handleSearchResult(wdSearchResult)
            self.previousKeyStrokeTime=now
        except BaseException as ex:
            self.app.handleException(ex)
            
    def handleSearchResult4Select(self,searchResult):
        # remove current Selection
        firstQid=None
        for qid,itemLabel,desc in searchResult:
            if firstQid is None:
                self.itemSelect.delete_components()
                firstQid=qid
            text=f"{itemLabel} ({qid}) {desc}"
            self.itemSelect.add(jp.Option(value=qid,text=text))
        if firstQid is not None:
            self.itemSelect.value=firstQid
            
    def handleSearchResult4ComboBox(self,searchResult):
        firstQid=None
        for qid,itemLabel,desc in searchResult:
            if firstQid is None:
                self.itemInput.dataList.clear()
                firstQid=qid
            text=f"{itemLabel} ({qid}) {desc}"
            self.itemInput.dataList.addOption(value=qid,text=text)
            
    async def onItemInput(self,msg):
        '''
        react on item being selected via enter key in input
        '''
        try:
            if self.useComboBox:
                itemQid=msg.value
            else:
                itemQid=self.itemSelect.value
            await self.app.selectItem(itemQid)
        except BaseException as ex:
            self.app.handleException(ex)
            
    async def onItemSelect(self,msg):
        '''
        react on item being selected via Select control
        '''
        try:
            await self.selectItem(msg.value)
        except Exception as ex:
            self.app.handleException(ex)

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
        self.addMenuLink(text='Settings',icon='cog',href="/settings")
        self.addMenuLink(text='github',icon='github', href="https://github.com/WolfgangFahl/pyLoDStorage/issues/79")
        self.addMenuLink(text='Documentation',icon='file-document',href="https://wiki.bitplan.com/index.php/Truly_Tabular_RDF")
        self.endpoints=EndpointManager.getEndpoints(lang="sparql")
        self.endpointName=None
        self.language="en"
        self.listSeparator="|"
        self.paretoLevel=1
        self.minPropertyFrequency=20
        self.withSubclasses=False
        self.subclassPredicate="wdt:P31"
        self.paretoLevels={}
        for level in range(1,10):
            pareto=Pareto(level)
            self.paretoLevels[level]=pareto
        self.ttTable=None
        # Routes
        jp.Route('/settings',self.settings)
        #jp.Route('/itemsearch',self.itemsearch)
        jp.Route('/tt/{qid}',self.ttcontent)
        self.starttime=time.time()
        self.wdProperty=WikidataProperty("P31")

    def getParser(self):
        '''
        get my parser
        '''
        parser=super().getParser()
        parser.add_argument('-en', '--endpointName', default="wikidata", help=f"Name of the endpoint to use for queries. Available by default: {EndpointManager.getEndpointNames()}")
        return parser

    def showFeedback(self,html):
        self.feedback.inner_html=html

    def isSelected(self,row:TableRow,column:str)->bool:
        '''
        check whether the checkbox at the column of the given row is selected

        Args:
            row(TableRow): the table row
            columnn(str): the key of the column
        Returns:
            True if the checkbox in that column is selected
        '''
        # TODO refactor to row
        cell=row.getCell(column)
        checkbox=cell.getControl()
        return checkbox.checked

    def getPropertyIdMap(self):
        '''
        get the map of selected propery ids with generation hints

        Returns:
            dict: a dict of list
        '''
        idMap={}
        cols=PropertySelection.aggregates.copy()
        cols.extend(["label","ignore"])
        for row in self.ttTable.rows:
            if self.isSelected(row,"select"):
                propertyId=row.getCellValue("propertyId")
                genList=[]
                for col in cols:
                    if self.isSelected(row,col):
                        genList.append(col)
                idMap[propertyId]=genList
        return idMap

    def createQueryDisplay(self,name,a,wdItem)->QueryDisplay:
        '''
        Args:
            name(str): the name of the query
            a(jp.Component): the ancestor
            wdItem(WikiDataItem): the wikidata item referenced

        Returns:
            QueryDisplay: the created QueryDisplay
        '''
        filenameprefix=f"{wdItem.qid}{name}"
        qd=QueryDisplay(
                app=self,
                name=name,
                a=a,
                filenameprefix=filenameprefix,
                text=wdItem.asText(),
                sparql=self.tt.sparql,
                endpointConf=self.endpointConf)
        return qd

    def createTrulyTabular(self,itemQid,propertyIds=[]):
        '''
        create a Truly Tabular configuration for my configure endpoint and the given itemQid and
        propertyIds

        Args:
            itemQid(str): e.g. Q5 human
            propertyIds(list): list of property Ids (if any) such as P17 country
        '''
        tt = TrulyTabular(
                itemQid=itemQid,
                propertyIds=propertyIds,
                subclassPredicate=self.subclassPredicate,
                endpointConf=self.endpointConf,
                debug=self.debug)
        return tt

    def generateQuery(self):
        '''
        generate and show the query
        '''
        self.clearErrors()
        propertyIdMap=self.getPropertyIdMap()
        tt=self.createTrulyTabular(itemQid=self.itemQid,propertyIds=list(propertyIdMap.keys()))
        if self.naiveQueryDisplay is None:
            self.naiveQueryDisplay=self.createQueryDisplay("naive Query",a=self.colB3,wdItem=tt.item)
        if self.aggregateQueryDisplay is None:
            self.aggregateQueryDisplay=self.createQueryDisplay("aggregate Query",a=self.colC3,wdItem=tt.item)
        sparqlQuery=tt.generateSparqlQuery(genMap=propertyIdMap,naive=True,lang=self.language,listSeparator=self.listSeparator)
        naiveSparqlQuery=Query(name="naive SPARQL Query",query=sparqlQuery)
        self.naiveQueryDisplay.showSyntaxHighlightedQuery(naiveSparqlQuery)
        sparqlQuery=tt.generateSparqlQuery(genMap=propertyIdMap,naive=False,lang=self.language,listSeparator=self.listSeparator)
        self.aggregateSparqlQuery=Query(name="aggregate SPARQL Query",query=sparqlQuery)
        self.aggregateQueryDisplay.showSyntaxHighlightedQuery(self.aggregateSparqlQuery)
        self.showFeedback("SPARQL queries generated")
        pass

    def setEndPoint(self,endpointName:str):
        '''
        set an endpoint
        '''
        self.endpointName=endpointName
        # get the endpoint Configuration
        self.endpointConf=self.endpoints.get(endpointName)
        self.addMenuLink(text='Endpoint',icon='web',href=self.endpointConf.website,target="_blank")

    async def onChangeEndpoint(self,msg:dict):
        '''
        handle selection of a different endpoint

        Args:
            msg(dict): the justpy message
        '''
        try:
            self.setEndPoint(msg.value)
            self.showFeedback(f"endpoint {self.endpointName} ({self.endpointConf.database}) selected")
        except BaseException as ex:
            self.handleException(ex)
        await self.wp.update()
        
    async def onSubclassChange(self,msg):
        self.withSubclasses=msg["checked"]
        self.subclassPredicate="wdt:P279*/wdt:P31*" if self.withSubclasses else "wdt:P31"

    def wikiTrulyTabularPropertyStats(self,itemId:str,propertyId:str):
        '''
        get the truly tabular property statistics

        Args:
            itemId(str): the Wikidata item identifier
            propertyId(str): the property id
        '''
        try:
            tt=self.createTrulyTabular(itemId,propertyIds=[propertyId])
            statsRow=next(tt.genPropertyStatistics())
            for key in ["queryf","queryex"]:
                queryText=statsRow[key]
                sparql=f"# This query was generated by Truly Tabular\n{queryText}"
                query=Query(name=key,query=sparql)
                tryItUrlEncoded=query.getTryItUrl(baseurl=self.endpointConf.website,database=self.endpointConf.database)
                tryItLink=Link.create(url=tryItUrlEncoded,text="try it!",tooltip=f"try out with {self.endpointConf.name}",target="_blank")
                statsRow[f"{key}TryIt"]=tryItLink
            return statsRow
        except (BaseException,HTTPError) as ex:
            self.handleException(ex)
            return None

    async def trulyTabularAnalysis(self,tt):
        """
        perform the truly tabular analysis

        Args:
            tt(TrulyTabular): the truly tabular entry
        """
        if getattr(self, "propertySelection", None) is None:
            self.showFeedback("no property Selection available for truly tabular analysis")
            await self.wp.update()
            return
        selectedItems = self.propertySelection.select()
        propertyCount = len(selectedItems)
        # start property tabular analysis
        analysisTasks = []
        completedTasks = 0
        executor = concurrent.futures.ThreadPoolExecutor(5)
        for _i, (propertyId,propRecord) in enumerate(selectedItems):
            prop = propRecord.get("property")
            future = executor.submit(self.wikiTrulyTabularPropertyStatsAndUpdateTable, tt, propertyId)
            analysisTasks.append((future, propertyId, prop))
        while len(analysisTasks) > 0:
            done = []
            _pending = []
            for future, propertyId, prop in analysisTasks:
                if future.done():
                    done.append((future, propertyId, prop))
                else:
                    _pending.append((future, propertyId, prop))
            analysisTasks = _pending
            if self.debug:
                print("Completed:", len(done), "Pending:", len(_pending))
            completedTasks += len(done)
            props = ",".join([prop for _, prop, _ in done])
            self.showFeedback(f"{completedTasks }/{propertyCount}: querying statistics - (completed statistics for {props})...")
            self.progressBar.updateProgress(int(completedTasks * 100 / propertyCount))
            await self.wp.update()
            await asyncio.sleep(2.0)
        self.showFeedback("")
        self.progressBar.updateProgress(0)
        if self.generateQueryButton is None:
            self.generateQueryButton = jp.Button(
                    text="Generate SPARQL query",
                    classes="btn btn-primary",
                    a=self.colD1,
                    click=self.onGenerateQueryButtonClick,
                    disabled=True)
        if self.paretoSelect is None:
            self.paretoSelect=self.createParetoSelect(a=self.colE1,ai=self.colE2)
        self.generateQueryButton.disabled=False

    def wikiTrulyTabularPropertyStatsAndUpdateTable(self, tt, propertyId):
        """
        Executes wikiTrulyTabularPropertyStats with the given parameters and updates the table with the result

        Args:
            tt(TrulyTabular): the truly tabular entry
            propertyId: id of the property to analyze
        """
        statsRow = self.wikiTrulyTabularPropertyStats(tt.itemQid, propertyId)
        if statsRow:
            statsRow["✔"] = "✔"
            for column, statsColumn in [("1", "1"), ("maxf", "maxf"), ("nt", "non tabular"), ("nt%", "non tabular%"),
                                        ("?f", "queryfTryIt"), ("?ex", "queryexTryIt"), ("✔", "✔")]:
                if statsColumn in statsRow:
                    value = statsRow[statsColumn]
                    self.ttTable.updateCell(propertyId, column, value)

#{
#  'property': 'instance of',
#  'max': 9,
#  'queryf': 'SELECT ?count (COUNT(?count) AS ?frequency) WHERE {{\n\n# Count all country (Q6256)☞distinct territorial body or political entity→ https://www.wikidata.org/wiki/Q6256 items\n# with the given instance of(P31) https://www.wikidata.org/wiki/Property:P31 \nSELECT ?item ?itemLabel (COUNT (?value) AS ?count)\nWHERE\n{\n  # instance of country\n  ?item wdt:P31 wd:Q6256.\n  ?item rdfs:label ?itemLabel.\n  filter (lang(?itemLabel) = "en").\n  # instance of\n  ?item wdt:P31 ?value.\n} GROUP by ?item ?itemLabel\n\n}}\nGROUP BY ?count\nORDER BY DESC (?frequency)',
#  'queryex': '\n# Count all country (Q6256)☞distinct territorial body or political entity→ https://www.wikidata.org/wiki/Q6256 items\n# with the given instance of(P31) https://www.wikidata.org/wiki/Property:P31 \nSELECT ?item ?itemLabel (COUNT (?value) AS ?count)\nWHERE\n{\n  # instance of country\n  ?item wdt:P31 wd:Q6256.\n  ?item rdfs:label ?itemLabel.\n  filter (lang(?itemLabel) = "en").\n  # instance of\n  ?item wdt:P31 ?value.\n} GROUP by ?item ?itemLabel\n\nHAVING (COUNT (?value) > 1)\nORDER BY DESC(?count)',
#  'total': 184,
#  'total%': 99.5,
#  'non tabular': 184,
#  'non tabular%': 100.0,
#  'queryfTryIt': "<a href='https://query.wikidata.org//#%23%20This%20query%20was%20generated%20by%20Truly%20Tabular%0ASELECT%20%3Fcount%20%28COUNT%28%3Fcount%29%20AS%20%3Ffrequency%29%20WHERE%20%7B%7B%0A%0A%23%20Count%20all%20country%20%28Q6256%29%E2%98%9Edistinct%20territorial%20body%20or%20political%20entity%E2%86%92%20https%3A//www.wikidata.org/wiki/Q6256%20items%0A%23%20with%20the%20given%20instance%20of%28P31%29%20https%3A//www.wikidata.org/wiki/Property%3AP31%20%0ASELECT%20%3Fitem%20%3FitemLabel%20%28COUNT%20%28%3Fvalue%29%20AS%20%3Fcount%29%0AWHERE%0A%7B%0A%20%20%23%20instance%20of%20country%0A%20%20%3Fitem%20wdt%3AP31%20wd%3AQ6256.%0A%20%20%3Fitem%20rdfs%3Alabel%20%3FitemLabel.%0A%20%20filter%20%28lang%28%3FitemLabel%29%20%3D%20%22en%22%29.%0A%20%20%23%20instance%20of%0A%20%20%3Fitem%20wdt%3AP31%20%3Fvalue.%0A%7D%20GROUP%20by%20%3Fitem%20%3FitemLabel%0A%0A%7D%7D%0AGROUP%20BY%20%3Fcount%0AORDER%20BY%20DESC%20%28%3Ffrequency%29 title='try out with wikidata query service''>try it!</a>",
#  'queryexTryIt': "<a href='https://query.wikidata.org//#%23%20This%20query%20was%20generated%20by%20Truly%20Tabular%0A%0A%23%20Count%20all%20country%20%28Q6256%29%E2%98%9Edistinct%20territorial%20body%20or%20political%20entity%E2%86%92%20https%3A//www.wikidata.org/wiki/Q6256%20items%0A%23%20with%20the%20given%20instance%20of%28P31%29%20https%3A//www.wikidata.org/wiki/Property%3AP31%20%0ASELECT%20%3Fitem%20%3FitemLabel%20%28COUNT%20%28%3Fvalue%29%20AS%20%3Fcount%29%0AWHERE%0A%7B%0A%20%20%23%20instance%20of%20country%0A%20%20%3Fitem%20wdt%3AP31%20wd%3AQ6256.%0A%20%20%3Fitem%20rdfs%3Alabel%20%3FitemLabel.%0A%20%20filter%20%28lang%28%3FitemLabel%29%20%3D%20%22en%22%29.%0A%20%20%23%20instance%20of%0A%20%20%3Fitem%20wdt%3AP31%20%3Fvalue.%0A%7D%20GROUP%20by%20%3Fitem%20%3FitemLabel%0A%0AHAVING%20%28COUNT%20%28%3Fvalue%29%20%3E%201%29%0AORDER%20BY%20DESC%28%3Fcount%29 title='try out with wikidata query service''>try it!</a>"
#}
    async def getMostFrequentlyUsedProperties(self, tt: TrulyTabular):
        '''
        get the most frequently used properties for the given truly tabular

        Args:
            tt(TrulyTabular): the truly tabular Wikidata Item Analysis
        '''
        total=self.ttcount
        pareto=self.paretoLevels[self.paretoLevel]
        if total is not None:
            minCount = round(total/pareto.oneOutOf)
        else:
            minCount = 0
        self.ttquery=tt.mostFrequentPropertiesQuery(minCount=minCount)
        if self.propertyQueryDisplay is None:
            self.propertyQueryDisplay=self.createQueryDisplay("property Query",a=self.colA4,wdItem=tt.item)
        self.propertyQueryDisplay.showSyntaxHighlightedQuery(self.ttquery)
        await self.wp.update()

    async def noAction(self,_msg):
        '''
        placeholder action which has no effect
        '''
        pass

    def addSelectionColumn(self,table:jp.Table,column:str,checkedCondition:callable,onInput=None):
        '''
        add a selection column to the given table

        Args:
            table(jp.Table): the table
            column(the column): the column
            checkedCondition(callable): set checked depending on the record content
            onInput(callable): an input handler - default is noAction
        '''
        if onInput is None:
            onInput=self.noAction
        for row in table.rows:
            cell=row.cellsMap[column]
            checked=checkedCondition(row.record)
            checkbox=jp.Input(type='checkbox',a=cell,checked=checked,input=onInput)
            cell.setControl(checkbox)

    async def getCountQuery(self, tt: TrulyTabular):
        """
        Run property count query and display progress and result
        Args:
            tt: the truly tabular entry
        """
        self.showFeedback(f"running count query for {str(self.tt)} ...")
        await self.wp.update()
        self.ttcount,countQuery=tt.count()
        # is ttcount mission critical? then activate the error check (if I can not count it how can I query for all used properties)
        # if tt.error is not None and self.isTimeoutException(tt.error):
        #     if self.debug:
        #         print("Query timeout: Could not successfully execute the count query")
        #     raise Exception("Query timeout of the count query - Try using a different endpoint")
        self.countDiv.text=f"{self.ttcount} instances found"
        if self.countQueryDisplay is None:
            self.countQueryDisplay=self.createQueryDisplay("count Query",a=self.colA4,wdItem=tt.item)
        countSparqlQuery=Query(name="count Query",query=countQuery)
        self.countQueryDisplay.showSyntaxHighlightedQuery(countSparqlQuery)
        await self.wp.update()

    @staticmethod
    def isTimeoutException(ex: EndPointInternalError):
        """
        Checks if the given exception is a query timeout exception

        Returns:
            True if the given exception is caused by a query timeout
        """
        check_for = "java.util.concurrent.TimeoutException"
        msg = ex.args[0]
        res = False
        if isinstance(msg, str):
            if check_for in msg:
                res = True
        return res

    async def getPropertiesTable(self, tt: TrulyTabular, ttquery: Query):
        '''
        get the properties table
        Args:
            tt: the truly tabular entry
            ttquery:
        '''
        self.showFeedback(f"running query for most frequently used properties of {str(self.tt)} ...")
        await self.wp.update()
        if self.debug:
            logging.info(ttquery.query)
        try:
            self.propertyList=tt.sparql.queryAsListOfDicts(ttquery.query)
        except EndPointInternalError as ex:
            if self.isTimeoutException(ex):
                raise Exception("Query timeout of the property table query")
        self.propertySelection = PropertySelection(
                self.propertyList,
                total=self.ttcount,
                paretoLevels=self.paretoLevels,
                minFrequency=self.minPropertyFrequency)
        self.propertySelection.prepare()
        self.ttTable=Table(a=self.colF1,
                           lod=self.propertySelection.propertyList,
                           headerMap=self.propertySelection.headerMap,
                           primaryKey='propertyId',
                           allowInput=False)
        for aggregate in PropertySelection.aggregates:
            checked=False #aggregate in ["sample","count","list"]
            self.addSelectionColumn(self.ttTable, aggregate, lambda _record: checked)
        self.addSelectionColumn(
                self.ttTable,
                "ignore",
                lambda record: self.propertySelection.hasMinFrequency(record),
                self.onIgnoreSelect)
        self.addSelectionColumn(
                self.ttTable,
                "label",
                lambda record: record["type"] == "WikibaseItem" and self.propertySelection.hasMinFrequency(record))
        self.addSelectionColumn(
                self.ttTable,
                "select",
                lambda record: self.propertySelection.hasMinFrequency(record) and record["propertyId"] != "P31")
        self.showFeedback(f"table for propertySelection of {str(self.tt)} created ...")
        await self.wp.update()

    async def selectProperty(self,propertySelection):
        '''
        select a wikidata Property for analysis
        '''
        
    async def selectItem(self, itemId: typing.Union[str, None]):
        """
        select a Wikidata Item for analysis

        Args:
            itemId(str|None): the Wikidata Q - ID of the selected item
        """
        if itemId is None or not itemId:
            return
        try:
            self.clearErrors()
            self.itemQid=itemId
            self.propertyList=None
            # delete the Table
            if self.ttTable is not None:
                try:
                    self.ttTable.a.remove_component(self.ttTable)
                except BaseException as ex:
                    pass
                self.ttTable=None
                if self.generateQueryButton is not None:
                    self.generateQueryButton.disabled=True
            self.showFeedback(f"item {itemId} selected")
            await self.wp.update()
            # create the Truly Tabular Analysis
            self.tt=self.createTrulyTabular(itemId)
            self.showFeedback(f"trulytabular {str(self.tt)} initiated")
            self.wdItemSearch.updateItemLink(self.tt.item)
            await self.wp.update()
            await self.getCountQuery(self.tt),  #defines: ttcount
            await self.getMostFrequentlyUsedProperties(self.tt),  #uses: ttcount, |defines: ttquery,propertyQueryDisplay
            await self.getPropertiesTable(self.tt, self.ttquery), #uses: ttquery  | defines: propertyList, propertySelection, ttTable
            await self.trulyTabularAnalysis(self.tt) #uses: propertySelection
        except BaseException as ex:
            self.handleException(ex)

    async def onGenerateQueryButtonClick(self,_msg):
        try:
            self.showFeedback(f"generating SPARQL query for {str(self.tt)}")
            self.generateQuery()
        except BaseException as ex:
            self.handleException(ex)
        await self.wp.update()
        
    async def onPropertySelect(self,msg):
        await self.selectProperty(msg.value)

    async def onIgnoreSelect(self,msg):
        try:
            target=msg["target"]
            cell=target.a
            row=cell.row
            for col in PropertySelection.aggregates:
                colCell=row.getCell(col)
                checkbox=colCell.getControl()
                checkbox.checked=False
        except BaseException as ex:
            self.handleException(ex)

    async def onChangeLanguage(self,msg):
        '''
        react on language being changed via Select control
        '''
        self.language=msg.value
        self.wdSearch.language=self.language

    async def onChangeListSeparator(self,msg):
        self.listSeparator=msg.value

    async def onParetoSelect(self,msg):
        '''
        change pareto selection
        '''
        try:
            self.paretoLevel=int(msg.value)
            pareto=self.paretoLevels[self.paretoLevel]
            self.minPropertyFrequency=pareto.asPercent()
            minPropertyFrequencyStr=f"{self.minPropertyFrequency:.2f}"
            self.minPropertyFrequencyInput.value=minPropertyFrequencyStr
            self.showFeedback(f"pareto level {self.paretoLevel} (>={minPropertyFrequencyStr}% )selected")
            if self.generateQueryButton is not None:
                await self.selectItem(self.itemQid)
        except Exception as ex:
            self.handleException(ex)
            
    async def onMinPropertyFrequencyChange(self,msg):
        try:
            changed=False
            try:
                minfreq=float(msg.value)
                self.minPropertyFrequency=minfreq
                self.showFeedback(f"minimum property frequency {minfreq} selected")
                changed=True
            except Exception as _floatConversionEx:
                pass
            if changed and self.generateQueryButton is not None:
                await self.selectItem(self.itemQid)
        except Exception as ex:
            self.handleException(ex)

    def createParetoSelect(self,a,ai):
        '''
        create the pareto select

        Args:
            a(object): the parent component

        Returns:
            jp.Select
        '''
        pselect = self.createSelect("Pareto",str(self.paretoLevel),change=self.onParetoSelect,a=a)
        for pareto in self.paretoLevels.values():
            option = jp.Option(value=pareto.level, text=pareto.asText(long=True))
            pselect.add(option)
        self.minPropertyFrequencyInput = self.createInput(
                labelText="min%",
                placeholder="e.g. 90",
                value=str(self.minPropertyFrequency),
                change=self.onMinPropertyFrequencyChange,
                a=ai,
                size=10)
        return pselect

    def setupRowsAndCols(self):
        # select endpoint
        head="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">
<link rel="stylesheet" href="/static/css/pygments.css">
"""
        if self.endpointName is None:
            self.setEndPoint(self.args.endpointName)
        self.itemQid=""
        # extend the justpy Webpage with the given head parameters
        self.wp=self.getWp(head)

        # setup Bootstrap5 rows and columns

        rowA=jp.Div(classes="row",a=self.contentbox)
        self.colA1=jp.Div(classes="col-3",a=rowA)
        self.colA2=jp.Div(classes="col-3",a=rowA)
        #self.colA3=jp.Div(classes="col-2",a=rowA)
        self.colA4=jp.Div(classes="col-6",a=rowA)

        self.rowB=jp.Div(classes="row",a=self.contentbox)
        self.colB1=jp.Div(classes="col-3",a=self.rowB)
        self.colB2=jp.Div(classes="col-3",a=self.rowB)
        self.colB3=jp.Div(classes="col-6",a=self.rowB)

        self.rowC=jp.Div(classes="row",a=self.contentbox)
        self.colC1=jp.Div(classes="col-3",a=self.rowC)
        self.colC2=jp.Div(classes="col-3",a=self.rowC)
        self.colC3=jp.Div(classes="col-6",a=self.rowC)

        self.rowD=jp.Div(classes="row",a=self.contentbox)
        self.colD1=jp.Div(classes="col-4",a=self.rowD)
        self.colD2=jp.Div(classes="col-2",a=self.rowD)
        self.colD3=jp.Div(classes="col-2",a=self.rowD)
        self.colD4=jp.Div(classes="col-2",a=self.rowD)

        self.rowE=jp.Div(classes="row",a=self.contentbox)
        self.colE1=jp.Div(classes="col-3",a=self.rowE)
        self.colE2=jp.Div(classes="col-3",a=self.rowE)
        
        self.rowF=jp.Div(classes="row",a=self.contentbox)
        self.colF1=jp.Div(classes="col-12",a=self.rowF)
        
        # mandatory UI parts
        # progressbar, feedback and errors
        self.progressBar = ProgressBar(a=self.rowD)
        self.feedback=jp.Div(a=self.rowD)
        self.errors=jp.Span(a=self.rowD,style='color:red')
        self.countQueryDisplay=None
        self.propertyQueryDisplay=None
        self.naiveQueryDisplay=None
        self.aggregateQueryDisplay=None
        self.generateQueryButton=None
        self.paretoSelect=None
        self.wdProperty=WikidataProperty("P31")
        self.downloadFormat:SpreadSheetType = SpreadSheetType.EXCEL
        
    async def itemsearch(self):
        '''
        try combobox itemsearch
        '''
        self.setupRowsAndCols()
        self.wdItemSearch=WikidataItemSearch(self,self.colA1,self.colA2,self.colB1,useComboBox=True)
        return self.wp

    async def settings(self):
        '''
        settings
        '''
        self.setupRowsAndCols()
        self.languageSelect=self.createSelect("Language","en",a=self.colC1,change=self.onChangeLanguage)
        for language in self.getLanguages():
            lang=language[0]
            desc=language[1]
            desc=html.unescape(desc)
            self.languageSelect.add(jp.Option(value=lang,text=desc))
        self.endpointSelect=self.createSelect("Endpoint", self.endpointName, a=self.colC1,change=self.onChangeEndpoint)
        for endpointName in self.endpoints:
            self.endpointSelect.add(jp.Option(value=endpointName, text=endpointName))
        self.listSeparatorSelect = self.createSelect(
                labelText="List separator",
                value=self.listSeparator,
                a=self.colC1,
                change=self.onChangeListSeparator)
        separatorOptions = [("|", "|"), (",", ","), (";", ";"), (":", ":"), (chr(28), "FS - ASCII(28)"),
                            (chr(29), "GS - ASCII(29)"), (chr(30), "RS - ASCII(30)"), (chr(31), "US - ASCII(31)")]
        for value, text in separatorOptions:
            self.listSeparatorSelect.add(jp.Option(value=value, text=text))
        # pareto selection
        self.paretoSelect=self.createParetoSelect(a=self.colE1,ai=self.colE2)
        return self.wp

    async def ttcontent(self,request) -> jp.WebPage:
        """
        RESTful access
        Args:
            request:

        Returns:
            TrulyTabular Webpage
        """
        qid = request.path_params.get("qid", None)
        content = await self.content()
        await self.wp.update()
        await self.selectItem(qid)
        return content

    async def content(self) -> jp.WebPage:
        '''
        provide the justpy content by adding to the webpage provide by the App
        '''
        self.setupRowsAndCols()
        self.wdItemSearch=WikidataItemSearch(self,a1=self.colA1,a2=self.colA2,a3=self.colB1,useComboBox=True)
        self.subclassCheckbox=self.createCheckbox("subclasses",a=self.colA2,checked=self.withSubclasses,input=self.onSubclassChange)
         
        self.countDiv=jp.Div(a=self.colB2,classes="h5")
        return self.wp

DEBUG = 1
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    wdBrowser=WikiDataBrowser(version.Version)
    sys.exit(wdBrowser.mainInstance())