'''Testbed for evaluating robustness of the automation interface.

Two threads are launched, one thread running an Acquire loop, the other
probing detector temperature every 100ms. The threads keep executing
infinitely until the user stops (key enter in terminal) or the execution
crashes.
'''

from threading import Thread, Lock
import time
from datetime import timedelta
import sys
from LFAutomation import AutoClass as ac


STOP = False
mutex = Lock()
exceptions = []

#pylint: disable=consider-using-f-string
#pylint: disable=broad-exception-caught
def temperature_acquisition_loop(automation: ac, timestamp: float) -> None:
    '''Call in own thread -- will keep probing temperature'''
    counter = 0
    while not STOP:
        try:
            sensor_temperature = automation.read_camera_temperature()
            if counter % 100 == 0:
                print('Current sensor temperature is %0.3f C'\
                    ', read number %d'%(sensor_temperature, \
                        counter + 1))
            time.sleep(0.1)
            counter += 1
        except Exception:
            exception_time = timedelta(seconds= \
                time.perf_counter() - timestamp)
            with mutex:
                print('Exception after %s runtime duration.\n'% \
                    (str(exception_time)))
                exceptions.append(sys.exc_info()[2])
            return
    print('Total temperature probes (every 10 s): %d'%(counter))

def acquire_loop(automation: ac, timestamp: float) -> None:
    '''Call in own thread - will continue to Acquire and generate files'''
    while not STOP:
        try:
            automation.acquire_with_wait()
        except Exception:
            exception_time = timedelta(seconds= \
                time.perf_counter() - timestamp)
            with mutex:
                print('Exception after %s runtime duration.\n'% \
                    (str(exception_time)))
                exceptions.append(sys.exc_info()[2])
            return
    automation.experiment.Stop()


if __name__=='__main__':
    lf = ac()
    #set up automation instance - you will want to replace my path with a
    #proper path to your desired experiment.
    lf.NewInstance(expPath=\
        'C:\\Users\\sliakat\\Documents\\LightField\\Experiments\\'\
        'AutomationTest-EM.lfe')
    #set up thread(s)
    start_time = time.perf_counter()
    t_temperature = Thread(target=temperature_acquisition_loop, args=(lf,\
        start_time,))
    t_acquire = Thread(target=acquire_loop, args=(lf,start_time), daemon=True)
    t_temperature.start()
    t_acquire.start()
    #keep looking for exception in the queue
    #will keep script alive until key is pressed to stop
    input('Enter a key to stop.\n')
    STOP = True
    t_temperature.join()
    if not exceptions:
        format_time = timedelta(seconds= \
            time.perf_counter() - start_time)
        print('Threads stopped by user - time delta ' \
            + str(format_time))
    lf.CloseInstance()
