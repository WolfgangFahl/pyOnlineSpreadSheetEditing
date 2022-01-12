import io
import math
import os
import dateutil.parser as dateparser
import pandas as pd


from io import BytesIO
from enum import Enum,auto
from zipfile import ZipFile
from lodstorage.csv import CSV
from pandas import Timestamp, NaT
from datetime import datetime, date
from werkzeug.datastructures import FileStorage

    
class Format:
    '''
    potential Formats 
    '''
    formatMap={
        "CSV": {
            "name": "CSV",
            "title": "Comma separated Values",
            "postfix": ".csv",
            "mimetype": "text/csv"
            
        },
        "EXCEL": {
            "name": "Excel",
            "title": "Microsoft Excel",
            "postfix": ".xlsx",
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        },
        "JSON": {
            "name": "JSON",
            "title": "Javascript Simple Object Notation",
            "postfix": ".json",
            "mimetype": "application/json"
        },
        "ODS": {
            "name": "ODS",
            "title": "OpenDocument Spreadsheet",
            "postfix": ".ods",
            "mimetype": "application/vnd.oasis.opendocument.onlinespreadsheet"
        }
        
    }    
class SpreadSheetType(Enum):
    '''
    Entities of openresearch.
    Used to specify for a fixer the domain of operation.
    '''
    CSV=auto()
    EXCEL=auto()
    ODS=auto()
    JSON=auto()
    
    def getProperty(self,propertyName):
        value=Format.formatMap[self.name][propertyName]
        return value
       
    def getPostfix(self):
        return self.getProperty("postfix")
       
    def getName(self):
        return self.getProperty("name")
    
    def getMimeType(self):
        return self.getProperty("mimetype")
    
    def getTitle(self):
        return self.getProperty("title")
    
    @classmethod
    def asSelectFieldChoices(cls):
        choices=[]
        for i,choice in enumerate(cls):
            choices.append((choice.name,choice.getTitle()))
        return choices


