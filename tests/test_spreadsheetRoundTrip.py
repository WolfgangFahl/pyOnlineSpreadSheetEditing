from unittest import TestCase
from tempfile import TemporaryDirectory
from datetime import datetime, date
from spreadsheet.spreadsheet import OdsDocument, ExcelDocument
from tests.basetest import BaseTest

class TestSpreadsheetRoundtrip(BaseTest):
    '''
    Tests roundtrip from dict to Spreadsheet and Back
    '''

    def setUp(self) -> None:
        BaseTest.setUp(self)
        self.tmpDir = TemporaryDirectory(prefix=self.__class__.__name__)
        self.testLoD=[
            {
                "name":"Jon",
                "lastname":"Doe"
            },
            {
                "name":"Bob",
                "lastname":"Doe",
                "modificationDate":datetime.now(),
                "dept":234.23
            },
            {
                "name":"Alice",
                "lastname":"Doe",
                "age":2,
                "url":"http://www.opendocumentformat.org/developers"
            },
        ]

    def tearDown(self) -> None:
        self.tmpDir.cleanup()

    def test_lod2table(self):
        """
        tests the roundtrip of LoD → .ods → LoD
        """
        doc=OdsDocument("Test")
        fileName = f"{self.tmpDir.name}/{doc.filename}"
        doc.addTable(self.testLoD, OdsDocument.lod2Table, name="Persons")
        doc.saveToFile(fileName)
        docReloaded=OdsDocument("TestReloaded")
        docReloaded.loadFromFile(fileName)
        extractedData=docReloaded.getLodFromTable("Persons")
        for i, record in enumerate(self.testLoD):
            for key,expectedValue in record.items():
                self.assertEqual(expectedValue, extractedData[i].get(key))

class TestExcelDocument(TestCase):

    def setUp(self) -> None:
        self.tmpDir = TemporaryDirectory(prefix=self.__class__.__name__)
        self.testLoD=[
            {
                "name":"Jon",
                "lastname":"Doe"
            },
            {
                "name":"Bob",
                "lastname":"Doe",
                "modificationDate":date(year=2021, month=12, day=2),
                "dept":234.23
            },
            {
                "name":"Alice",
                "lastname":"Doe",
                "age":2,
                "url":"http://www.opendocumentformat.org/developers"
            },
        ]
        self.samples=samples={
            "Persons":self.testLoD,
            "Persons2": self.testLoD
        }

    def tearDown(self) -> None:
        self.tmpDir.cleanup()

    def assertLodEqual(self, expectedLOD, actualLOD):
        """
        Compares the two given list of dicts (LOD) and checks if they are equal.
        Order of the dicts is here relevant for equality.
        Args:
            expectedLOD: expected LOD
            actualLOD: actual LOD
        """
        for i, record in enumerate(expectedLOD):
            for key,expectedValue in record.items():
                self.assertEqual(expectedValue, actualLOD[i].get(key))
                self.assertEqual(type(expectedValue), type(actualLOD[i].get(key)))

    def test_lod2table(self):
        """
        tests the roundtrip of LoD → .xlsx → LoD
        """
        doc=ExcelDocument("Test")
        fileName = f"{self.tmpDir.name}/{doc.filename}"
        doc.addTable("Persons", self.testLoD)
        doc.addTable("Persons2", self.testLoD)
        doc.saveToFile(fileName)
        docReloaded=ExcelDocument("TestReloaded")

        docReloaded.loadFromFile(fileName, samples=self.samples)
        extractedData=docReloaded.getTable("Persons")
        self.assertLodEqual(self.testLoD, extractedData)

    def test_bufferLoading(self):
        """
        test the buffer loading of xlsx documents
        """
        doc = ExcelDocument("Test")
        doc.addTable("Persons", self.testLoD)
        buffer = doc.toBytesIO()
        docReloaded = ExcelDocument("TestReloaded")
        docReloaded.loadFromFile(buffer, self.samples)
        extractedData = docReloaded.getTable("Persons")
        self.assertLodEqual(self.testLoD, extractedData)