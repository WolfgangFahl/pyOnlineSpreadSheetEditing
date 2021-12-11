import math
import pandas as pd
import dateutil.parser as parser
import xml.etree.ElementTree as ET

from odf.text import P
from io import BytesIO
from pandas import Timestamp, NaT
from datetime import datetime, date
from lodstorage.lod import LOD
from odf.opendocument import load
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableColumn, TableRow, TableCell
from enum import Enum,auto

class SpreadSheetType(Enum):
    '''
    Entities of openresearch.
    Used to specify for a fixer the domain of operation.
    '''
    CSV=auto()
    EXCEL=auto()
    ODS=auto()
    
class SpreadSheet:
    '''
    i am spreadsheet
    '''
    
    def __init__(self,name:str,spreadSheetType:SpreadSheetType):
        '''
        constructor
        '''
        self.name=name
        self.spreadSheetType=spreadSheetType
        self.tables={} # dict of lods
        pass
    
    @classmethod
    def create(cls,spreadSheetType:SpreadSheetType,name:str):
        '''
        create a SpreadSheet of the given types
        
        Args:
            spreadSheetType(SpreadSheetType): the type of spreadsheet to create
            name(str): the name of the spreadsheet
        
        '''
        spreadSheet=None
        if spreadSheetType==SpreadSheetType.EXCEL:
            spreadSheet=ExcelDocument(name=name)
        elif spreadSheetType==SpreadSheetType.ODS:
            spreadSheet=OdsDocument(name=name)
        elif spreadSheetType==SpreadSheetType.CSV:
            spreadSheet=CSVSpreadSheet(name=name)
        return spreadSheet
    
    def getTable(self, name:str):
        """
        returns the data corresponding to the given table name
        Args:
            name: name of the table

        Returns:
            LoD
        """
        if name in self.tables:
            return self.tables[name]
        
    def addTable(self, name:str, lod:list, headers:dict=None):
        """
        add the given data as table to the document

        Args:
            name(str): name of the table
            lod: data that should be added to the document as table
            headers(dict): Mapping from dict key to the new headers. Also functions as restriction. If not defined dict key are used as headers
        """
        if headers:
            lod=[{newHeader:record.get(oldHeader, None) for oldHeader, newHeader in headers.items()} for record in lod]
        self.tables[name]=lod

    
class CSVSpreadSheet(SpreadSheet):
    '''
    CSV Spreadsheet packaging as ZIP file of CSV files
    '''
    def __init__(self, name: str):
        super().__init__(name=name, spreadSheetType=SpreadSheetType.CSV)
        

