import justpy as jp
import pandas as pd

wm_df = pd.read_csv('https://elimintz.github.io/women_majors.csv').round(2)

def row_selected(self, msg):
    print(msg)
    if msg.selected:
        self.row_data_div.text = msg.data
        self.row_selected = msg.rowIndex
    elif self.row_selected == msg.rowIndex:
        self.row_data_div.text = ''

def grid_test():
    wp = jp.WebPage()
    row_data_div = jp.Div(a=wp)
    grid = wm_df.jp.ag_grid(a=wp)
    grid.row_data_div = row_data_div
    grid.on('rowSelected', row_selected)
    grid.options.columnDefs[0].checkboxSelection = True
    return wp

jp.justpy(grid_test)
