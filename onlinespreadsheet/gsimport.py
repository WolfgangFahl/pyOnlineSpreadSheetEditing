"""
Created on 2024-03-18

@author: wf
"""
from ngwidgets.input_webserver import InputWebserver, InputWebSolution
from ngwidgets.webserver import WebserverConfig
from nicegui.client import Client

from onlinespreadsheet.version import Version

# from onlinespreadsheet.wdgrid import WikidataGrid, GridSync


class GsImportWebserver(InputWebserver):
    """
    scholary knowledge graph browser
    """

    @classmethod
    def get_config(cls) -> WebserverConfig:
        copy_right = "(c)2022-2024 Wolfgang Fahl"
        config = WebserverConfig(
            copy_right=copy_right,
            version=Version(),
            default_port=8765,
            short_name="gsimport",
        )
        server_config = WebserverConfig.get(config)
        server_config.solution_class = GsImportSolution
        return server_config

    def __init__(self):
        """Constructs all the necessary attributes for the WebServer object."""
        config = GsImportWebserver.get_config()
        InputWebserver.__init__(self, config=config)


class GsImportSolution(InputWebSolution):
    """
    the google spreadsheet import solution
    """

    def __init__(self, webserver: GsImportWebserver, client: Client):
        """
        Initialize the solution

        Calls the constructor of the base solution
        Args:
            webserver (GsImportWebserver): The webserver instance associated with this context.
            client (Client): The client instance this context is associated with.
        """
        super().__init__(webserver, client)  # Call to the superclass constructor
        # self.wdgrid: WikidataGrid = None
        # self.gridSync: GridSync = None

    def show_ui(self):
        """
        show my user interface
        """

    async def home(
        self,
    ):
        """Generates the home page with a selection of examples and
        svg display
        """
        await self.setup_content_div(self.show_ui)
