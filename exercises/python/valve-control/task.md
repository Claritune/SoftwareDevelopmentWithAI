## Task description

Your task is to develop a software module that will be responsible for adjusting valves in a water system.
The software controls a hardware component capable of adjusting the valve to any desired position, through a signal (+/-) that gradually opens or closes the valve. The valve can end up in any position between 0% (closed) and 100% (fully open).
Closing the valve when pipe pressure is too high is dangerous and the software should prevent it from happening.
The software can inquire the valve state, the pipe pressure and the water temperature.
Under certain circumstances (known in advance) the system should open the valves as quickly as possible to the maximum.


Hardware implementation is out of scope but dictating hardware-software relationships is in scope