class ExcelDocument(SpreadSheet):
    """
    Provides methods to convert LoDs to an excel document and vice versa
    """

    MIME_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def __init__(self, name: str):
        """
        Args:
            name(str): name of the document
        """
        super().__init__(name=name, spreadSheetType=SpreadSheetType.EXCEL)
        

    @property
    def filename(self):
        return self.name + ".xlsx"

    def saveToFile(self, name: str = None):
        """
        saves the document to a file

        Args:
            name(str): name of the file. If not given the name of the document is used
        """
        if name is None:
            name = self.filename
        with pd.ExcelWriter(name, mode="w", engine="xlsxwriter") as writer:
            for tableName, tableData in self.tables.items():
                df = pd.DataFrame(tableData)
                df.to_excel(writer, sheet_name=tableName, index = False)

    def toBytesIO(self) -> BytesIO:
        """
        Converts the document into an StringIO stream

        Returns:
            StringIO Stream of the document
        """
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            for tableName, tableData in self.tables.items():
                df = pd.DataFrame(tableData)
                df.to_excel(writer, sheet_name=tableName, index = False)
        buffer.seek(0)
        return buffer

    def loadFromFile(self, file, samples:dict):
        """
        load the document from the given .ods file
        Args:
            file: absolut file path to the file that should be loaded
            samples(dict): samples of the sheets. Expected format: sheetName:SamplesForSheet
        Returns:

        """
        def getColType(value):
            if isinstance(value, datetime) or isinstance(value, date):
                return pd.to_datetime
            else:
                return type(value)
        def getLodValueType(value):
            if isinstance(value, datetime):
                return datetime
            elif isinstance(value, date):
                return date
            else:
                return type(value)

        def _loadFromFile(file):
            sheets = pd.read_excel(file, sheet_name=None).keys()
            for sheet in sheets:
                df = pd.read_excel(file, sheet_name=sheet, converters=sheetColTypes.get(sheet, None), na_values=None)
                df=df.where(pd.notnull(df), None)
                lod=df.to_dict('records')
                # NaT handling issue due to a bug in pandas https://github.com/pandas-dev/pandas/issues/29024
                lod=[{k: v.to_pydatetime() if isinstance(v, Timestamp) else None if isinstance(v, type(NaT)) else v for k,v in d.items()} for d in lod]
                # fix date (datetime → date) datetiem and date can not be distinguished in excel (handled over format)
                dateCols=[col for col, _type in lodValueTypes.get(sheet, {}).items() if _type == date]
                lod=[{k:v.date() if v and k in dateCols else v for k,v in d.items()} for d in lod]
                # float nan to None
                lod=[{k:v if not (isinstance(v, float) and math.isnan(v)) else None for k,v in d.items() }for d in lod]
                self.tables[sheet] = lod

        sheetColTypes={}
        lodValueTypes={}
        for sheet, sheetSamples in samples.items():
            colTypes={}
            valueTypes={}
            for s in sheetSamples:
                for col, value in s.items():
                    colType = getColType(value)
                    valueTypes[col]=getLodValueType(value)
                    if col in colTypes:
                        if colTypes[col] == colType:
                            continue
                        else:
                            # inconsistent datatype default to string
                            colType=str
                    colTypes[col]=colType
            sheetColTypes[sheet]=colTypes
            lodValueTypes[sheet]=valueTypes
        if isinstance(file, str):
            with open(file, mode="rb") as reader:
                _loadFromFile(reader)
        else:
            _loadFromFile(file)

