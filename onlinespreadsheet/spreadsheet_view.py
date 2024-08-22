"""
Created on 2024-03-19

@author: wf
"""

from typing import List

from ez_wikidata.wbquery import WikibaseQuery
from lodstorage.sparql import SPARQL
from ngwidgets.lod_grid import ListOfDictsGrid
from ngwidgets.widgets import Link
from nicegui import run, ui
from spreadsheet.googlesheet import GoogleSheet

# from onlinespreadsheet.wdgrid import GridSync


class SpreadSheetView:
    """
    shows a Spreadsheet
    """

    def __init__(self, solution):
        self.solution = solution
        self.debug = self.solution.debug
        self.args = solution.args
        self.url = self.args.url
        self.sheetNames = self.args.sheets
        if len(self.sheetNames) < 1:
            raise Exception("need at least one sheetName in sheets argument")
        self.sheetName = self.sheetNames[0]
        self.mappingSheetName = self.args.mappingSheet
        self.endpoint = self.args.endpoint
        self.sparql = SPARQL(self.endpoint)
        self.lang = self.args.lang
        self.setup_ui()
        # self.grid_sync=GridSync()

    def setup_ui(self):
        """
        setup my user interface
        """
        with ui.row() as self.log_row:
            self.log_view = ui.html()
        with ui.row() as self.input_row:
            url_label_text = "Google Spreadsheet Url"
            ui.label(url_label_text)
            ui.input(
                value=self.url,
                placeholder=f"Enter new {url_label_text}",
                on_change=self.on_change_url,
            )
            ui.button("reload", on_click=self.reload)
        with ui.row() as self.grid_row:
            self.lod_grid = ListOfDictsGrid()

        # ui.timer(0, self.reload, once=True)

    def load_items_from_selected_sheet(self) -> List[dict]:
        """
        Extract the records from the selected sheet and returns them as LoD

        Returns:
            List of dicts containing the sheet content
        """

        self.wbQueries = GoogleSheet.toWikibaseQuery(
            self.url, self.mappingSheetName, debug=self.debug
        )
        if len(self.wbQueries) == 0:
            print(
                f"Warning Wikidata mapping sheet {self.mappingSheetName} not defined!"
            )
        self.gs = GoogleSheet(self.url)
        self.gs.open([self.sheetName])
        items = self.gs.asListOfDicts(self.sheetName)
        wbQuery = self.wbQueries.get(self.sheetName, None)
        # self.gridSync.wbQuery = wbQuery
        return items

    def load_sheet(self):
        """
        load sheet in background
        """
        with self.solution.content_div:
            try:
                items = self.load_items_from_selected_sheet()
                self.lod_grid.load_lod(items)
                ui.notify(f"loaded {len(items)} items")
                self.lod_grid.update()
            except Exception as ex:
                self.solution.handle_exception(ex)

    async def reload(self):
        """
        reload my spreadsheet
        """
        try:
            link = Link.create(self.url, self.sheetNames[0])
            self.log_view.content = (
                f"{link}<br>{self.lang} {self.endpoint} {self.sheetNames}"
            )
            await run.io_bound(self.load_sheet)
        except Exception as ex:
            self.solution.handle_exception(ex)

    async def on_change_url(self, args):
        """
        handle selection of a different url
        """
        self.url = args.value
        await self.reload()
        pass
