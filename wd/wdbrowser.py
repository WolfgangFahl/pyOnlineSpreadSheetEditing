'''
Created on 2022-07-24

@author: wf
'''
import collections
import html
import sys
import justpy as jp
from jpwidgets.jpTable import Table
from jpwidgets.bt5widgets import App,Alert,Collapsible, ComboBox, Link, ProgressBar
import onlinespreadsheet.version as version
from lodstorage.query import Query,EndpointManager, QuerySyntaxHighlight
from lodstorage.trulytabular import TrulyTabular
from onlinespreadsheet.pareto import Pareto
from wd.wdsearch import WikidataSearch
from urllib.error import HTTPError

class PropertySelection():
    '''
    select properties
    '''
    aggregates=["min","max","avg","sample","list","counter"]
    
    def __init__(self,inputList,total:int,paretoLevels:list):
        '''
           Constructor
        
        Args:
            propertyList(list): the list of properties to show
        '''
        self.propertyMap={}
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

    def prepare(self):
        '''
        prepare the propertyList
        
        Args:
            total(int): the total number of records
            paretoLevels(list): the pareto Levels to use
        '''
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
            for col in PropertySelection.aggregates:
                prop[col]=""
            prop["ignore"]=""
            prop["select"]=""
            self.propertyMap[itemId]=prop
             
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
        self.language="en"
        self.wdSearch=WikidataSearch(self.language)
        self.paretoLevel=1
        self.ttTable=None
        jp.Route('/tt/{qid}', self.content)
        
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
        
        
    def generateQuery(self):
        Alert(a=self.rowC, text="SPARQL Query generation not implemented yet")
        pass
        
    def onChangeEndpoint(self,msg:dict):
        '''
        handle selection of a different endpoint
        
        Args:
            msg(dict): the justpy message
        '''
       
        if self.debug:
            print(msg)
        self.endPointName=msg.value
        
    def onItemBoxChange(self,msg:dict):
        searchFor=msg.value
        self.showFeedback(f"searching wikidata for {searchFor}...")
        for qid,itemLabel,desc in self.wdSearch.searchOptions(searchFor):
            text=f"{itemLabel} ({qid}) {desc}"
            self.itemcombo.addOption(text)
        
    def onItemChange(self,msg:dict):
        '''
        rect on changes in the item input
        '''
        try:
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
        except Exception as ex:
            self.handleException(ex)
           
    async def wikiTrulyTabularPropertyStats(self,itemId:str,propertyId:str):
        '''
        get the truly tabular property statistics
        
        Args:
            itemId(str): the Wikidata item identifier
            propertyId(str): the property id
        '''        
        tt=TrulyTabular(itemId,propertyIds=[propertyId])
        statsRow=next(tt.genPropertyStatistics())
        for key in ["queryf","queryex"]:
            queryText=statsRow[key]
            sparql=f"# This query was generated by Truly Tabular\n{queryText}"
            query=Query(name=key,query=sparql)
            tryItUrl="https://query.wikidata.org/"
            tryItUrlEncoded=query.getTryItUrl(tryItUrl)
            tryItLink=Link.create(url=tryItUrlEncoded,text="try it!",tooltip="try out with wikidata query service",target="_blank")
            statsRow[f"{key}TryIt"]=tryItLink
        return statsRow
            
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
        propertyCount=0
        for propRecord in self.propertySelection.propertyMap.values():
            paretoLevel=propRecord["pareto"]
            if paretoLevel<=self.paretoLevel:
                propertyCount+=1
        for i,item in enumerate(self.propertySelection.propertyMap.items()):
            propertyId,propRecord=item
            paretoLevel=propRecord["pareto"]
            prop=propRecord["property"]
            if paretoLevel<=self.paretoLevel:
                self.showFeedback(f"{i+1}/{propertyCount}: querying statistics for {propertyId}:{prop} ...")
                self.progressBar.updateProgress(int((i+1)*100/propertyCount))
                await self.wp.update()
                statsRow=await self.wikiTrulyTabularPropertyStats(tt.itemQid, propertyId)
                statsRow["✔"]="✔"
                for column,statsColumn in [("1","1"),("maxf","maxf"),("nt","non tabular"),("nt%","non tabular%"),("?f","queryfTryIt"),("?ex","queryexTryIt"),("✔","✔")]:
                    if statsColumn in statsRow:
                        value=statsRow[statsColumn]
                        self.ttTable.updateCell(propertyId, column, value)
                await self.wp.update()
            #done
            self.showFeedback("")
            self.progressBar.updateProgress(0)
            self.generateQueryButton.disabled=False
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
            self.ttquery=tt.mostFrequentPropertiesQuery()    
            qs=QuerySyntaxHighlight(self.ttquery)
            queryHigh=qs.highlight()
            # TODO: configure via endpoint configuration
            tryItUrl="https://query.wikidata.org/"
            tryItUrlEncoded=self.ttquery.getTryItUrl(tryItUrl)
            self.queryDiv.inner_html=queryHigh
            # clear div for try It
            self.queryTryIt.delete_components()
            self.tryItLink=jp.Link(href=tryItUrlEncoded,text="try it!",title="try out with wikidata query service",a=self.queryTryIt,target="_blank")
            await self.wp.update()
        except Exception as ex:
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
                
    async def getPropertiesTable(self,tt,ttquery):
        try:
            self.showFeedback(f"running count query for {str(self.tt)} ...")
            await self.wp.update()
            self.ttcount=tt.count()
            self.countDiv.text=f"{self.ttcount} instances found"
            self.showFeedback(f"running query for most frequently used properties of {str(self.tt)} ...")
            await self.wp.update()
            self.propertyList=tt.sparql.queryAsListOfDicts(ttquery.query)
            self.propertySelection=PropertySelection(self.propertyList,total=self.ttcount,paretoLevels=self.paretoLevels)
            self.propertySelection.prepare()
            self.ttTable=Table(lod=self.propertySelection.propertyList,primaryKey='propertyId',allowInput=False,a=self.rowE)        
            for aggregate in PropertySelection.aggregates:
                self.addSelectionColumn(self.ttTable, aggregate,lambda _record:True)
            self.addSelectionColumn(self.ttTable,"select",lambda record:record["pareto"]<=self.paretoLevel)
            self.addSelectionColumn(self.ttTable,"ignore",lambda _record:False,self.onIgnoreSelect)
            self.showFeedback(f"table for propertySelection of {str(self.tt)} created ...")
            await self.wp.update()
        except (Exception,HTTPError) as ex:
            self.handleException(ex)
                              
    async def selectItem(self,itemId):
        '''
        select a Wikidata Item for analysis
        
        Args:
            itemId(str): the Wikidata Q - ID of the selected item
        '''
        if itemId is None:
            return
        try:
            self.itemQid=itemId
            self.propertyList=None
            # delete the Table
            if self.ttTable is not None:
                try:
                    self.ttTable.a.remove_component(self.ttTable)
                except Exception as ex:
                    pass
                self.ttTable=None
                self.generateQueryButton.disabled=True
            self.showFeedback(f"item {itemId} selected")
            await self.wp.update()
            # create the Truly Tabular Analysis
            self.tt=TrulyTabular(itemId)
            self.showFeedback(f"trulytabular {str(self.tt)} initiated")
            wdItem=self.tt.item
            self.itemLinkDiv.inner_html=Link.create(f"{wdItem.url}",wdItem.qlabel, wdItem.description, target="_blank")
            await self.wp.update()
            await self.getMostFrequentlyUsedProperties(self.tt)
            await self.getPropertiesTable(self.tt,self.ttquery)
            await self.trulyTabularAnalysis(self.tt)
        except Exception as ex:
            self.handleException(ex)
        
    async def onGenerateQueryButtonClick(self,_msg):
        try:
            self.showFeedback(f"generating SPARQL query for {str(self.tt)}")
            self.generateQuery()
        except Exception as ex:
            self.handleException(ex)
            
    async def onItemSelect(self,msg):
        '''
        react on item being selected via Select control
        '''
        await self.selectItem(msg.value) 
        
    async def onItemInput(self,_msg):
        '''
        react on item being selected via enter key in input
        '''
        try: 
            await self.selectItem(self.itemSelect.value)
        except Exception as ex:
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
        except Exception as ex:
            self.handleException(ex)
        
    async def onChangeLanguage(self,msg):
        '''
        react on language being changed via Select control
        '''
        self.language=msg.value
        self.wdSearch.language=self.language
        
    async def onParetoSelect(self,msg):
        '''
        change pareto selection
        '''
        self.paretoLevel=int(msg.value)
        self.feedback.text=f"pareto level {self.paretoLevel} selected"
        await self.selectItem(self.itemQid)
        pass
            
    def createParetoSelect(self,a,topLevel:int=9):
        '''
        create the pareto select
        
        Args:
            topLevel(int): the maximum pareto Level
            a(object): the parent component
            
        Returns:
            jp.Select
        '''
        pselect=self.createSelect("Pareto",self.paretoLevel,change=self.onParetoSelect,a=a)
        self.paretoLevels=[]
        for level in range(1,topLevel+1):
            pareto=Pareto(level)
            self.paretoLevels.append(pareto)
            pselect.add(jp.Option(value=pareto.level,text=pareto.asText(long=True)))
        return pselect
    
    async def content(self,request):
        '''
        provide the justpy content by adding to the webpage provide by the App
        '''
        if "qid" in request.path_params:
            self.itemQid=request.path_params["qid"]
        else:
            self.itemQid=""
        head="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">
