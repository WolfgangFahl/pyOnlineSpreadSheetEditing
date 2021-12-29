import io
from tempfile import TemporaryDirectory
from datetime import datetime, date
from lodstorage.csv import CSV
from spreadsheet.spreadsheet import OdsDocument, ExcelDocument, SpreadSheet, CSVSpreadSheet
from tests.basetest import BaseTest


class TestSpreadSheet(BaseTest):
    """
    tests SpreadSheet
    """

    def setUp(self,debug=False,profile=True):
        BaseTest.setUp(self, debug=debug, profile=profile)
        self.tmpDir = TemporaryDirectory(prefix=self.__class__.__name__)
        self.testLoD = [
            {
                "name": "Jon",
                "lastname": "Doe",
                "birthDay":date(year=2021, month=12, day=2),
            },
            {
                "name": "Bob",
                "lastname": "Doe",
                "modificationDate": datetime(year=2021, month=12, day=2, hour=12),
                "dept": 234.23
            },
            {
                "name": "Alice",
                "lastname": "Doe",
                "age": 2,
                "url": "http://www.opendocumentformat.org/developers"
            },
        ]
        self.samples = samples = {
            "Persons": self.testLoD,
            "Persons2": self.testLoD
        }

    def tearDown(self):
        BaseTest.tearDown(self)
        self.tmpDir.cleanup()

    def assertLodEqual(self, expectedLOD, actualLOD, checkType:bool=True, errMsg:str=None):
        """
        Compares the two given list of dicts (LOD) and checks if they are equal.
        Order of the dicts is here relevant for equality.
        Args:
            expectedLOD: expected LOD
            actualLOD: actual LOD
        """
        for i, record in enumerate(expectedLOD):
            for key,expectedValue in record.items():
                self.assertEqual(expectedValue, actualLOD[i].get(key), errMsg)
                if checkType:
                    self.assertEqual(type(expectedValue), type(actualLOD[i].get(key)), errMsg)

    def testRoundTrip(self):
        """
        tests the onlinespreadsheet round trip for all SpreadSheet types
        """
        spreadSheetTypes={OdsDocument,ExcelDocument, CSVSpreadSheet}
        for spreadSheetType in spreadSheetTypes:
            doc = spreadSheetType("Test")
            fileName = f"{self.tmpDir.name}/{doc.filename}"
            doc.addTable("Persons", self.testLoD)
            doc.addTable("Persons2", self.testLoD)
            doc.saveToFile(fileName)

            docReloaded = spreadSheetType("TestReloaded")
            docReloaded.loadFromFile(fileName, samples=self.samples)
            extractedData = docReloaded.getTable("Persons")
            self.assertLodEqual(self.testLoD, extractedData, errMsg=f"when testing {spreadSheetType.__name__}")

    def testLoading(self):
        """"
        tests the loading of a onlinespreadsheet file
        """
        spreadSheetTypes = {OdsDocument, ExcelDocument, CSVSpreadSheet}
        for spreadSheetType in spreadSheetTypes:
            # creating a onlinespreadsheet file
            doc = spreadSheetType("Test")
            fileName = f"{self.tmpDir.name}/{doc.filename}"
            doc.addTable("Persons", self.testLoD)
            doc.addTable("Persons2", self.testLoD)
            doc.saveToFile(fileName)
            # loading the file without specifying the type
            docReloaded = SpreadSheet.load(fileName)
            # test loading
            self.assertIsInstance(docReloaded, spreadSheetType, f"when testing {spreadSheetType.__name__}")
            self.assertTrue(len(docReloaded.tables)==2, f"when testing {spreadSheetType.__name__}")

            # test loading of BytesIO document
            docReloaded = SpreadSheet.load(doc.toBytesIO())
            self.assertIsInstance(docReloaded, spreadSheetType, f"when testing {spreadSheetType.__name__}")
            self.assertTrue(len(docReloaded.tables) == 2, f"when testing {spreadSheetType.__name__}")

    def testCSV(self):
        """tests csv archive roundtrip"""
        doc=CSVSpreadSheet(name="csvTest")
        doc.addTable("Persons", self.testLoD)
        buffer=doc.toBytesIO()
        with open(f"{self.tmpDir.name}/{buffer.name}", mode="wb") as f:
            buffer.seek(0)
            f.write(buffer.read())
        docReloaded=CSVSpreadSheet("csvReloaded")
        docReloaded.loadFromFile(f"{self.tmpDir.name}/{buffer.name}", samples=self.samples)
        self.assertEqual(len(docReloaded.tables['Persons']),len(self.testLoD))

    def testCsvLoadingOfCsv(self):
        """
        tests tha loading of a given csv file
        """
        csvStr=CSV.toCSV(self.testLoD)
        buffer=io.BytesIO(initial_bytes=csvStr.encode())
        buffer.name="Persons.csv"
        spreadsheet=CSVSpreadSheet("PersonTest")
        spreadsheet.loadFromFile(buffer, samples=self.samples)
        self.assertTrue("Persons" in spreadsheet.tables)
        self.assertLodEqual(self.testLoD, spreadsheet.tables["Persons"])

