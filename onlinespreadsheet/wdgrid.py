"""
Created on 2023-01-11

@author: wf
"""

import asyncio
import copy
import datetime
import json
import pprint
import re
import typing
from dataclasses import dataclass
from typing import Callable

from ez_wikidata.wbquery import WikibaseQuery
from ez_wikidata.wdproperty import PropertyMapping
from ez_wikidata.wikidata import Wikidata, WikidataItem

# from jpwidgets.bt5widgets import Alert, App, IconButton, Spinner, Switch
# from jpwidgets.widgets import LodGrid, QPasswordDialog
# from justpy import Br, Button, Div, Link, Span, WebPage
from lodstorage.lod import LOD
from lodstorage.sparql import SPARQL
from markupsafe import Markup
from ngwidgets.lod_grid import ListOfDictsGrid
from ngwidgets.webserver import WebSolution

from onlinespreadsheet.record_sync import ComparisonRecord, SyncAction, SyncRequest


class WikidataGrid:
    """
    a grid with tabular data from wikidata to work with
    """

    def __init__(
        self,
        solution: WebSolution,
        entityName: str,
        entityPluralName: typing.Optional[str],
        source: str,
        getLod: Callable,
        additional_reload_callback: typing.Union[Callable, None] = None,
        row_selected_callback: typing.Callable = None,
        lodRowIndex_column: str = "lodRowIndex",
        debug: bool = False,
    ):
        """
        constructor
        Args:
            solution(Websolution): the web solution context of this grid
            entityName(str): the name of the entity that this grid is for
            entityPluralName(str): the plural name of the entity type of items displayed in this grid
            source(str): the name of my source (where the data for this grid comes from)
            getLod(Callable): the function to get my list of dicts
            additional_reload_callback: Function to be called after fetching the new data and before updating aggrid
            lodRowIndex_column(str): the column/attribute to use for tracking the index in the lod
            debug(bool): if True show debug information
        """
        self.solution = solution
        self.lod_grid = None
        self.setEntityName(entityName, entityPluralName)
        self.lodRowIndex_column = lodRowIndex_column
        self.getLod = getLod
        self.additional_reload_callback = additional_reload_callback
        self.row_selected_callback = row_selected_callback
        self.source = source
        self.debug = debug
        self.dryRun = True
        self.ignoreErrors = False
        # @TODO make endpoint configurable
        self.wd = Wikidata("https://www.wikidata.org", debug=True)

    def setEntityName(self, entityName: str, entityPluralName: str = None):
        self.entityName = entityName
        self.entityPluralName = (
            entityPluralName if entityPluralName is not None else entityName
        )

    def setup(self, a):
        """
        setup the Wikidata grid nicegui components
        """
        if getattr(self, "container", None) is not None:
            self.container.delete_components()
        self.container = Div(a=a)
        self.controls_div = Div(
            a=self.container, classes="flex flex-row items-center m-2 p-2 gap-2"
        )
        self.alert_div = Div(a=self.container)
        self.dryRunButton = Switch(
            a=self.controls_div,
            labelText="dry run",
            checked=True,
            disable=True,
            on_input=self.onChangeDryRun,
        )
        self.ignoreErrorsButton = Switch(
            a=self.controls_div,
            labelText="ignore errors",
            checked=False,
            on_input=self.onChangeIgnoreErrors,
        )
        self.addFitSizeButton()
        self.assureAgGrid()
        self.sync_dialog_div = Div(a=self.alert_div, classes="container")

    def setViewLod(self, lod: list, nonValue: str = "-"):
        """
        add lodRowIndex column to list of dicts and
        use a copy of the given list of dicts for the view
        modify datetime columns to avoid problems with justpy

        Args:
            lod(list): the list of dicts
            nonValue(str): the string to use for "None" values
        """
        for index, row in enumerate(lod):
            row[self.lodRowIndex_column] = index
        self.viewLod = copy.deepcopy(lod)
        # fix non values
        for record in self.viewLod:
            for key in list(record):
                value = record[key]
                if value is None:
                    record[key] = nonValue
                vtype = type(value)
                # fix datetime entries
                if vtype is datetime.datetime:
                    value = str(value)
                    record[key] = value
        pass

    def reloadAgGrid(self, viewLod: list, showLimit: int = 10):
        """
        reload the agGrid with the given list of Dicts

        Args:
            viewLod(list): the list of dicts for the current view
            showLimit: number of rows to print when debugging
        """
        if self.agGrid is None:
            return
        self.agGrid.load_lod(viewLod)
        if self.debug:
            pprint.pprint(viewLod[:showLimit])
        self.refreshGridSettings()

    def setDefaultColDef(self, agGrid):
        """
        set the default column definitions
        Args:
            agGrid: agGrid to set the column definitions for
        """
        defaultColDef = agGrid.options.defaultColDef
        defaultColDef.resizable = True
        defaultColDef.sortable = True
        # https://www.ag-grid.com/javascript-data-grid/grid-size/
        defaultColDef.wrapText = True
        defaultColDef.autoHeight = True

    def refreshGridSettings(self):
        """
        refresh the ag grid settings e.g. enable the row selection event handler
        enable row selection event handler
        """
        self.agGrid.on("rowSelected", self.onRowSelected)
        self.agGrid.options.columnDefs[0].checkboxSelection = True

    def linkWikidataItems(self, viewLod, itemColumn: str = "item"):
        """
        link the wikidata entries in the given item column if containing Q values

        Args:
            viewLod(list): the list of dicts for the view
            itemColumn(str): the name of the column to handle
        """
        for row in viewLod:
            if itemColumn in row:
                item = row[itemColumn]
                if re.match(r"Q[0-9]+", item):
                    itemLink = self.createLink(
                        f"https://www.wikidata.org/wiki/{item}", item
                    )
                    row[itemColumn] = itemLink

    async def reload(self, _msg=None, clearErrors=True):
        """
        reload the table content via my getLod function

        Args:
            clearErrors(bool): if True clear Errors before reloading
        """
        try:
            if clearErrors:
                self.app.clearErrors()
            msg = (
                f"reload called ... fetching {self.entityPluralName} from {self.source}"
            )
            if self.debug:
                print(msg)
            _alert = Alert(a=self.alert_div, text=msg)
            await self.app.wp.update()
            items = self.getLod()
            self.setLod(items)
            _alert.delete_alert(None)
            msg = f"found {len(items)} {self.entityPluralName}"
            _alert = Alert(a=self.alert_div, text=msg)
            await self.app.wp.update()
            if self.debug:
                print(json.dumps(self.viewLod, indent=2, default=str))
            if callable(self.additional_reload_callback):
                self.additional_reload_callback()
            self.reloadAgGrid(self.viewLod)
            await self.app.wp.update()
            await asyncio.sleep(0.2)
            await self.agGrid.run_api("sizeColumnsToFit()", self.app.wp)
        except Exception as ex:
            _error = Span(a=_alert, text=f"Error: {str(ex)}", style="color:red")
            self.app.handleException(ex)

    def onChangeDryRun(self, msg: dict):
        """
        handle change of DryRun setting

        Args:
            msg(dict): the justpy message
        """
        self.dryRun = msg.value

    def onChangeIgnoreErrors(self, msg: dict):
        """
        handle change of IgnoreErrors setting

        Args:
            msg(dict): the justpy message
        """
        self.ignoreErrors = msg.value

    async def onRowSelected(self, msg):
        """
        row selection event handler

        Args:
            msg(dict): row selection information
        """
        if self.debug:
            print(msg)
        self.app.clearErrors()
        if msg.selected:
            self.rowSelected = msg.rowIndex
            # check whether a lodeRowIndex Index is available
            lodByRowIndex, _dup = LOD.getLookup(self.lod, self.lodRowIndex_column)
            if len(lodByRowIndex) == len(self.lod):
                lodRowIndex = msg.data[self.lodRowIndex_column]
            else:
                lodRowIndex = self.rowSelected
            record = self.lod[lodRowIndex]
            write = not self.dryRun
            # show spinner
            webpage: WebPage = msg.page
            self.sync_dialog_div.delete_components()
            Spinner(a=self.sync_dialog_div, classes="container")
            await webpage.update()
            try:
                if callable(self.row_selected_callback):
                    self.row_selected_callback(
                        record=record,
                        row_index=lodRowIndex,
                        write=write,
                        ignore_errors=self.ignoreErrors,
                    )
            except Exception as ex:
                self.sync_dialog_div.delete_components()
                self.app.handleException(ex)