<link rel="stylesheet" href="/static/css/pygments.css">
"""
        # extend the justpy Webpage with the given head parameters
        self.wp=self.getWp(head)
        
        # setup Bootstrap5 rows and columns
        
        rowA=jp.Div(classes="row",a=self.contentbox)
        colA1=jp.Div(classes="col-3",a=rowA)
        colA2=jp.Div(classes="col-3",a=rowA)
        colA3=jp.Div(classes="col-6",a=rowA)
        
        self.rowB=jp.Div(classes="row",a=self.contentbox)
        self.colB1=jp.Div(classes="col-2",a=self.rowB)
        self.colB2=jp.Div(classes="col-2",a=self.rowB)
        
        self.rowC=jp.Div(classes="row",a=self.contentbox)
        self.colC1=jp.Div(classes="col-3",a=self.rowC)
    
        self.rowD=jp.Div(classes="row",a=self.contentbox)
        self.colD1=jp.Div(classes="col-3",a=self.rowD)
        
        self.rowE=jp.Div(classes="row",a=self.contentbox)
        
        # self.itemcombo=ComboBox(a=colA1,placeholder='Please type here to search ...',change=self.onItemBoxChange)
        self.item=self.createInput(text="Wikidata item", a=colA1, placeholder='Please type here to search ...',value=self.itemQid,change=self.onItemChange)
        # on enter use the currently selected item 
        self.item.on('change', self.onItemInput)   
        self.itemSelect=jp.Select(classes="form-select",a=colA2,change=self.onItemSelect)
        
        # link and count for the item
        self.itemLinkDiv=jp.Div(a=self.colB1,classes="h5")
        self.countDiv=jp.Div(a=self.colB2,classes="h5")
        
        # Query
        self.queryHideShow=Collapsible("Query",a=colA3)
        self.queryDiv=jp.Div(a=self.queryHideShow.body)
        self.queryTryIt=jp.Div(a=self.queryHideShow.body)
        
        # Settings
        self.settingsCollapsible = Collapsible("Settings", a=self.rowC)
        self.endpointName=self.args.endpointName
        self.endpointSelect=self.createSelect("Endpoint", self.endpointName, a=self.settingsCollapsible.body,change=self.onChangeEndpoint)
        for name in EndpointManager.getEndpointNames():
            self.endpointSelect.add(jp.Option(value=name, text=name))
        
        self.languageSelect=self.createSelect("Language","en",a=self.settingsCollapsible.body,change=self.onChangeLanguage)
        for language in self.getLanguages():
            lang=language[0]
            desc=language[1]
            desc=html.unescape(desc)
            self.languageSelect.add(jp.Option(value=lang,text=desc))
            
        # pareto selection
        self.paretoSelect=self.createParetoSelect(a=self.colD1)
        self.generateQueryButton=jp.Button(text="Generate SPARQL query",classes="btn btn-primary",a=self.colD1,click=self.onGenerateQueryButtonClick,disabled=True)
        # progressbar, feedback and errors
        self.progressBar = ProgressBar(a=self.rowD)                                
        self.feedback=jp.Div(a=self.rowD)
        self.errors=jp.Span(a=self.rowD,style='color:red')
        return self.wp
        
DEBUG = 0
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    wdBrowser=WikiDataBrowser(version.Version)    
    sys.exit(wdBrowser.mainInstance())