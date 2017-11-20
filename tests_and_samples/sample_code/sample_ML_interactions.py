from ListManagement import HeaderPredictions, ListManagementLogger

log = ListManagementLogger().logger

# to run only diagnostics to automatically find the best performing algorithm
hp = HeaderPredictions(log=log, run_diagnostics='only_diagnostics')

# to run diagnostics to automatically find the best performing algorithm and leverage it on the fly
hp = HeaderPredictions(log=log, run_diagnostics='True', use_saved=True)

# to leverage the best, pre-selected, algorithm selected based on cross-validation.
hp = HeaderPredictions(log=log, use_saved=True)
