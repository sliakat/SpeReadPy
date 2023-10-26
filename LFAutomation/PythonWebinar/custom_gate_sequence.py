"""Application example: Custom gate sequence

Demonstrates a use case for a custom gating sequence on an ICCD
(PI-MAX3 / PI-MAX4) where repetitive gate delays are changed online
during asynchronous acquisition. This concept can be used to achieve
non-linear (i.e. logarithmic) gate sweeps inside a single acquisition.
This example will specifically demonstrate a spline interpolated sweep
where the majority of steps are taken close to the starting delay.a

The script contains all necessary imports and a __main__ block, so it
can be run as-is through a terminal or IDE, provided all the necessary
packages are in the user's virutal environment and LightField is properly
installed on the PC the script is being executed on.

Ther user should adjust the user inputs to suit their application before
running the script.

Please reference the
'LightField Add-ins and Automation Programming Manual.pdf' in your
'C:\\ProgramData\\Documents\\Princeton Instruments\\LightField\\
Add-in and Automation SDK\\' folder
for more information on the automation objects referenced here.

Author: Sabbir Liakat, Teledyne Princeton Instruments
*This is a personal example and not an official Teledyne sample.*
"""
from typing import Any, List, Optional, Self, Tuple, Type

## USER INPUTS
# TODO: change these inputs as needed for your application
ICCD_SERIAL_NUMBER: Optional[str] = None
# large gate delays are used here for easy validation through time stamps
START_GATE_DELAY_NS: float = 100.e6
END_GATE_DELAY_NS: float = 1000.e6
NUM_STEPS: int = 20
#
##

import os
import sys
from threading import Event, Lock
from types import TracebackType

import numpy as np
import clr

from System import Boolean, String, IntPtr, Int64, Double
from System.Collections.Generic import List as NETList

# Add needed dll references
sys.path.append(os.environ['LIGHTFIELD_ROOT'])
sys.path.append(os.environ['LIGHTFIELD_ROOT']+"\\AddInViews")
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

# PI imports
from PrincetonInstruments.LightField.Automation import Automation
from PrincetonInstruments.LightField.AddIns import (CameraSettings, DeviceType,
ExperimentSettings, GatingMode, Pulse, TimeStamps, ReadoutControlMode)

global_thread_event: Event = Event()

#Callback
def experiment_completed(sender: Any, evt_args: Any) -> None:
    """Fires when an asynchronous acquisition is completed."""
    global_thread_event.set()
    print('Experiment completed!')

