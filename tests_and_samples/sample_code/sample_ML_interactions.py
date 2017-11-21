from ListManagement import HeaderPredictions, ListManagementLogger

log = ListManagementLogger().logger

# to run only diagnostics to automatically find the best performing algorithm
# (Recommended use: weekly shell or task script)
hp = HeaderPredictions(log=log, run_diagnostics='only_diagnostics')

# to run diagnostics to automatically find the best performing algorithm
# and leverage it in a production run, on the fly. (Not recommended)
hp = HeaderPredictions(log=log, run_diagnostics=True, use_saved=True)

# to leverage the best, pre-selected, algorithm selected based on cross-validation.
# Recommended use in production code-base
hp = HeaderPredictions(log=log, use_saved=True)
