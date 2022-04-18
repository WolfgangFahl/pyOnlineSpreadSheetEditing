import justpy as jp
from sl.googlesheet import GoogleSheet

class GoogleSheetObserver():
    '''
    Observer for a google sheet
    '''
    def __init__(self,url,spreadSheetName):
        self.gs=GoogleSheet(url)    
        self.gs.open([spreadSheetName])  
        self.df=self.gs.dfs[spreadSheetName]

    def row_selected(self, msg):
        print(msg)
        if msg.selected:
            self.row_data_div.text = msg.data
            self.row_selected = msg.rowIndex
        elif self.row_selected == msg.rowIndex:
            self.row_data_div.text = ''

    def gridForDataFrame(self):
        '''
        show aggrid for the given data frame
        '''
        wp = jp.WebPage()
        self.row_data_div = jp.Div(a=wp)
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

