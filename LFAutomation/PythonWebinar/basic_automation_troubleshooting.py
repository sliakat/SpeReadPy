"""Basic Automation Troubleshooting

This script is a barebones LightField Automation instance launcher.
It should be used for troubleshooting package pre-requisites and other
possible issues (i.e antivirus conflicts) with connections to
inter-process communication (IPC) ports.

The user should first run the script as-is to see if an automation
instance launches. If so, they can add code line-by-line until the
troublesome code is identified.

----
Notes:
----
- .NET Framework 4 is required to run LightField and perform automation
- The pythonnet package is required to automate in Python. The clr import
(common language runtime) comes from pythonnet.
-- pip install pythonnet
"""

import os
import sys
import clr
from System import String
from System.Collections.Generic import List
# TODO: Add imports to identify those that may be causing problems.


sys.path.append(os.environ['LIGHTFIELD_ROOT'])
sys.path.append(os.environ['LIGHTFIELD_ROOT']+"\\AddInViews")
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

from PrincetonInstruments.LightField.Automation import Automation

if __name__ == '__main__':
    auto = Automation(True, List[String]())
    # TODO: Add lines to identify automation issues.
    input('Press Enter key to dispose the automation instance and'
        ' exit script.\n')
    auto.Dispose()
