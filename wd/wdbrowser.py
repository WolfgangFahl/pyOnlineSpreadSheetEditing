'''
Created on 2022-07-24

@author: wf
'''
import asyncio
import concurrent.futures
import collections
import html
import sys
import time
import justpy as jp
from jpwidgets.jpTable import Table, TableRow
from jpwidgets.bt5widgets import App,Alert,Collapsible, ComboBox, Link, ProgressBar
import onlinespreadsheet.version as version
from lodstorage.query import Query,EndpointManager, QuerySyntaxHighlight, Endpoint
from lodstorage.trulytabular import TrulyTabular, WikidataProperty
from onlinespreadsheet.pareto import Pareto
from wd.wdsearch import WikidataSearch
from urllib.error import HTTPError

class PropertySelection():
    '''
    select properties
    '''
    aggregates=["min","max","avg","sample","list","count"]

    def __init__(self,inputList,total:int,paretoLevels:list):
        '''
           Constructor
        
        Args:
            propertyList(list): the list of properties to show
        '''
        self.propertyMap={}
        self.headerMap={}
        self.propertyList=[]
        self.total=total
        self.paretoLevels=paretoLevels
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
        for pareto in reversed(self.paretoLevels):
            if pareto.ratioInLevel(ratio):
                level=pareto.level
        return level

    def getInfoHeaderColumn(self,col):
        href=f"https://wiki.bitplan.com/index.php/Truly_Tabular_RDF/Info#{col}"
        info=f"{col}<br><a href='{href}'style='color:white' target='_blank'>ⓘ</a>"
        return info

    def prepare(self):
        '''
        prepare the propertyList
        
        Args:
            total(int): the total number of records
            paretoLevels(list): the pareto Levels to use
        '''

        self.headerMap={}
        cols=["#","%","pareto","property","propertyId","1","maxf","nt","nt%","?f","?ex","✔"]
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