class SpreadSheet:
    '''
    i am onlinespreadsheet
    '''

    FILE_TYPE=NotImplemented
    MIME_TYPE=NotImplemented
    
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
            spreadSheetType(SpreadSheetType): the type of onlinespreadsheet to create
            name(str): the name of the onlinespreadsheet
        
        '''
        spreadSheet=None
        if spreadSheetType==SpreadSheetType.EXCEL:
            spreadSheet=ExcelDocument(name=name)
        elif spreadSheetType==SpreadSheetType.ODS:
            spreadSheet=OdsDocument(name=name)
        elif spreadSheetType==SpreadSheetType.CSV:
            spreadSheet=CSVSpreadSheet(name=name)
        return spreadSheet

    @classmethod
    def load(cls, document):
        """
        Tries to load the given document as SpreadSheet
        Args:
            document: onlinespreadsheet document to load

        Returns:
            SpreadSheet
        """
        documentSpreadSheetType=None
        documentName=""
        spreadsheet = None
        # TODO - use SpreadSheeeType enum instead
        spreadSheetTypes=[OdsDocument, ExcelDocument, CSVSpreadSheet]
        if isinstance(document, FileStorage):
            document.stream.seek(0)
            for spreadSheetType in spreadSheetTypes:
                if document.filename.endswith(spreadSheetType.FILE_TYPE):
                    documentName=document.filename[:-len(spreadSheetType.FILE_TYPE)]
                    documentSpreadSheetType=spreadSheetType
                    break
        elif isinstance(document, io.BytesIO) or isinstance(document, io.StringIO) or isinstance(document, io.TextIOWrapper):
            document.seek(0)
            for spreadSheetType in spreadSheetTypes:
                if document.name.endswith(spreadSheetType.FILE_TYPE):
                    documentName=document.name[:-len(spreadSheetType.FILE_TYPE)]
                    documentSpreadSheetType=spreadSheetType
                    break
        elif isinstance(document, str):
            try:
                buffer=None
                with open(document, "rb") as f:
                    buffer = io.BytesIO(f.read())
                    buffer.name=document
                return cls.load(buffer)
            except Exception as e:
                print(e)
                raise e
        else:
            print("Unable to load SpreadSheet")
            return None
        if documentSpreadSheetType:
            spreadsheet = documentSpreadSheetType(name=documentName)
            spreadsheet.loadFromFile(document)
        return spreadsheet
    
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

    def hasTable(self, name:str):
        """
        Checks if table under given name exists

        Args:
            name(str): name of the Table

        Retruns:
            True if table exists otherwise False
        """
        return name in self.tables

    def saveToFile(self, fileName:str=None, dir_name:str=None):
        """
        saves SpreadSheet to file

        Args:
            fileName(str): name of the file if None SpreadSheet name is used
            dir_name(str): name of directory to store the file

        Returns:
            Nothing
        """
        if fileName is None:
            fileName=self.filename
        if dir_name is not None:
            fileName=os.path.join(dir_name, fileName)
        documentBuffer=self.toBytesIO()
        with open(fileName, "wb") as f:
            documentBuffer.seek(0)
            f.write(documentBuffer.read())

    def toBytesIO(self) -> BytesIO:
        """
        Converts the document into an BytesIO stream

        Returns:
            BytesIO Stream of the document
        """
        raise NotImplementedError

    def loadFromFile(self, file, samples:dict=None):
        """
        Load SpreadSheet from given file or file object
        """
        tables=self._loadFromFile(file)
        if tables:
            for name,table in tables.items():
                if samples:
                    if name in samples:
                        self.fixLodTypes(table, samples[name])
                self.tables[name]=table
            
    def _loadFromFile(self, file):
        """
        load the document from the given .ods file
        Args:
            file: absolut file path to the file that should be loaded
            samples(dict): samples of the sheets. Expected format: sheetName:SamplesForSheet
        Returns:

        """
        if isinstance(file, str):
            try:
                with open(file, mode="rb") as f:
                    buffer=BytesIO()
                    buffer.write(f.read())
                    # work around along the line of
                    # https://stackoverflow.com/a/42811024/1497139
                    buffer.name=f.name
            except Exception as e:
                print(f"Tried to open {file} as a File and failed")
                raise e
        else:
            buffer=file
        return self._loadFromBuffer(buffer)

    def _loadFromBuffer(self, buffer):
        """
        Load SpreadSheet from given buffer

        Args:
            buffer: file like object

        """
        raise NotImplementedError

    @property
    def filename(self):
        return self.name + self.FILE_TYPE

    @staticmethod
    def fixLodTypes(lod: list, samples: list, typeConversionMap: dict = None):
        """
        Fixes the types of the values of the given lod by converting it to the type corresponding to the given sampeles

        Args:
            lod(list): List of dicts to be type fixed
            samples(list): list of samples specifying the value types
            typeConversionMap(dict): Map from type to corresponding conversion function. If None default conversions for string values are used.
        """
        if typeConversionMap is None:
            def toDate(value):
                if isinstance(value, str):
                    return dateparser.parse(value).date()
                elif isinstance(value, datetime):
                    return value.date()
                elif isinstance(value, date):
                    return value
                else:
                    print(f"{value} could not be converted to date")
                    return value
            typeConversionMap = {
                str:      lambda value: str(value),
                int:      lambda value: int(value),
                float:    lambda value: float(value),
                date:     lambda value: toDate(value),
                datetime: lambda value: dateparser.parse(value)
            }
        # build sample types map
        sampleTypes = {}
        for sample in samples:
            if isinstance(sample, dict):
                for key, value in sample.items():
                    valueType = type(value)
                    if key not in sampleTypes:
                        sampleTypes[key] = valueType
                    elif sampleTypes[key] != valueType:
                        print(f"Sample has inconsistent types for {key} the types {sampleTypes[key]} and {valueType} are defined")
                    else:
                        pass
        # fix types of lod
        for d in lod:
            if isinstance(d, dict):
                for key, value in d.items():
                    if value is not None and key in sampleTypes and sampleTypes[key] in typeConversionMap:
                        if type(value) != sampleTypes[key]:
                            d[key] = typeConversionMap[sampleTypes[key]](value)
            else:
                print("List of dicts contains a non dict item")

    
class CSVSpreadSheet(SpreadSheet):
    '''
    CSV Spreadsheet packaging as ZIP file of CSV files
    '''

    FILE_TYPE = '.zip'
    TABLE_TYPE = '.csv'
    MIME_TYPE = 'application/zip'

    def __init__(self, name: str):
        super().__init__(name=name, spreadSheetType=SpreadSheetType.CSV)

    def toBytesIO(self) -> BytesIO:
        """
        Converts the document into an BytesIO stream

        Returns:
            BytesIO Stream of the document
        """
        buffer = BytesIO()
        buffer.name=self.filename
        with ZipFile(buffer, mode="w") as documentZip:
            for tableName, table in self.tables.items():
                csv=CSV.toCSV(table)
                documentZip.writestr(tableName+self.TABLE_TYPE, csv)
        buffer.seek(0)
        return buffer

    def _loadFromBuffer(self, file):
        """
        load the document from the given .zip file
        Args:
            file: absolut file path to the file that should be loaded
        Returns:

        """
        fileName=file.name
        tables={}
        if fileName.endswith(self.FILE_TYPE):
            with ZipFile(file, mode="r") as documentZip:
                archivedFiles=documentZip.namelist()
                for archivedFile in archivedFiles:
                    with documentZip.open(archivedFile) as csvFile:
                        lod = CSV.fromCSV(csvFile.read().decode())
                        tableName=archivedFile[:-len(self.TABLE_TYPE)]
                        tables[tableName] = lod
        elif fileName.endswith(self.TABLE_TYPE):
            #single csv file load as sheet with one table
            lod = CSV.fromCSV(file.read().decode())
            tableName = fileName[:-len(self.TABLE_TYPE)]
            tables[tableName] = lod
        return tables


class ExcelDocument(SpreadSheet):
    """
    Provides methods to convert LoDs to an excel document and vice versa
    """

    FILE_TYPE = '.xlsx'
    MIME_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def __init__(self, name: str, engine:str=None,spreadSheetType:SpreadSheetType=SpreadSheetType.EXCEL):
        """
        Args:
            name(str): name of the document
        """
        super().__init__(name=name, spreadSheetType=spreadSheetType)
        if engine is None:
            engine="xlsxwriter"
        self.engine=engine
        
    def toBytesIO(self) -> BytesIO:
        """
        Converts the document into an BytesIO stream

        Returns:
            BytesIO Stream of the document
        """
        buffer = BytesIO()
        with pd.ExcelWriter(buffer,
                            engine=self.engine,
                            engine_kwargs={
                                'options': {
                                    'strings_to_numbers': True
                                }
                            },
                            ) as writer:
            for tableName, tableData in self.tables.items():
                df = pd.DataFrame(tableData)
                df.to_excel(writer,
                            sheet_name=tableName,
                            index=False)
        buffer.seek(0)
        buffer.name=self.filename
        return buffer

    def _loadFromBuffer(self,buffer):
        '''
        read my table from the given BytesIO buffer
        '''
        sheets = pd.read_excel(buffer, sheet_name=None).keys()
        tables={}
        for sheet in sheets:
            df = pd.read_excel(buffer, sheet_name=sheet, na_values=None)
            df=df.where(pd.notnull(df), None)
            lod=df.to_dict('records')
            # NaT handling issue due to a bug in pandas https://github.com/pandas-dev/pandas/issues/29024
            lod=[{k: v.to_pydatetime() if isinstance(v, Timestamp) else None if isinstance(v, type(NaT)) else v for k,v in d.items()} for d in lod]
            # float nan to None
            lod=[{k:v if not (isinstance(v, float) and math.isnan(v)) else None for k,v in d.items() }for d in lod]
            tables[sheet] = lod
        return tables

class OdsDocument(ExcelDocument):
    """
    OpenDocument Spreadsheet that can store multiple tables.
    Provides functions to traverse between LoD and ODS document
    """

    FILE_TYPE = '.ods'
    MIME_TYPE = 'application/vnd.oasis.opendocument.onlinespreadsheet'

    def __init__(self, name: str):
        """
        Args:
            name(str): name of the document
        """
        super().__init__(name=name, spreadSheetType=SpreadSheetType.ODS, engine="odf")

