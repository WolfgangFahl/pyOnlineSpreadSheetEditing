"""
Created on 2022-03-06

@author: wf
"""

from dataclasses import dataclass

import onlinespreadsheet


@dataclass
class Version:
    """
    Version handling for pyOnlineSpreadsheetEditing
    """

    name = "pyOnlineSpreadsheetEditing"
    version = onlinespreadsheet.__version__
    date = "2021-12-11"
    updated = "2024-08-22"
    description = "python Online SpreadSheet Editing tool with configurable enhancer/importer and check phase"
    authors = "Wolfgang Fahl/Tim Holzheim"
    doc_url = "https://wiki.bitplan.com/index.php/PyOnlineSpreadSheetEditing"
    chat_url = "https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing/discussions"
    cm_url = "https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing"

    license = f"""Copyright 2021-2024 contributors. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied."""
    longDescription = f"""{name} version {version}
{description}

  Created by {authors} on {date} last updated {updated}"""
