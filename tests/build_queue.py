import os
from ListManagement.core.build_queue import establish_queue

from PythonUtilities.LoggingUtility import Logging
from PythonUtilities.salesforcipy import SFPy

log = Logging('LMA_TestLogs', 'LMA_TL').logger

sfdc = SFPy(user='sandbox-user', pw='sandbox-pw',
            token='sandbox-token', instance='Sandbox',
            _dir=os.path.expanduser('~\\Downloads'))

queue = establish_queue(sfdc, log)

print(len(queue))