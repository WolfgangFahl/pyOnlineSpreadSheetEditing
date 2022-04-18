import justpy as jp
from sl.googlesheet import GoogleSheet
from onlinespreadsheet.wikidata import Wikidata
from lodstorage.lod import LOD

class GoogleSheetObserver():
    '''
    Observer for a google sheet
    '''
    def __init__(self,url,spreadSheetName):
        self.gs=GoogleSheet(url)    
        spreadSheetNames=["WorldPrayerDays","Wikidata"] 
        self.gs.open(spreadSheetNames)  
        self.df=self.gs.dfs["WorldPrayerDays"]
        mapRows=self.gs.asListOfDicts("Wikidata")
        self.mapDict,_dup=LOD.getLookup(mapRows, "PropertyId", withDuplicates=False)
        self.wd=Wikidata("https://www.wikidata.org",debug=True)
        self.wd.login()

    def row_selected(self, msg):
        print(msg)
        if msg.selected:
            self.row_selected = msg.rowIndex
            write=True
            label=msg.data["label"]
            qid=self.wd.addDict(msg.data, self.mapDict,write=write)
            if qid is not None:
                self.link.href=f"https://www.wikidata.org/wiki/{qid}"
                self.link.text=f"{label}"
  
        elif self.row_selected == msg.rowIndex:
            self.row_data_div.text = ''

    def gridForDataFrame(self):
        '''
        show aggrid for the given data frame
        '''
        wp = jp.WebPage()
        self.row_data_div = jp.Div(a=wp)
        self.link=jp.A(a=self.row_data_div,href="https://www.wikidata.org/",text="wikidata")
        grid = self.df.jp.ag_grid(a=wp)
        grid.row_data_div = self.row_data_div
        grid.on('rowSelected', self.row_selected)
        grid.options.columnDefs[0].checkboxSelection = True
        return wp
    
    def start(self):
        jp.justpy(self.gridForDataFrame)

url="https://docs.google.com/spreadsheets/d/1AZ4tji1NDuPZ0gwsAxOADEQ9jz_67yRao2QcCaJQjmk"
gso=GoogleSheetObserver(url,"WorldPrayerDays")
gso.start()