class ICCDOperator():
    """Hub for the ICCD-focused LightField automation instance.
    Contains methods for experiment validation, setup, and cleanup.

    The constructor spawns a new LightField automation process with
    no experiment loaded. It then looks for available ICCDs. If it finds
    ICCDs, it loads the first one it finds if `ICCD_SERIAL_NUMBER` is not
    None, else it tries to find the ICCD matching `ICCD_SERIAL_NUMBER`.

    -----
    Exceptions:
    -----
    `RuntimeError` is thrown if there are no available ICCDs, or if there
    is at least one available ICCD but none match `ICCD_SERIAL_NUMBER`.

    -----
    Notes:
    -----
    All members will be kept private - the user can use the public
    methods to execute tasks.
    """
    class _IndexManager():
        """Helper class to cache running index"""
        _lock: Lock = Lock()
        _idx_to_use: int = 0
        @property
        def idx_to_use(self) -> int:
            """Index to use for next Pulse"""
            with self._lock:
                return self._idx_to_use
        def increment(self, *, amount: int=1) -> None:
            """Increment index by `amount` (default 1)"""
            with self._lock:
                self._idx_to_use += amount
        def reset(self) -> None:
            "Resets count to 0"
            with self._lock:
                self._idx_to_use = 0
    _automation: Any
    _delay_sequence: List[Pulse] = []
    _experiment: Any
    _iccd_device: Optional[Any] = None
    _iccd_model_strings: Tuple[str,...] = (
        'PI-MAX3', 'PI-MAX4')
    _index_to_use: _IndexManager = _IndexManager()
    def __init__(self) -> None:
        # start the automation engine with no experiment
        auto_clargs: Any = NETList[String]()
        auto_clargs.Add('/empty')
        self._automation = Automation(True, auto_clargs)
        self._experiment = self._automation.LightFieldApplication.Experiment

    # public methods
    def cleanup(self, *, error: Optional[Exception] = None) -> None:
        """Disposes the automation instance. If an exception is passed
        in, the content of the error message will be printed before the
        Dispose is called.

        -----
        Notes:
        -----
        Called by the `__exit__` class method, so if the object is
        constructed by a with statement, no need to call.

        If not using the context management, then this method should be
        called with exception handling code.
        """
        if error is not None:
            print(f'The following exception was handled:\n\t{error!r}')
        if not self._automation.IsDisposed:
            print('Disposing automation reference...')
            try:
                self._experiment.ImageDataSetReceived -=\
                    self.image_dataset_received
                self._experiment.ExperimentCompleted -=\
                    experiment_completed
            except ValueError:
                pass
            self._automation.Dispose()

    def execute_acquisition(self) -> None:
        """Calls an asynchronous Acquire and blocks calling thread. The
        thread will be awakened once the `experiment_completed` callback
        fires and the global event is set.

        -----
        Notes:
        -----
        Immediately sets next pulse online before calling the wait, as
        the current frame is already locked into the initial Pulse.
        """
        self._experiment.Acquire()
        self._index_to_use.increment()
        self._experiment.SetValue(CameraSettings.GatingRepetitiveGate,
            self._delay_sequence[self._index_to_use.idx_to_use])
        global_thread_event.clear()
        global_thread_event.wait()

    def load_iccd(self) -> None:
        """Looks for available ICCDs. If ICCD(s) are found, loads the
        first found if `ICCD_SERIAL_NUMBER` is not None, else tries to
        find the ICCD matching `ICCD_SERIAL_NUMBER`.
        """
        # first check if any devices are loaded - if so, throw exception as
        # the engine should have launched with no experiment.
        if self._experiment.ExperimentDevices.Count > 0:
            #self.cleanup(error=RuntimeError('Experiment device was loaded but'
            #    ' a blank experiment was expected.'))
            raise RuntimeError('An experiment device was loaded, but a'
                ' a blank experiment was expected.')
        # now check for available ICCDs.
        iccd_candidates: List[Any] = []
        for device in self._experiment.AvailableDevices:
            if device.Type == DeviceType.Camera:
                for allowed in self._iccd_model_strings:
                    if allowed in device.Model:
                        iccd_candidates.append(device)
        if ICCD_SERIAL_NUMBER is None and iccd_candidates:
            self._iccd_device = iccd_candidates[0]
        else:
            for candidate in iccd_candidates:
                assert ICCD_SERIAL_NUMBER is not None
                if ICCD_SERIAL_NUMBER.casefold() == candidate.SerialNumber:
                    self._iccd_device = candidate
        if self._iccd_device is None:
            raise RuntimeError('Appropriate ICCD not available.')
        else:
            self._experiment.Add(self._iccd_device)
            print(f'Loaded {self._iccd_device.Model}, '
                  f'SN: {self._iccd_device.SerialNumber}')

    def prep_custom_sequence(self) -> None:
        """Sets experiment parameters as follows:
        - Frames to save: NUM_STEPS user input
        - File name: CustomGateSequence w/ date and time stamp
        - Repetitive Gate mode
        - Gate Tracking on for Delay and Width

        -----
        Notes:
        -----
        The user should use the LightField UI to set other relevant parameters
        specific to their experiment (such as gate width,
        on-ccd accumulations, triggering, ADC Speed, etc.) prior to continuing
        past the prompt in the __main__ block.
        """
        if NUM_STEPS < 10:
            raise ValueError('Experiment needs to be configured with at least'
                ' 10 steps.')
        # steps and gate mode
        self._experiment.SetValue(ExperimentSettings.AcquisitionFramesToStore,
            Int64(NUM_STEPS))
        self._experiment.SetValue(CameraSettings.GatingMode,
            GatingMode.Repetitive)
        # file settings
        self._experiment.SetValue(
            ExperimentSettings.FileNameGenerationBaseFileName,
            String('CustomGateSequence'))
        self._experiment.SetValue(
            ExperimentSettings.FileNameGenerationAttachDate,
            Boolean(True))
        self._experiment.SetValue(
            ExperimentSettings.FileNameGenerationAttachTime,
            Boolean(True))
        # time stamps
        self._experiment.SetValue(
            CameraSettings.AcquisitionTimeStampingStamps, Int64(3))
        # disable continuous clean
        self._experiment.SetValue(
            CameraSettings.SensorCleaningCleanUntilTrigger, Boolean(False))
        # event hooks
        self._experiment.ImageDataSetReceived += self.image_dataset_received
        self._experiment.ExperimentCompleted +=\
                    experiment_completed
        self._generate_delay_sequence()
        if len(self._delay_sequence) != NUM_STEPS:
            raise ValueError('Generated delay sequence does not have the'
                'correct length.')

    # private methods
    def _generate_delay_sequence(self) -> None:
        """Fills in the `_delay_sequence` member with a list of gate
        pulses. For this example, a spline interpolated sequence
        with a 10% inflection at 3/4 of the delay range will be
        generated.

        -----
        Notes:
        -----
        This is the call that a user can modify to get their desired
        customized gating behavior. If making modifications, make sure
        to validate that the number of delays matches `NUM_STEPS`.
        -----
        This method should be called from `prep_custom_sequence` and not
        on its own.
        """
        # grab gate width
        gate_width: float = self._experiment.GetValue(
            CameraSettings.GatingRepetitiveGate).Width
        # generate log sequence
        inflection_pt: float = START_GATE_DELAY_NS\
            + (0.1*(END_GATE_DELAY_NS - START_GATE_DELAY_NS))
        starting_indices = np.array([0, NUM_STEPS*3//4, NUM_STEPS-1],
            dtype=np.uint32)
        interpolated_delay_indices = np.arange(NUM_STEPS, dtype=np.int32)
        starting_delays = np.array([START_GATE_DELAY_NS, inflection_pt,
            END_GATE_DELAY_NS], dtype=np.float64)
        interpolated_delays = np.interp(interpolated_delay_indices,
            starting_indices, starting_delays)
        # fill in Pulse sequence.
        for gate_delay in interpolated_delays:
            self._delay_sequence.append(Pulse(
                Double(gate_width), Double(gate_delay)))

    # Object-specific callback
    def image_dataset_received(self,
        sender: Any, evt_args: Any) -> None:
        """Callback that will fire any time one or more frame(s) are
        returned.

        The signaling of this event will indicate to the user that the
        gate pulse needs to be updated online so that the next frame(s)
        in the acquisiton have an updated delay, if there are more frame(s)
        expected.
        """
        try:
            frames_received = evt_args.ImageDataSet.Frames
            self._index_to_use.increment(amount=frames_received)
            if self._index_to_use.idx_to_use < len(self._delay_sequence):
                self._experiment.SetValue(CameraSettings.GatingRepetitiveGate,
                    self._delay_sequence[self._index_to_use.idx_to_use])
        except Exception as exc:
            global_thread_event.set()
            self.cleanup(error=exc)

    # context management
    def __enter__(self) -> Self:
        return self
    def __exit__(self, exc_type: Optional[Type[Exception]],
        exc_value: Optional[Exception],
        traceback: Optional[TracebackType]) -> bool:
        self.cleanup(error=exc_value)
        return True

if __name__ == '__main__':
    with ICCDOperator() as iccd_auto:
        iccd_auto.load_iccd()
        input('Prepare experiment using the LightField UI and press Enter'
            ' to begin the automated gating sequence once ready.')
        iccd_auto.prep_custom_sequence()
        iccd_auto.execute_acquisition()
