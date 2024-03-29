from PythonUtilities.LoggingUtility import Logging

from ListManagement.core.ml.header_predictions import LM_Model
from ListManagement.utils.general import duration, time
from ListManagement.config import Config as con

if __name__ == '__main__':
    log = Logging(name=con.AppName, abbr=con.NameAbbr, dir_=con.LogDrive, level='debug').logger
    log.info('AUTOMATED HEADER PREDICTION DIAGNOSTICS STARTING.')
    start = time.time()
    hp = LM_Model(log=log)
    hp.run_diagnostics(save=True)
    log.ino('AUTOMATED JOB COMPLETED IN %s.\n\n' % duration(start, time.time()))
