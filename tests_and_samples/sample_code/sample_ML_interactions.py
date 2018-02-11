from ListManagement.ml.header_predictions import HeaderPredictions
from ListManagement.utility.log_helper import ListManagementLogger
from ListManagement.utility.gen_helper import duration, time

log = ListManagementLogger().logger

# to run only diagnostics to automatically find the best performing algorithm
# (Recommended use: weekly shell or task script)
log.info('AUTOMATED HEADER PREDICTION DIAGNOSTICS STARTING.')
start = time.time()
hp = HeaderPredictions(log=log, run_diagnostics='only_diagnostics')
log.ino('AUTOMATED JOB COMPLETED IN %s.\n\n' % duration(start, time.time()))

# to run diagnostics to automatically find the best performing algorithm
# and leverage it in a production run, on the fly. (Not recommended)
# hp = HeaderPredictions(log=log, run_diagnostics=True, use_saved=True)

# to leverage the best, pre-selected, algorithm selected based on cross-validation.
# Recommended use in production code-base
# hp = HeaderPredictions(log=log, use_saved=True)
