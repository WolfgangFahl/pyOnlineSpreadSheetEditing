"""
Created on 09.12.2021

@author: wf
"""
import copy
import getpass
import os

from lodstorage.lod import LOD
from lodstorage.query import Query
from lodstorage.sparql import SPARQL
from spreadsheet.tableediting import SpreadSheetType
from wikibot3rd.wikiuser import WikiUser

from onlinespreadsheet.tablequery import QueryType, TableQuery
from ngwidgets.basetest import Basetest


class TestTableQuery(Basetest):
    """
    test table query handling
    """

    @classmethod
    def setUpClass(cls):
        super(TestTableQuery, cls).setUpClass()
        cls.user = getpass.getuser()

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        

    @classmethod
    def getSMW_WikiUser(cls, wikiId="smw"):
        """
        get semantic media wiki users for SemanticMediawiki.org and openresearch.org

        Args:
            wikiId(str): the wikiId to get the Semantic MediaWiki user for
        """
        iniFile = WikiUser.iniFilePath(wikiId)
        wikiUser = None
        if not os.path.isfile(iniFile):
            wikiDict = None
            if wikiId == "smwcopy":
                wikiDict = {
                    "wikiId": wikiId,
                    "email": "webmaster@bitplan.com",
                    "url": "http://smw.bitplan.com",
                    "scriptPath": "/",
                    "version": "MediaWiki 1.35.0",
                }
            if wikiId == "smw":
                wikiDict = {
                    "wikiId": wikiId,
                    "email": "webmaster@semantic-mediawiki.org",
                    "url": "https://www.semantic-mediawiki.org",
                    "scriptPath": "/w",
                    "version": "MediaWiki 1.31.16",
                }
            if wikiId == "or":
                wikiDict = {
                    "wikiId": wikiId,
                    "email": "webmaster@openresearch.org",
                    "url": "https://www.openresearch.org",
                    "scriptPath": "/mediawiki/",
                    "version": "MediaWiki 1.31.1",
                }
            if wikiId == "orclone":
                wikiDict = {
                    "wikiId": wikiId,
                    "email": "webmaster@openresearch.org",
                    "url": "https://confident.dbis.rwth-aachen.de",
                    "scriptPath": "/or/",
                    "version": "MediaWiki 1.35.5",
                }
            wikiDict["user"] = f"{cls.user}"
            if wikiDict is None:
                raise Exception(f"{iniFile} missing for wikiId {wikiId}")
            else:
                wikiUser = WikiUser.ofDict(wikiDict, lenient=True)
                if Basetest.inPublicCI():
                    wikiUser.save()
        else:
            wikiUser = WikiUser.ofWikiId(wikiId, lenient=True)
        return wikiUser

    def getTableQuery(self):
        wikiId = "smw"
        # make sure wiki user is available
        TestTableQuery.getSMW_WikiUser(wikiId)
        self.askQueries = [
            {"name": "eventseries", "ask": "[[SMWCon]]|mainlabel='pageTitle'"},
            {
                "name": "events",
                "ask": """{{#ask: [[isA::Conference]][[Has Wikidata item ID::+]]|mainlabel='pageTitle'
|?Has Wikidata item ID=wikidataid
|?Has planned finish=endDate
|?Has planned start=startDate
|format=table
}}""",
            },
        ]
        tq = TableQuery()
        tq.fromAskQueries(wikiId=wikiId, askQueries=self.askQueries)
        return tq

    def documentQueryResult(self, query: Query, qlod: list, show=True):
        """ """
        for tablefmt in ["mediawiki", "github", "latex"]:
            lod = copy.deepcopy(qlod)
            qdoc = query.documentQueryResult(lod, tablefmt=tablefmt)
            if show:
                print(qdoc.asText())

    def testTableQuery(self):
        """
        test table query handling
        """
        tq = self.getTableQuery()
        self.assertEqual(2, len(tq.queries))
        self.assertFalse(tq.tableEditing is None)
        lods = tq.tableEditing.lods
        if len(lods) != 2:
            print(lods)
        self.assertEqual(2, len(lods))
        debug = self.debug
        debug = True
        for query in tq.queries.values():
            qlod = tq.tableEditing.lods[query.name]
            if debug:
                print(len(qlod))
                print(qlod)
            self.documentQueryResult(query, qlod, show=True)
        for askQuery in self.askQueries:
            name = askQuery["name"]
            self.assertTrue(name in lods)
            lod = lods[name]
            if debug:
                print(len(lod))
                print(lod)
            if name == "events":
                self.assertTrue(len(lod) >= 18)

    def testSpreadSheetFromTableQuery(self):
        """
        test creating a spreadSheet from a table Query
        """
        tq = self.getTableQuery()
        name = "testSMWCon"
        s = tq.tableEditing.toSpreadSheet(
            spreadSheetType=SpreadSheetType.EXCEL, name=name
        )
        self.assertTrue(s is not None)
        debug = self.debug
        # debug=True
        if debug:
            print(type(s))
        # TODO add test
        pass

    def testSPARQLQuery(self):
        """
        test SPARQL Query support
        """
        testQueries = [
            {
                "endpoint": "https://query.wikidata.org/sparql",
                "prefixes": ["http://www.wikidata.org/entity/"],
                "lang": "sparql",
                "name": "CityTop10",
                "title": "Ten largest cities of the world",
                "description": "Wikidata SPARQL query showing the 10 most populated cities of the world using the million city class Q1637706 for selection",
                "query": """# Ten Largest cities of the world 
# WF 2021-08-23
# see also http://wiki.bitplan.com/index.php/PyLoDStorage#Examples
# see also https://github.com/WolfgangFahl/pyLoDStorage/issues/46
SELECT DISTINCT ?city ?cityLabel ?population ?country ?countryLabel 
WHERE {
  VALUES ?cityClass { wd:Q1637706}.
  ?city wdt:P31 ?cityClass .
  ?city wdt:P1082 ?population .
  ?city wdt:P17 ?country .
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY DESC(?population)
LIMIT 10""",
            }
        ]
        tq = TableQuery()
        for queryMap in testQueries:
            endpointUrl = queryMap.pop("endpoint")
            query = Query(**queryMap)
            query.tryItUrl = endpointUrl
            query.endpoint = SPARQL(endpointUrl)
            tq.addQuery(query)
        tq.fetchQueryResults()
        lods = tq.tableEditing.lods
        self.assertEqual(1, len(lods))
        qlod = lods["CityTop10"]
        self.assertTrue(len(qlod) == 10)
        citiesByLabel, _dup = LOD.getLookup(qlod, "cityLabel")
        self.assertTrue("Delhi" in citiesByLabel)
        delhi = citiesByLabel["Delhi"]
        self.assertTrue(delhi["population"] > 20000000.0)
        self.documentQueryResult(query, qlod, show=self.debug)

    def testBlazegraph(self):
        """
        testing blazegraph endpoint
        """
        return False
        testQueries = [
            {
                "endpoint": "http://localhost:9999/blazegraph/sparql",
                "prefixes": [],
                "lang": "sparql",
                "name": "TownsInBavaria",
                "title": "Towns in Bavaria",
                "description": "Local Blazegraph  SPARQL query for finding cities",
                "query": """PREFIX unlocode:<http://unlocode.rkbexplorer.com/id/>
PREFIX portal: <http://www.aktors.org/ontology/portal#>
PREFIX support: <http://www.aktors.org/ontology/support#>

SELECT ?townname ?lat ?lon ?regionname ?countryname
WHERE {
  ?town a portal:Town.
  ?town support:has-pretty-name ?townname.
  ?town portal:has-latitude ?lat.
  ?town portal:has-longitude ?lon.
  ?town portal:is-located-in ?region.

  ?region support:has-pretty-name ?regionname.
  ?region portal:is-part-of ?country.

  ?country support:has-pretty-name ?countryname.
 
   FILTER regex(?regionname,"bayern","i")
}
ORDER by ?townname
LIMIT 7
""",
            }
        ]
        tq = TableQuery()
        for queryMap in testQueries:
            endpointUrl = queryMap.pop("endpoint")
            query = Query(**queryMap)
            query.tryItUrl = endpointUrl
            query.endpoint = SPARQL(endpointUrl)
            tq.addQuery(query)
        tq.fetchQueryResults()
        lods = tq.tableEditing.lods
        print(lods)

    def testRESTfulQuery(self):
        """
        tests the handling of RESTful queries in TableQuery
        """
        tq = TableQuery()
        url = "https://conferencecorpus.bitplan.com/eventseries/WEBIST"
        tq.addRESTfulQuery(name="WEBIST", url=url)
        tq.fetchQueryResults()
        if len(tq.errors) > 0:
            error = tq.errors[0]
            if "503" in error:
                print(f"Couldn't test {url} due to a 503 Service Unavailable status")
                return
        self.assertEquals(0, len(tq.errors))
        self.assertTrue("WEBIST_confref" in tq.tableEditing.lods)
        self.assertTrue(len(tq.tableEditing.lods["WEBIST_confref"]) > 15)

    def testGuessQueryType(self):
        """
        tests guessing the query type
        """
        queries = [
            {
                "type": QueryType.RESTful,
                "query": "http://conferencorpus.bitplan.com/eventseries/WEBIST?format=json",
            },
            {
                "type": QueryType.RESTful,
                "query": "https://conferencorpus.bitplan.com/eventseries/WEBIST?format=json",
            },
            {
                "type": QueryType.ASK,
                "query": "{{#ask: [[Concept:Event series]][[EventSeries acronym::WEBIST]]|mainlabel=pageTitle }}",
            },
            {"type": QueryType.SPARQL, "query": "SELECT ?s ?p ?o WHERE{ ?s ?p ?o }"},
            {
                "type": QueryType.SPARQL,
                "query": """# SPARQL query
# Ten Largest cities of the world 
# WF 2021-08-23
# see also http://wiki.bitplan.com/index.php/PyLoDStorage#Examples
# see also https://github.com/WolfgangFahl/pyLoDStorage/issues/46
SELECT DISTINCT ?city ?cityLabel ?population ?country ?countryLabel 
WHERE {
  VALUES ?cityClass { wd:Q1637706}.
  ?city wdt:P31 ?cityClass .
  ?city wdt:P1082 ?population .
  ?city wdt:P17 ?country .
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY DESC(?population)
LIMIT 10""",
            },
            {"type": QueryType.SQL, "query": "SELECT * FROM Event"},
            {
                "type": QueryType.SQL,
                "query": "SELECT name, firstname, count(children) FROM Event",
            },
            {"type": QueryType.INVALID, "query": "# This is not a proper query"},
        ]
        for i, record in enumerate(queries):
            query = record.get("query")
            guessedType = TableQuery.guessQueryType(query)
            expectedType = record.get("type")
            if guessedType != expectedType:
                print(f"query {i} not guessed correctly: {query}")
            self.assertEqual(expectedType, guessedType)
