"""
Created on 2024-03-18

@author: wf
"""

import sys
from argparse import ArgumentParser

from ngwidgets.cmd import WebserverCmd

from onlinespreadsheet.gsimport import GsImportWebserver


class GoogleSheetWikidataCmd(WebserverCmd):
    """
    Command line tool for managing Google Sheets to Wikidata imports via a web server.
    """

    def getArgParser(self, description: str, version_msg: str) -> ArgumentParser:
        """
        Extend the default argument parser with Google Sheets to Wikidata specific arguments.
        """
        parser = super().getArgParser(description, version_msg)
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Show verbose output [default: %(default)s]",
        )
        parser.add_argument(
            "--url",
            required=True,
            help="URL of the Google Spreadsheet to import from",
        )
        parser.add_argument(
            "--sheets",
            nargs="+",
            required=True,
            help="Names of the sheets to import data from",
        )
        parser.add_argument(
            "--mappingSheet",
            default="WikidataMapping",
            help="Name of the sheet containing Wikidata mappings [default: %(default)s]",
        )
        parser.add_argument(
            "--pk",
            required=True,
            help="Primary key property to use for Wikidata queries",
        )
        parser.add_argument(
            "--endpoint",
            default="https://query.wikidata.org/sparql",
            help="SPARQL endpoint URL [default: %(default)s]",
        )
        parser.add_argument(
            "--lang",
            "--language",
            default="en",
            help="Language to use for labels [default: %(default)s]",
        )
        return parser


def main(argv: list = None):
    """
    Main entry point for the command-line tool.
    """
    cmd = GoogleSheetWikidataCmd(
        config=GsImportWebserver.get_config(),
        webserver_cls=GsImportWebserver,
    )
    exit_code = cmd.cmd_main(argv)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
