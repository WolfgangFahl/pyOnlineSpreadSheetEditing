'''
Created on 2022-07-24

@author: wf
'''
import collections
import html
import sys
import justpy as jp
from jpwidgets.jpTable import Table
from jpwidgets.bt5widgets import App,ComboBox
import onlinespreadsheet.version as version
from lodstorage.query import EndpointManager, QuerySyntaxHighlight
from lodstorage.trulytabular import TrulyTabular, WikidataItem
from onlinespreadsheet.pareto import Pareto
from wd.wdsearch import WikidataSearch

class PropertySelection():
    '''
    select properties
    '''
    def __init__(self,inputList):
        '''
           Constructor
        
        Args:
            propertyList(list): the list of properties to show
        '''
        self.propertyList=[]
        for record in inputList:
            orecord=collections.OrderedDict(record.copy())
            self.propertyList.append(orecord)
        pass

    def prepare(self,total:int,paretoLevels:list,checkBoxName:str,defaultParetoSelect=1):
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
            continue
            propLabel=prop.pop("propLabel")
            url=prop.pop("prop")
            itemId=url.replace("http://www.wikidata.org/entity/","")
            prop["property"]=jp.Link(href=url,text=propLabel)
            ratio=int(prop["count"])/total
            level=0
            for pareto in reversed(paretoLevels):
                if pareto.ratioInLevel(ratio):
                    level=pareto.level
            prop["%"]=f'{ratio*100:.1f}'
            prop["pareto"]=level
            prop["1"]=""
            prop["max"]=""
            prop["nt"]=""
            prop["nt%"]=""
            prop["?f"]=""
            prop["?ex"]=""
            prop["✔"]=""
            checked=" checked" if level<=defaultParetoSelect else ""
            prop["select"]=f'<input name="{checkBoxName}" value="{itemId}" id="{itemId}" type="checkbox"{checked}>'
        pass
    
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
        self.feedback.text = searchFor
        for qid,itemLabel,desc in self.wdSearch.searchOptions(searchFor):
            text=f"{itemLabel} ({qid}) {desc}"
            self.itemcombo.addOption(text)
        
    def onItemChange(self,msg:dict):
        '''
        rect on changes in the item input
        '''
        try:
            searchFor=msg.value
            self.feedback.text = searchFor
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
            self.tryItLink=jp.Link(href=tryItUrlEncoded,text="try it!",title="try out with wikidata query service",a=self.queryTryIt)
            await self.wp.update()
        except Exception as ex:
            self.handleException(ex)
                
    async def getTable(self,tt,ttquery):
        try:
            self.feedback.text="running count query ..."
            await self.wp.update()
            ttcount=tt.count()
            self.countDiv.text=f"{ttcount}"
            self.feedback.text="running query ..."
            await self.wp.update()
            propertyList=tt.sparql.queryAsListOfDicts(ttquery.query)
            propertySelection=PropertySelection(propertyList)
            propertySelection.prepare(total=ttcount,paretoLevels=self.paretoLevels,checkBoxName="propertyCheck")
            self.table=Table(lod=propertySelection.propertyList,allowInput=False,a=self.rowE)        
            self.feedback.text="table created ..."
            await self.wp.update()
        except Exception as ex:
            self.handleException(ex)
                              
    async def selectItem(self,itemId):
        '''
        select a Wikidata Item for analysis
        
        Args:
            itemId(str): the Wikidata Q - ID of the selected item
        '''
        try:
            self.feedback.text = f"item {itemId} selected"
            await self.wp.update()
            # create the Truly Tabular Analysis
            self.tt=TrulyTabular(itemId)
            self.feedback.text = f"trulytabular {str(self.tt)} initiated"
            await self.wp.update()
            await self.getMostFrequentlyUsedProperties(self.tt)
            await self.getTable(self.tt,self.ttquery)
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
        
    def onChangeLanguage(self,msg):
        '''
        react on language being changed via Select control
        '''
        self.language=msg.value
        self.wdSearch.language=self.language
        
    def onParetoSelect(self,msg):
        '''
        '''
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
        pselect=self.createSelect("Pareto",1,change=self.onParetoSelect,a=a)
        self.paretoLevels=[]
        for level in range(1,topLevel+1):
            pareto=Pareto(level)
            self.paretoLevels.append(pareto)
            pselect.add(jp.Option(value=pareto.level,text=pareto.asText(long=True)))
        return pselect
    
    async def browse(self):
        '''
        browse
        '''
        head="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">
<link rel="stylesheet" href="/static/css/pygments.css">
"""
        self.wp=self.getWp(head)
        rowA=jp.Div(classes="row",a=self.contentbox)
        colA1=jp.Div(classes="col-3",a=rowA)
        colA2=jp.Div(classes="col-3",a=rowA)
        colA3=jp.Div(classes="col-6",a=rowA)
        
        rowB=jp.Div(classes="row",a=self.contentbox)
        colB1=jp.Div(classes="col-3",a=rowB)
        colB2=jp.Div(classes="col-3",a=rowB)
        
        rowC=jp.Div(classes="row",a=self.contentbox)
        colC1=jp.Div(classes="col-3",a=rowC)
    
        self.rowD=jp.Div(classes="row",a=self.contentbox)
        self.colD1=jp.Div(classes="col-3",a=self.rowD)
        
        self.rowE=jp.Div(classes="row",a=self.contentbox)
        
        
        self.queryDiv=jp.Div(a=colA3)
        self.queryTryIt=jp.Div(a=colA3)
        # self.itemcombo=ComboBox(a=colA1,placeholder='Please type here to search ...',change=self.onItemBoxChange)
        self.item=self.createInput(text="Wikidata item", a=colA1, placeholder='Please type here to search ...',change=self.onItemChange)
        # on enter use the currently selected item 
        self.item.on('change', self.onItemInput)   
        self.itemSelect=jp.Select(classes="form-select",a=colA2,change=self.onItemSelect)
        
        self.countDiv=jp.Div(a=self.colD1)
        
        self.endpointName=self.args.endpointName
        self.endpointSelect=self.createSelect("Endpoint", self.endpointName, a=colB1,change=self.onChangeEndpoint)
        for name in EndpointManager.getEndpointNames():
            self.endpointSelect.add(jp.Option(value=name, text=name))
        
        self.languageSelect=self.createSelect("Language","en",a=colB2,change=self.onChangeLanguage)
        for language in self.getLanguages():
            lang=language[0]
            desc=language[1]
            desc=html.unescape(desc)
            self.languageSelect.add(jp.Option(value=lang,text=desc))
            
        self.paretoSelect=self.createParetoSelect(a=colC1)
            
        self.feedback=jp.Div(a=rowC)
        
        self.errors=jp.Span(a=rowC,style='color:red')
        return self.wp
        
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