class GridSync:
    """
    allow syncing the grid with data from wikibase
    """

    def __init__(
        self,
        wdgrid: WikidataGrid,
        entityName: str,
        pk: str,
        sparql: SPARQL,
        debug: bool = False,
    ):
        """
        constructor

        Args:
            wdgrid(WikiDataGrid): the wikidata grid to use
            entityName: name of the sheet
            pk: primary key
            sparql(SPARQL): the sparql endpoint access to use
            debug(bool): if True show debug information
        """
        self.wdgrid = wdgrid
        self.solution = wdgrid.solution
        self.entityName = entityName
        self.pk = pk
        self.sparql = sparql
        self.debug = debug
        self.wdgrid.additional_reload_callback = self.setup_aggrid_post_reload
        self.wdgrid.row_selected_callback = self.handle_row_selected
        self.wbQuery = None

    def loadItems(self):
        # we assume the grid has already been loaded here
        self.itemRows = self.wdgrid.lod
        self.pkColumn, self.pkType, self.pkProp = self.getColumnTypeAndVarname(self.pk)
        self.itemsByPk, _dup = LOD.getLookup(self.itemRows, self.pkColumn)
        if self.debug:
            print(f"{self.entityName} by {self.pkColumn}:{list(self.itemsByPk.keys())}")
            pass

    def setup(self, a, header):
        """
        initialize my components

        Args:
            a(HtmlComponent): the parent component
            header(HtmlComponent): the header for the primary key selector

        """
        selectorClasses = "w-32 m-2 p-2 bg-white"
        self.toolbar = self.app.jp.QToolbar(a=a, classes="flex flex-row gap-2")
        # for icons see  https://quasar.dev/vue-components/icon
        # see justpy/templates/local/materialdesignicons/iconfont/codepoints for available icons
        self.reloadButton = IconButton(
            a=self.toolbar,
            text="",
            title="reload",
            iconName="refresh-circle",
            click=self.wdgrid.reload,
            classes="btn btn-primary btn-sm col-1",
        )
        self.checkButton = IconButton(
            a=self.toolbar,
            text="",
            title="check",
            iconName="check",
            click=self.onCheckWikidata,
            classes="btn btn-primary btn-sm col-1",
        )
        self.loginButton = IconButton(
            a=self.toolbar,
            title="login",
            iconName="login",
            text="",
            click=self.onLogin,
            classes="btn btn-primary btn-sm col-1",
        )
        self.passwordDialog = QPasswordDialog(a=self.app.wp)
        # selector for column/property
        self.pkSelect = self.app.jp.Select(
            classes=selectorClasses, a=header, value=self.pk, change=self.onChangePk
        )

    def setup_aggrid_post_reload(self):
        """
        setup the aggrid
        """
        viewLod = self.wdgrid.viewLod
        self.wdgrid.agGrid.html_columns = self.getHtmlColumns()
        self.wdgrid.linkWikidataItems(viewLod)
        self.pkSelect.delete_components()
        self.pkSelect.add(self.app.jp.Option(value="item", text="item"))
        if self.wbQuery is not None:
            for propertyName, row in self.wbQuery.propertiesByName.items():
                columnName = row["Column"]
                if columnName:
                    self.pkSelect.add(
                        self.app.jp.Option(value=propertyName, text=columnName)
                    )

    async def onChangePk(self, msg: dict):
        """
        handle selection of a different primary key

        Args:
            msg(dict): the justpy message
        """
        self.pk = msg.value
        if self.debug:
            print(f"changed primary key of {self.entityName} to {self.pk}")
        try:
            await self.wdgrid.reload()
        except Exception as ex:
            self.app.handleException(ex)

    def onCheckWikidata(self, msg=None):
        """
        check clicked - check the wikidata content

        Args:
            msg(dict): the justpy message
        """
        if self.debug:
            print(msg)
        try:
            self.app.clearErrors()
            self.loadItems()
            # prepare syncing the table results with the wikibase query result
            # query based on table content
            self.query(self.sparql)
            # get the view copy to insert result as html statements
            viewLod = self.wdgrid.viewLod
            self.addHtmlMarkupToViewLod(viewLod)
            # reload the AG Grid with the html enriched content
            self.wdgrid.reloadAgGrid(viewLod)
        except Exception as ex:
            self.app.handleException(ex)

    def query(self, sparql):
        """
        query the wikibase instance based on the list of dict
        """
        lang = "en" if self.pkType == "text" else None
        valuesClause = self.wbQuery.getValuesClause(
            self.itemsByPk.keys(), self.pkProp, propType=self.pkType, lang=lang
        )
        self.sparqlQuery = self.wbQuery.asSparql(
            filterClause=valuesClause,
            orderClause=f"ORDER BY ?{self.pkProp}",
            pk=self.pk,
        )
        if self.debug:
            print(self.sparqlQuery)
        self.wbRows = sparql.queryAsListOfDicts(self.sparqlQuery)
        if self.debug:
            pprint.pprint(self.wbRows)

    def checkCell(
        self,
        viewLodRow,
        column,
        value,
        propVarname,
        propType,
        propLabel,
        propUrl: str = None,
    ):
        """
        update the cell value for the given

        Args:
            viewLodRow(dict): the row to modify
            value(object): the value to set for the cell
            propVarName(str): the name of the property Variable set in the SPARQL statement
            propType(str): the abbreviation for the property Type
            propLabel(str): the propertyLabel (if any)
            propUrl(str): the propertyUrl (if any)
        """
        cellValue = viewLodRow[column]
        valueType = type(value)
        print(
            f"{column}({propVarname})={value}({propLabel}:{propUrl}:{valueType})⮂{cellValue}"
        )
        # overwrite empty cells
        overwrite = not cellValue
        if cellValue:
            # overwrite values with links
            if propUrl and cellValue == value:
                overwrite = True
        if overwrite and value:
            doadd = True
            # create links for item  properties
            if not propType:
                value = self.wdgrid.createLink(value, propLabel)
            elif propType == "extid" or propType == "url":
                value = self.wdgrid.createLink(propUrl, value)
            if valueType == str:
                pass
            elif valueType == datetime.datetime:
                value = value.strftime("%Y-%m-%d")
            else:
                doadd = False
                print(f"{valueType} not added")
            if doadd:
                viewLodRow[column] = value

    def addHtmlMarkupToViewLod(self, viewLod: list):
        """
        add HtmlMarkup to the view list of dicts
        viewLod(list): a list of dict for the mark result
        """
        # now check the wikibase rows retrieved in comparison
        # to the current view List of Dicts Markup
        for wbRow in self.wbRows:
            # get the primary key value
            pkValue = wbRow[self.pkProp]
            pkValue = re.sub(
                r"http://www.wikidata.org/entity/(Q[0-9]+)", r"\1", pkValue
            )
            # if we have the primary key then we mark the whole row
            if pkValue in self.itemsByPk:
                if self.debug:
                    print(f"adding html markup for {pkValue}")
                # https://stackoverflow.com/questions/14538885/how-to-get-the-index-with-the-key-in-a-dictionary
                lodRow = self.itemsByPk[pkValue]
                rowIndex = lodRow[self.wdgrid.lodRowIndex_column]
                viewLodRow = viewLod[rowIndex]
                itemLink = self.wdgrid.createLink(wbRow["item"], wbRow["itemLabel"])
                viewLodRow["item"] = itemLink
                itemDescription = wbRow.get("itemDescription", "")
                self.checkCell(
                    viewLodRow,
                    "description",
                    itemDescription,
                    propVarname="itemDescription",
                    propType="string",
                    propLabel="",
                )
                # loop over the result items
                for propVarname, value in wbRow.items():
                    # remap the property variable name to the original property description
                    if propVarname in self.wbQuery.propertiesByVarname:
                        propRow = self.wbQuery.propertiesByVarname[propVarname]
                        column = propRow["Column"]
                        propType = propRow["Type"]
                        if not propType:
                            propLabel = wbRow[f"{propVarname}Label"]
                        else:
                            propLabel = ""
                        if propType == "extid":
                            propUrl = wbRow[f"{propVarname}Url"]
                        elif propType == "url":
                            propUrl = wbRow[f"{propVarname}"]
                        else:
                            propUrl = ""
                        # Linked Or
                        if (
                            type(value) == str
                            and value.startswith("http://www.wikidata.org/entity/")
                            and f"{propVarname}Label" in wbRow
                        ):
                            propUrl = value
                            propLabel = wbRow[f"{propVarname}Label"]
                            value = propLabel
                        if column in lodRow:
                            self.checkCell(
                                viewLodRow,
                                column,
                                value,
                                propVarname,
                                propType,
                                propLabel,
                                propUrl,
                            )

    def getColumnTypeAndVarname(self, propName: str):
        """
        slightly modified getter to account for "item" special case

        Args:
            propName(str): the name of the property
        """
        if propName == "item":
            column = "item"
            propType = "item"
            varName = "item"
        else:
            column, propType, varName = self.wbQuery.getColumnTypeAndVarname(propName)
        return column, propType, varName

    def getHtmlColumns(self):
        """
        get the columns that have html content(links)
        """
        htmlColumns = [0]
        # loop over columns of list of dicts
        wbQuery = self.wbQuery
        if wbQuery is not None:
            for columnIndex, column in enumerate(self.wdgrid.columns):
                # check whether there is metadata for the column
                if column in wbQuery.propertiesByColumn:
                    propRow = wbQuery.propertiesByColumn[column]
                    propType = propRow["Type"]
                    if not propType or propType == "extid" or propType == "url":
                        htmlColumns.append(columnIndex)
        return htmlColumns

    def add_record_to_wikidata(
        self,
        record: dict,
        row_index: int,
        write: bool = False,
        ignore_errors: bool = False,
    ):
        """
        add a record to wikidata when the row has been selected

        Args:
            record(dict): the data to be added to wikidata
            row_index(int): the row index
            write(bool): if True actually write data
            ignore_errors(bool): if True ignore errors that might occur
        """
        if not "label" in record:
            raise Exception(f"label missing in {record}")
        label = record["label"]
        mapDict = self.wbQuery.propertiesById
        rowData = record.copy()
        # remove index
        if self.wdgrid.lodRowIndex_column in rowData:
            rowData.pop(self.wdgrid.lodRowIndex_column)
        qid, errors = self.wdgrid.wd.addDict(
            rowData, mapDict, write=write, ignoreErrors=ignore_errors
        )
        if qid is not None:
            # set item link
            link = self.wdgrid.createLink(
                f"https://www.wikidata.org/wiki/{qid}", f"{label}"
            )
            self.wdgrid.viewLod[row_index]["item"] = link
            self.wdgrid.agGrid.load_lod(self.wdgrid.viewLod)
            self.wdgrid.refreshGridSettings()
        # @TODO improve error handling
        if len(errors) > 0:
            self.wdgrid.app.errors.text = errors
            print(errors)
        # dry run and error display
        if not write or len(errors) > 0:
            prettyData = pprint.pformat(rowData)
            html = Markup(f"<pre>{prettyData}</pre>")
            # create an alert
            alert = Alert(text="", a=self.wdgrid.app.rowA)
            alert.contentDiv.inner_html = html

    def handle_row_selected(
        self,
        record: dict,
        row_index: int,
        write: bool = False,
        ignore_errors: bool = False,
    ):
        record = record.copy()
        record = {k: v if v != "" else None for k, v in record.items()}
        prop_maps = self.get_property_mappings()
        item_prop = PropertyMapping.get_item_mapping(prop_maps)
        item_id = record.get(item_prop.column, None)
        # sanitize record
        for key in [item_prop.column, "lodRowIndex"]:
            if key in record:
                record.pop(key)
        # limit record to properties that are synced with wikidata
        prop_by_col = [pm.column for pm in prop_maps if not pm.is_item_itself()]
        prop_by_col.extend(["label", "description"])
        record = {k: v for k, v in record.items() if k in prop_by_col}
        # fetch record from wikidata
        wd_record = dict()
        if item_id is not None and item_id != "":
            wd_record = self.wdgrid.wd.get_record(item_id, prop_maps)
            wd_record = {k: v for k, v in wd_record.items() if k in prop_by_col}
        # normalize records
        record = self.wdgrid.wd.normalize_records(record, prop_maps)
        wd_record = self.wdgrid.wd.normalize_records(wd_record, prop_maps)

        cr = ComparisonRecord(self.wdgrid.source, record, "wikidata", wd_record)
        # save item specific attrs
        cr.lodRowIndex = row_index
        cr.qid = item_id
        # show SyncDialog
        self.wdgrid.sync_dialog_div.delete_components()
        sync_dialog = SyncDialog(
            cr,
            sync_callback=self._sync_callback,
            value_enhancement_callback=self.enhance_value_display,
            a=self.wdgrid.sync_dialog_div,
        )

    def _sync_callback(self, sync_request: SyncRequest):
        """
        Handle the given sync request
        """
        write = not self.wdgrid.dryRun
        lodRowIndex = getattr(sync_request.data, "lodRowIndex", None)
        update_sources = []
        if sync_request.action in [SyncAction.SYNC, SyncAction.RIGHT_SYNC]:
            update_sources.append(sync_request.data.right_source_name)
        if sync_request.action in [SyncAction.SYNC, SyncAction.LEFT_SYNC]:
            update_sources.append(sync_request.data.left_source_name)
        for source in update_sources:
            record = sync_request.data.get_update_record_of(source)
            for key, value in record.items():
                if isinstance(value, WikidataItem):
                    record[key] = value.qid
            for key in ["label", "desc"]:
                if key not in record and sync_request.data.comparison_data.get(
                    key, None
                ):
                    record[key] = sync_request.data.comparison_data.get(key).left_value
            prop_maps = self.get_property_mappings()
            item_pm = PropertyMapping.get_item_mapping(prop_maps)
            record[item_pm.column] = getattr(sync_request.data, "qid")
            if source == "wikidata":
                try:
                    self.add_record_to_wikidata(
                        record=record,
                        row_index=lodRowIndex,
                        write=write,
                        ignore_errors=self.wdgrid.ignoreErrors,
                    )
                    self.wdgrid.sync_dialog_div.delete_components()
                except Exception as ex:
                    self.app.handleException(ex)
            else:
                self.app.handleException(
                    Exception(f"Updating of source {source} is not supported")
                )

    def enhance_value_display(self, row: SyncDialogRow):
        """
        Enhances the displayed value
        """
        value_div_pairs = [
            (row.comparison_data.left_value, row.left_value_div),
            (row.comparison_data.right_value, row.right_value_div),
        ]
        for value_raw, div in value_div_pairs:
            values = value_raw if isinstance(value_raw, list) else [value_raw]
            for i, value in enumerate(values):
                if i > 0:
                    Br(a=div)
                if isinstance(value, WikidataItem):
                    div.text = ""
                    Link(a=div, href=value.get_url(), text=value.label)
                elif isinstance(value, str) and value.startswith("http"):
                    div.text = ""
                    Link(a=div, href=value, text=value)
