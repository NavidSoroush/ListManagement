# def id_preprocessing_needs(path):
#     # should be comprised of three steps.
#     # 1. Evaluate path extension type.
#     # 2. If file is of appropriate type - check if:
#     # a. top row is blank
#     # b. remove any random blank rows
#     # c. identify if there is a bad header row
#     # 3. Notify user of needs / actions performed
#
#     _accepted_file_ext = ['.xlsx', '.xls', '.csv']
#     has_bad_file_ext = False
#     needs_manual_intervention = False
#     has_malformed_header_row = False
#     has_blank_rows = False
#
#     extension = _ghelp.os.path.splitext(path)[1]
#     if extension not in _accepted_file_ext:
#         has_bad_file_ext = True
#
#     if not has_bad_file_ext:
#         df = read_df(path)
#
#         if df.shape[0] - df.dropna().shape[0] > 0:
#             has_blank_rows = True
#
#     if has_bad_file_ext or has_malformed_header_row or has_blank_rows:
#         needs_manual_intervention = True
#
#     print({'needs_intervention': needs_manual_intervention,
#            'bad_ext': has_bad_file_ext,
#            'blank_rows': has_blank_rows,
#            'malformed_header': has_malformed_header_row})