class OdsDocument(SpreadSheet):
    """
    OpenDocument Spreadsheet that can store multiple tables.
    Provides functions to traverse between LoD and ODS document
    """
    MIME_TYPE = 'application/vnd.oasis.opendocument.spreadsheet'

    prefix_map = {
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
        "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
        "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
        "number": "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
        "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
        "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
        "chart": "urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
        "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
        "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0"
    }

    def __init__(self, name: str):
        """
        Args:
            name(str): name of the document
        """
        self.name = name
        self.doc = OpenDocumentSpreadsheet()

    @property
    def filename(self):
        return self.name + ".ods"

    @staticmethod
    def lod2Table(lod: list, name: str = None, headers: list = None, **kwargs) -> Table:
        """
        converts the given lod to an ODS Table

        Args:
            lod(list): lod containing the data for the table
            name(str): name of the table
            headers(list): order of the columns by order of column headers

        Returns:
            Table
        """
        table = Table(name=name)
        if headers is None:
            headers = LOD.getFields(lod)

        def valuetype(val):
            """

            https://github.com/eea/odfpy/blob/574f0fafad73a15a5b11b115d94821623274b4b0/examples/datatable.py#L23
            """
            valuetypeConfig = {valuetype: "string"}
            if isinstance(val, str): valuetypeConfig = {"valuetype": "string"}
            if isinstance(val, int): valuetypeConfig = {"valuetype": "float"}
            if isinstance(val, float): valuetypeConfig = {"valuetype": "float"}
            if isinstance(val, bool): valuetypeConfig = {"valuetype": "boolean"}
            if isinstance(val, datetime): valuetypeConfig = {"valuetype": "date"}
            return valuetypeConfig

        # create column headers
        columns = {header: TableColumn(defaultcellstylename=header) for header in headers}
        headerRow = TableRow()
        for col in columns:
            table.addElement(columns[col])
            cell = TableCell(**valuetype(col), value=col)
            cell.addElement(P(text=col))
            headerRow.addElement(cell)
        table.addElement(headerRow)
        for d in lod:
            row = TableRow()
            for col in columns:
                value = d.get(col)
                if value:
                    cell = TableCell(**valuetype(value), value=value)
                    cell.addElement(P(text=value))
                else:
                    cell = TableCell()
                row.addElement(cell)
            table.addElement(row)
        return table

    def addTable(self, data, toTableCallback: callable, **kwargs):
        """
        add the given data as table to the document

        Args:
            data: data that should be added to the document as table
            toTableCallback: function that converts the data to a Table
            kwargs: additional arguments that are forwarded to the toTableCallback
        """
        if data:
            table = toTableCallback(data, **kwargs)
            self.doc.spreadsheet.addElement(table)

    def saveToFile(self, name: str = None):
        """
        saves the document to a file

        Args:
            name(str): name of the file. If not given the name of the document is used
        """
        if name is None:
            name = self.filename
        self.doc.save(name)

    def toBytesIO(self) -> BytesIO:
        """
        Converts the document into an StringIO stream

        Returns:
            StringIO Stream of the document
        """
        buffer = BytesIO()
        self.doc.write(buffer)
        buffer.seek(0)
        return buffer

    def loadFromFile(self, fileName):
        """
        load the document from the given .ods file
        Args:
            fileName: absolut file path to the file that should be loaded

        Returns:

        """
        self.doc=load(fileName)

    def getLodFromTable(self, name:str):
        """

        Args:
            name: name of the table

        Returns:
            list of dicts containing the values of the table
        """

        table=self._getTable(name)
        if not table:
            return []
        tableRows=table.findall(".//table:table-row", self.prefix_map)
        headers = [cell.get("value") for cell in self._getRowValues(tableRows[0]).values()]
        tableRows=tableRows[1:]
        rows = []
        for tableRow in tableRows:
            row=self._getRowValues(tableRow)
            row={ colName:row.get(col) for col, colName in enumerate(headers)}
            rows.append(row)
        if rows:
            # if col names equal to first row remove first row
            firstRowValues={r.get('value') for r in rows[0].values()}
            if not set(headers) - firstRowValues:
                rows=rows[1:]
        return self._rawTableLoD2LoD(rows)

    def _getTable(self, name:str):
        """
        returns the table in this document identified by the given name
        Args:
            name: name of the table

        Returns:

        """
        xmlDoc=ET.fromstring(self.doc.contentxml())
        table=xmlDoc.find(f".//table:table[@table:name='{name}']", self.prefix_map)
        return table

    def hasTable(self, name:str):
        """
        Checks if the document has a table with the given name
        Args:
            name: name of the table

        Returns:
            True if a table with the given name exists
        """
        table=self._getTable(name)
        return

    def _getRowValues(self, tableRow):
        """
        Converts the given xml ods row into a dict
        Each column is identified by its number and the value contains the cell value and type
        Args:
            tableRow:

        Returns:
            dict
        """
        row = {}
        i=0
        for cell in tableRow.findall(".//table:table-cell", self.prefix_map):
            cellValue = cell.find(".//text:p", self.prefix_map)
            cellRecord = {
                "value": cellValue.text if cellValue is not None else None,
                "valuetype": cell.attrib.get(f"{{{self.prefix_map['office']}}}value-type")
            }
            # table:number-columns-repeated="4" → in this row from the cell i to i+4 have the same value
            repeat = cell.attrib.get(f"{{{self.prefix_map['table']}}}number-columns-repeated")
            if repeat and repeat.isdigit():
                repeat=int(repeat)
            else:
                repeat = 1
            for j in range(repeat):
                row[i+j] = cellRecord
            i+=repeat
        return row

    def _rawTableLoD2LoD(self, data: list):
        res = []
        for rawRow in data:
            row = {}
            for column, valueRecord in rawRow.items():
                if valueRecord:
                    valuetype = valueRecord.get('valuetype')
                    value = valueRecord.get('value')
                    if valuetype == "float":
                        if value.isdigit(): value = int(value)
                        else: value=float(value)
                    if valuetype == "boolean":
                        value = bool(value)
                    if valuetype == "date":
                        value = parser.parse(value)
                    row[column] = value
                else:
                    row[column] = None
            res.append(row)
        return res