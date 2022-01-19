import os

from flask import Blueprint
from lodstorage.jsonable import JSONAble
from lodstorage.query import Query
from lodstorage.sparql import SPARQL


class ProfileBlueprint(object):
    """
    Flask Blueprint providing routes to the profile pages
    """

    def __init__(self, app, name: str, template_folder:str=None, appWrap=None):
        '''
        construct me

        Args:
            name(str): my name
            welcome(str): the welcome page
            template_folder(str): the template folder
        '''
        self.name = name
        if template_folder is not None:
            self.template_folder = template_folder
        else:
            self.template_folder = 'profile'
        self.blueprint = Blueprint(name, __name__, template_folder=self.template_folder,url_prefix="/profile")
        self.app = app
        self.appWrap = appWrap

        @self.blueprint.route('/<wikidataid>')
        def profile(wikidataid: str):
            return self.profile(wikidataid)

        app.register_blueprint(self.blueprint)

    def profile(self, wikidataid:str):
        title = 'Profile'
        template = os.path.join(self.template_folder,"profile.html")
        activeItem = ""
        profile=Profile(wikidataid)
        html = self.appWrap.render_template(template, title=title, activeItem=activeItem, profile=profile)
        return html

class Profile(JSONAble):
    """
    Generates a profile page from a given wikidata id
    """

    def __init__(self, wikidataid:str):
        super().__init__()
        self.wikidataid=wikidataid
        self.fromDict(self.getUserInformation()[0])
        self.ids=self.getIdentifiers()

    def getSamples(self):
        samples = [
            {
                "wikidataid": "Q1910001",
                "firstname": "Matthias",
                "lastname": "Jarke",
                "image": "",
                "dateOfBirth": "1952-05-28",
                "homepage":"",
                "ids":{
                    "GND ID": {
                        "id":"121078221",
                        "url": "https://d-nb.info/gnd/121078221"
                    },
                    "DBLP author ID":{
                        "id":"j/MatthiasJarke",
                        "url":"https://dblp.org/pid/j/MatthiasJarke"
                    },
                    "ORCID iD":{
                        "id":"0000-0001-6169-2942",
                        "url":"https://orcid.org/0000-0001-6169-2942"
                    }
                }

            }
        ]

    @property
    def sparqlEndpoint(self) -> SPARQL:
        return SPARQL("https://query.wikidata.org/sparql")

    def getUserInformation(self) -> dict:
        """
        Retrieves basic information about the user from wikidata that is assigned to the id
        """
        sparql = self.sparqlEndpoint
        query = self.getUserInformationQuery()
        qres = sparql.queryAsListOfDicts(query.query)
        return qres

    def getIdentifiers(self) -> dict:
        """
        Retrieves all identifiers of the user that are assigned to the id

        Returns:
            dict of dict containing the id, idUrl, type of id
        """
        sparql = self.sparqlEndpoint
        query = self.getUserIdentifierQuery()
        qres = sparql.queryAsListOfDicts(query.query)
        ids = {}
        for record in qres:
            ids[record.get("propertyLabel")]={
                "id": record.get("id"),
                "url": record.get("idUrl")
            }
        return ids

    def getUserInformationQuery(self) -> Query:
        """
        Returns the query for basic user information
        """
        queryStr = """
        SELECT ?firstname ?lastname ?image ?dateOfBirth ?homepage
        WHERE{
          VALUES ?user {wd:%s}

          ?user wdt:P31 wd:Q5.

          OPTIONAL{ ?user wdt:P735 ?f.
                    ?f rdfs:label ?firstname. 
                   FILTER(lang(?firstname)="en")
          }
          OPTIONAL{ ?user wdt:P734 ?l.
                    ?l rdfs:label ?lastname. 
                   FILTER(lang(?lastname)="en")
          }
          OPTIONAL{ ?user wdt:P18 ?image.}
          OPTIONAL{ ?user wdt:P569 ?dateOfBirth.}
          OPTIONAL{ ?user wdt:P856 ?homepage.}
        }
        """ % self.wikidataid
        query = Query(name="BasicUserInformation", title="Basic wikidata user information", lang="sparql",
                      query=queryStr)
        return query

    def getUserIdentifierQuery(self) -> Query:
        """
        Returns the query for the Identifiers of given human
        """
        queryStr=r"""
        SELECT ?property ?propertyLabel ?id ?idUrl
        WHERE{
          VALUES ?user {wd:%s}
          ?user wdt:P31 wd:Q5.
          ?property wikibase:propertyType wikibase:ExternalId .    
          ?property wikibase:directClaim ?propertyclaim .                                              
          OPTIONAL {?property wdt:P1630 ?formatterURL .}   
          ?user ?propertyclaim ?id .    
          BIND(IF(BOUND(?formatterURL), IRI(REPLACE(?formatterURL, "\\$1", ?id)) , "") AS ?idUrl) 
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } 
        }""" % self.wikidataid
        query = Query(name="UserIdentifiers", title="The Identifiers of given human", lang="sparql",
                      query=queryStr)
        return query

    def getIdIcon(self, idType):
        """
        Returns a url to the icon of the given id
        """
        iconMap = {
            "GND ID":"https://gnd.network/SiteGlobals/Frontend/gnd/Images/faviconGND.png?__blob=normal&v=5",
            "ORCID iD":"https://orcid.org/assets/vectors/orcid.logo.icon.svg",
            "DBLP author ID": "https://dblp.org/img/favicon.ico",
            "Twitter username": "https://upload.wikimedia.org/wikipedia/commons/4/4f/Twitter-logo.svg",
            "GitHub username": "https://github.githubassets.com/favicons/favicon.svg",
            "ISNI": "https://isni.oclc.org:2443/isni/psi_images/img_psi/3.0/logos/logo_xml_isni.png",
            "Google Scholar author ID":"google-scholar",
            "ACM Digital Library author ID":"acm",
            "Scopus author ID":"scopus",
            "WorldCat Identities ID":"https://upload.wikimedia.org/wikipedia/commons/a/a8/WorldCat_logo.svg",
            "LibraryThing author ID":"https://image.librarything.com/pics/LT-logo-square-75-bw-w2.png",
            "Dimensions author ID":"https://cdn-app.dimensions.ai/static/d8b0339df3b57265d674.png",
            "GEPRIS person ID":"https://gepris.dfg.de/gepris/images/GEPRIS_Logo.png",
            "Wikimedia username":"https://upload.wikimedia.org/wikipedia/commons/8/81/Wikimedia-logo.svg",
            "Mendeley person ID":"mendeley",
            "ResearchGate profile ID":"researchgate",
            "Publons author ID":"https://publons.com/static/images/logos/square/blue_white_shadow.png",
            "OpenReview.net profile ID":"https://openreview.net/images/openreview_logo_512.png",
            "Library of Congress authority ID":"https://loc.gov/static/images/logo-loc-new-branding.svg"
        }
        iconId = iconMap.get(idType)
        if iconId is not None:
            if iconId.startswith("http"):
                return f'<img src="{ iconId }"   alt="" style="max-width:50px;">'
            else:
                return f'<i class="ai ai-{ iconId } ai-3x"></i>'
        return ""