class QueryDisplay():
    '''
    display queries
    '''

    def __init__(self,name:str,a,endpointConf:Endpoint):
        '''
        Args:
            name(str): the name of the display and query
            a(jp.Component): an ancestor component
            endpointConf(Endpoint): SPARQL endpoint configuration to use
            
        '''
        self.name=name
        self.endpointConf=endpointConf
        self.queryHideShow=Collapsible(name,a=a)
        self.queryHideShow.btn.classes+="btn-sm col-3"
        self.queryDiv=jp.Div(a=self.queryHideShow.body)
        self.queryTryIt=jp.Div(a=a)
        pass

    def showSyntaxHighlightedQuery(self,sparqlQuery):
        '''
        show a syntax highlighted Query
        
        sparqQuery(str): the query to show
        queryDiv(jp.Div): the div to use for displaying
        queryTryIt(jp.Div): the div for the tryIt button
        '''
        qs=QuerySyntaxHighlight(sparqlQuery)
        queryHigh=qs.highlight()
        tryItUrlEncoded=sparqlQuery.getTryItUrl(baseurl=self.endpointConf.website,database=self.endpointConf.database)
        self.queryDiv.inner_html=queryHigh
        # clear div for try It
        self.queryTryIt.delete_components()
        self.tryItLink=jp.Link(href=tryItUrlEncoded,text="try it!",title="try out with wikidata query service",a=self.queryTryIt,target="_blank")


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
        self.wdSearch=WikidataSearch(self.language)
        self.paretoLevel=1
        self.paretoLevels=[]
        for level in range(1,10):
            pareto=Pareto(level)
            self.paretoLevels.append(pareto)
        self.ttTable=None
        jp.Route('/settings',self.settings)
        jp.Route('/tt/{qid}',self.ttcontent)
        self.starttime=time.time()
        self.previousKeyStrokeTime=None
        self.wdProperty=WikidataProperty("P31")

    def getParser(self):
        '''
        get my parser
        '''
        parser=super().getParser()
        parser.add_argument('-en', '--endpointName', default="wikidata", help=f"Name of the endpoint to use for queries. Available by default: {EndpointManager.getEndpointNames()}")
        return parser

    def getLanguages(self):
        # see https://github.com/sahajsk21/Anvesha/blob/master/src/components/topnav.js
        languages= [
                ["ar", "&#1575;&#1604;&#1593;&#1585;&#1576;&#1610;&#1577;"],
                ["arz", "&#1605;&#1589;&#1585;&#1609;"],
                ["ast", "Asturianu"],
                ["az", "Az&#601;rbaycanca"],
                ["azb", "&#1578;&#1734;&#1585;&#1705;&#1580;&#1607;"],
                ["be", "&#1041;&#1077;&#1083;&#1072;&#1088;&#1091;&#1089;&#1082;&#1072;&#1103;"],
                ["bg", "&#1041;&#1098;&#1083;&#1075;&#1072;&#1088;&#1089;&#1082;&#1080;"],
                ["bn", "&#2476;&#2494;&#2434;&#2482;&#2494;"],
                ["ca", "Catal&agrave;"],
                ["ce", "&#1053;&#1086;&#1093;&#1095;&#1080;&#1081;&#1085;"],
                ["ceb", "Sinugboanong Binisaya"],
                ["cs", "&#268;e&scaron;tina"],
                ["cy", "Cymraeg"],
                ["da", "Dansk"],
                ["de", "Deutsch"],
                ["el", "&Epsilon;&lambda;&lambda;&eta;&nu;&iota;&kappa;&#940;"],
                ["en", "English"],
                ["eo", "Esperanto"],
                ["es", "Espa&ntilde;ol"],
                ["et", "Eesti"],
                ["eu", "Euskara"],
                ["fa", "&#1601;&#1575;&#1585;&#1587;&#1740;"],
                ["fi", "Suomi"],
                ["fr", "Fran&ccedil;ais"],
                ["gl", "Galego"],
                ["he", "&#1506;&#1489;&#1512;&#1497;&#1514;"],
                ["hi", "&#2361;&#2367;&#2344;&#2381;&#2342;&#2368;"],
                ["hr", "Hrvatski"],
                ["hu", "Magyar"],
                ["hy", "&#1344;&#1377;&#1397;&#1381;&#1408;&#1381;&#1398;"],
                ["id", "Bahasa Indonesia"],
                ["it", "Italiano"],
                ["ja", "&#26085;&#26412;&#35486;"],
                ["ka", "&#4325;&#4304;&#4320;&#4311;&#4323;&#4314;&#4312;"],
                ["kk", "&#1178;&#1072;&#1079;&#1072;&#1179;&#1096;&#1072; / Qazaq&#351;a / &#1602;&#1575;&#1586;&#1575;&#1602;&#1588;&#1575;"],
                ["ko", "&#54620;&#44397;&#50612;"],
                ["la", "Latina"],
                ["lt", "Lietuvi&#371;"],
                ["lv", "Latvie&scaron;u"],
                ["min", "Bahaso Minangkabau"],
                ["ms", "Bahasa Melayu"],
                ["nan", "B&acirc;n-l&acirc;m-g&uacute; / H&#333;-l&oacute;-o&#275;"],
                ["nb", "Norsk (bokm&aring;l)"],
                ["nl", "Nederlands"],
                ["nn", "Norsk (nynorsk)"],
                ["pl", "Polski"],
                ["pt", "Portugu&ecirc;s"],
                ["ro", "Rom&acirc;n&#259;"],
                ["ru", "&#1056;&#1091;&#1089;&#1089;&#1082;&#1080;&#1081;"],
                ["sh", "Srpskohrvatski / &#1057;&#1088;&#1087;&#1089;&#1082;&#1086;&#1093;&#1088;&#1074;&#1072;&#1090;&#1089;&#1082;&#1080;"],
                ["sk", "Sloven&#269;ina"],
                ["sl", "Sloven&scaron;&#269;ina"],
                ["sr", "&#1057;&#1088;&#1087;&#1089;&#1082;&#1080; / Srpski"],
                ["sv", "Svenska"],
                ["ta", "&#2980;&#2990;&#3007;&#2996;&#3021;"],
                ["tg", "&#1058;&#1086;&#1207;&#1080;&#1082;&#1251;"],
                ["th", "&#3616;&#3634;&#3625;&#3634;&#3652;&#3607;&#3618;"],
                ["tr", "T&uuml;rk&ccedil;e"],
                ["tt", "&#1058;&#1072;&#1090;&#1072;&#1088;&#1095;&#1072; / Tatar&ccedil;a"],
                ["uk", "&#1059;&#1082;&#1088;&#1072;&#1111;&#1085;&#1089;&#1100;&#1082;&#1072;"],
                ["ur", "&#1575;&#1585;&#1583;&#1608;"],
                ["uz", "O&#699;zbekcha / &#1038;&#1079;&#1073;&#1077;&#1082;&#1095;&#1072;"],
                ["vi", "Ti&#7871;ng Vi&#7879;t"],
                ["vo", "Volap&uuml;k"],
                ["war", "Winaray"],
                ["yue", "&#31925;&#35486;"],
                ["zh", "&#20013;&#25991;"],
            ]
        return languages

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

    def createQueryDisplay(self,name,a)->QueryDisplay:
        '''
        Args:
            name(str): the name of the query
            a(jp.Component): the ancestor
            
        Returns:
            QueryDisplay: the created QueryDisplay
        '''
        qd=QueryDisplay(name=name,a=a,endpointConf=self.endpointConf)
        return qd

    def createTrulyTabular(self,itemQid,propertyIds=[]):
        '''
        create a Truly Tabular configuration for my configure endpoint and the given itemQid and
        propertyIds
        
        Args:
            itemQid(str): e.g. Q5 human
            propertyIds(list): list of property Ids (if any) such as P17 country
        '''
        tt=TrulyTabular(itemQid=itemQid,propertyIds=propertyIds,endpointConf=self.endpointConf,debug=self.debug)
        return tt

    def generateQuery(self):
        '''
        generate and show the query
        '''
        propertyIdMap=self.getPropertyIdMap()
        tt=self.createTrulyTabular(itemQid=self.itemQid,propertyIds=list(propertyIdMap.keys()))
        if self.naiveQueryDisplay is None:
            self.naiveQueryDisplay=self.createQueryDisplay("naive Query",a=self.colB3)
        if self.aggregateQueryDisplay is None:
            self.aggregateQueryDisplay=self.createQueryDisplay("aggregate Query",a=self.colC3)
        sparqlQuery=tt.generateSparqlQuery(genMap=propertyIdMap,naive=True,lang=self.language,listSeparator=self.listSeparator)
        naiveSparqlQuery=Query(name="naive SPARQL Query",query=sparqlQuery)
        self.naiveQueryDisplay.showSyntaxHighlightedQuery(naiveSparqlQuery)
        sparqlQuery=tt.generateSparqlQuery(genMap=propertyIdMap,naive=False,lang=self.language,listSeparator=self.listSeparator)
        aggregateSparqlQuery=Query(name="aggregate SPARQL Query",query=sparqlQuery)
        self.aggregateQueryDisplay.showSyntaxHighlightedQuery(aggregateSparqlQuery)
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

    def onItemBoxChange(self,msg:dict):
        searchFor=msg.value
        self.showFeedback(f"searching wikidata for {searchFor}...")
        for qid,itemLabel,desc in self.wdSearch.searchOptions(searchFor):
            text=f"{itemLabel} ({qid}) {desc}"
            self.itemcombo.addOption(text)

    def onItemChange(self,msg:dict):
        '''
        react on changes in the item input
        '''
        try:
            now=time.time()
            if self.previousKeyStrokeTime is not None:
                elapsed=now-self.previousKeyStrokeTime
                if elapsed>0.6:
                    searchFor=msg.value
                    self.showFeedback(f"searching wikidata for {searchFor}...")
                    # remove current Selection
                    firstQid=None
                    for qid,itemLabel,desc in self.wdSearch.searchOptions(searchFor):
                        if firstQid is None:
                            self.itemSelect.delete_components()
                            firstQid=qid
                        text=f"{itemLabel} ({qid}) {desc}"
                        self.itemSelect.add(jp.Option(value=qid,text=text))
                    if firstQid is not None:
                        self.itemSelect.value=firstQid
            self.previousKeyStrokeTime=now
        except BaseException as ex:
            self.handleException(ex)

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
        '''
        perform the truly tabular analysis
        
        Args:
            tt(TrulyTabular): the truly tabular entry
        '''
        if self.propertySelection is None:
            self.showFeedback("no property Selection available for truly tabular analysis")
            await self.wp.update()
            return
        try:
            selectedItems = [(propertyId,propRecord)
                             for propertyId,propRecord in self.propertySelection.propertyMap.items()
                             if propRecord.get("pareto") <= self.paretoLevel]
            propertyCount = len(selectedItems)
            # start property tabular analysis
            analysisTasks = []
            completedTasks = 0
            executor = concurrent.futures.ThreadPoolExecutor(5)
            for i, (propertyId,propRecord) in enumerate(selectedItems):
                prop = propRecord.get("property")
                future = executor.submit(self.wikiTrulyTabularPropertyStatsAndUpdateTable, tt, propertyId)
                analysisTasks.append((future, propertyId, prop))
            while len(analysisTasks) > 0:
                done = [(future, propertyId, prop) for future, propertyId, prop in analysisTasks if future.done()]
                _pending = [(future, propertyId, prop) for future, propertyId, prop in analysisTasks if not future.done()]
                analysisTasks = _pending
                if self.debug:
                    print("Completed:", len(done), "Pending:", len(_pending))
                completedTasks += len(done)
                props = ",".join([prop for _, prop, _ in done])
                self.showFeedback(f"{completedTasks }/{propertyCount}: querying statistics - (completed statistics for {props})...")
                self.progressBar.updateProgress(int((completedTasks) * 100 / propertyCount))
                await self.wp.update()
                await asyncio.sleep(0.5)
            self.showFeedback("")
            self.progressBar.updateProgress(0)
            if self.generateQueryButton is None:
                self.generateQueryButton=jp.Button(text="Generate SPARQL query",classes="btn btn-primary",a=self.colD1,click=self.onGenerateQueryButtonClick,disabled=True)
            if self.paretoSelect is None:
                self.paretoSelect=self.createParetoSelect(a=self.colD1)
            self.generateQueryButton.disabled=False
        except (BaseException,HTTPError) as ex:
            self.handleException(ex)

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
    async def getMostFrequentlyUsedProperties(self,tt):
        '''
        get the most frequently used properties for the given truly tabular
        
        Args:
            tt(TrulyTabular): the truly tabular Wikidata Item Analysis 
        '''
        try:
            total=self.ttcount
            pareto=self.paretoLevels[self.paretoLevel]

            minCount=round(total/pareto.oneOutOf)
            self.ttquery=tt.mostFrequentPropertiesQuery(minCount=minCount)
            if self.propertyQueryDisplay is None:
                self.propertyQueryDisplay=self.createQueryDisplay("property Query",a=self.colA4)
            self.propertyQueryDisplay.showSyntaxHighlightedQuery(self.ttquery)
            await self.wp.update()
        except (BaseException,HTTPError) as ex:
            self.handleException(ex)

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

    async def getCountQuery(self,tt):
        try:
            self.showFeedback(f"running count query for {str(self.tt)} ...")
            await self.wp.update()
            self.ttcount,countQuery=tt.count()
            self.countDiv.text=f"{self.ttcount} instances found"
            if self.countQueryDisplay is None:
                self.countQueryDisplay=self.createQueryDisplay("count Query",a=self.colA4)
            countSparqlQuery=Query(name="count Query",query=countQuery)
            self.countQueryDisplay.showSyntaxHighlightedQuery(countSparqlQuery)
            await self.wp.update()
        except (BaseException,HTTPError) as ex:
            self.handleException(ex)

    async def getPropertiesTable(self,tt,ttquery):
        '''
        get the properties table
        '''
        try:
            self.showFeedback(f"running query for most frequently used properties of {str(self.tt)} ...")
            await self.wp.update()
            self.propertyList=tt.sparql.queryAsListOfDicts(ttquery.query)
            self.propertySelection=PropertySelection(self.propertyList,total=self.ttcount,paretoLevels=self.paretoLevels)
            self.propertySelection.prepare()
            self.ttTable=Table(lod=self.propertySelection.propertyList,headerMap=self.propertySelection.headerMap,primaryKey='propertyId',allowInput=False,a=self.rowE)
            for aggregate in PropertySelection.aggregates:
                checked=False #aggregate in ["sample","count","list"]
                self.addSelectionColumn(self.ttTable, aggregate,lambda _record:checked)
            self.addSelectionColumn(self.ttTable,"ignore",lambda record:record["pareto"]<=self.paretoLevel,self.onIgnoreSelect)
            self.addSelectionColumn(self.ttTable,"label",lambda _record:False)
            self.addSelectionColumn(self.ttTable,"select",lambda record:record["pareto"]<=self.paretoLevel)


            self.showFeedback(f"table for propertySelection of {str(self.tt)} created ...")
            await self.wp.update()
        except (BaseException,HTTPError) as ex:
            self.handleException(ex)
            
    async def selectProperty(self,propertySelection):
        '''
        select a wikidata Property for analysis
        '''
        

    async def selectItem(self,itemId):
        '''
        select a Wikidata Item for analysis
        
        Args:
            itemId(str): the Wikidata Q - ID of the selected item
        '''
        if not itemId:
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
            wdItem=self.tt.item
            itemText=str(self.tt)
            self.itemLinkDiv.inner_html=Link.create(f"{wdItem.url}",itemText, wdItem.description, target="_blank")
            await self.wp.update()
            await self.getCountQuery(self.tt),
            await self.getMostFrequentlyUsedProperties(self.tt),
            await self.getPropertiesTable(self.tt,self.ttquery),
            await self.trulyTabularAnalysis(self.tt)
        except BaseException as ex:
            self.handleException(ex)

    async def onGenerateQueryButtonClick(self,_msg):
        try:
            self.showFeedback(f"generating SPARQL query for {str(self.tt)}")
            self.generateQuery()
        except BaseException as ex:
            self.handleException(ex)
        await self.wp.update()

    async def onItemSelect(self,msg):
        '''
        react on item being selected via Select control
        '''
        await self.selectItem(msg.value)
        
    async def onPropertySelect(self,msg):
        await self.selectProperty(msg.value)

    async def onItemInput(self,_msg):
        '''
        react on item being selected via enter key in input
        '''
        try:
            await self.selectItem(self.itemSelect.value)
        except BaseException as ex:
            self.handleException(ex)

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
        self.paretoLevel=int(msg.value)
        self.feedback.text=f"pareto level {self.paretoLevel} selected"
        if self.generateQueryButton is not None:
            await self.selectItem(self.itemQid)
        pass

    def createParetoSelect(self,a):
        '''
        create the pareto select
        
        Args:
            a(object): the parent component
            
        Returns:
            jp.Select
        '''
        pselect=self.createSelect("Pareto",self.paretoLevel,change=self.onParetoSelect,a=a)
        for pareto in self.paretoLevels:
            pselect.add(jp.Option(value=pareto.level,text=pareto.asText(long=True)))
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
        self.colA1=jp.Div(classes="col-2",a=rowA)
        self.colA2=jp.Div(classes="col-2",a=rowA)
        self.colA3=jp.Div(classes="col-2",a=rowA)
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
        self.colD1=jp.Div(classes="col-3",a=self.rowD)

        self.rowE=jp.Div(classes="row",a=self.contentbox)
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
        self.listSeparatorSelect=self.createSelect("List separator",self.listSeparator,a=self.colC1,change=self.onChangeListSeparator)
        for value,text in [("|","|"),(",",","),(";",";"),(":",":"),(chr(28),"FS - ASCII(28)"),(chr(29),"GS - ASCII(29)"),(chr(30),"RS - ASCII(30)"),(chr(31),"US - ASCII(31)")]:
            self.listSeparatorSelect.add(jp.Option(value=value,text=text))
        # pareto selection
        self.paretoSelect=self.createParetoSelect(a=self.colD1)
        return self.wp

    async def ttcontent(self,request):
        '''
        RESTful access
        '''
        if "qid" in request.path_params:
            qid=request.path_params["qid"]
        content=await self.content()
        await self.wp.update()
        await self.selectItem(qid)
        return content

    async def content(self):
        '''
        provide the justpy content by adding to the webpage provide by the App
        '''

        self.setupRowsAndCols()

        # self.itemcombo=ComboBox(a=colA1,placeholder='Please type here to search ...',change=self.onItemBoxChange)
        self.item=self.createInput(labelText="Wikidata item", a=self.colA1, placeholder='Please type here to search ...',value=self.itemQid,change=self.onItemChange)
        # on enter use the currently selected item 
        self.item.on('change', self.onItemInput)
        self.itemSelect=jp.Select(classes="form-select",a=self.colA2,change=self.onItemSelect)
        self.propertyCombo=self.createComboBox("property", a=self.colA3,value=str(self.wdProperty),size=40,change=self.onPropertySelect)
        wds=WikidataSearch()
        props=wds.getProperties()
        for propId,propName in props.items():
            self.propertyCombo.dataList.addOption(value=f"{propName}:({propId})",text=propName)
        # link and count for the item
        self.itemLinkDiv=jp.Div(a=self.colB1,classes="h5")
        self.countDiv=jp.Div(a=self.colB2,classes="h5")

        return self.wp

DEBUG = 0
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    wdBrowser=WikiDataBrowser(version.Version)
    sys.exit(wdBrowser.mainInstance())