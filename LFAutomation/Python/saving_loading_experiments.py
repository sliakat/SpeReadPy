# Import the .NET class library
import clr

# Import python sys module
import sys

# Import os module
import os

# Import System.IO for saving and opening files
from System.IO import *

# Import c compatible List and String
from System import String
from System.Collections.Generic import List

# Add needed dll references
sys.path.append(os.environ['LIGHTFIELD_ROOT'])
sys.path.append(os.environ['LIGHTFIELD_ROOT']+"\\AddInViews")
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

# PI imports
from PrincetonInstruments.LightField.Automation import Automation


def save_experiment(experiment_name):
    # Save PI Experiment for future use
    experiment.SaveAs(experiment_name)


def print_savedexperiments():
    # Print a list (of type string) of saved experiments
    print ("My Saved Experiments:")    
    for savedexperiment in experiment.GetSavedExperiments():
        print ("\t" + savedexperiment)



# Create the LightField Application (true for visible)
# The 2nd parameter forces LF to load with no experiment 
auto = Automation(True, List[String]())

# Get experiment object
experiment = auto.LightFieldApplication.Experiment

# Save these new settings as an experiment
save_experiment("PI_Sample_Saved_Experiment")

# Print all saved experiments
print_savedexperiments()



# Result: will save an experiment and print saved experiments








