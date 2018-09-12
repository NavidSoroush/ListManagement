from ListManagement.utility import general as ghelp
from ListManagement.utility import pandas_helper as phelp


def parse(path, frame, dict_elements):
    dict_elements['no_update_path'] = ghelp.create_path_name(path=path, new_name='no_updates')
    dict_elements['update_path'] = ghelp.create_path_name(path=path, new_name='to_update')
    dict_elements['to_create_path'] = ghelp.create_path_name(path=path, new_name='to_create')
    dict_elements['bdg_update_path'] = ghelp.create_path_name(path=path, new_name='bdg_update')

    no_update_df = frame[(frame['AccountId'].notnull()) & (frame['Needs Info Updated?'] == 'N')]
    to_update_df = frame[(frame['AccountId'].notnull()) & (frame['Needs Info Updated?'] != 'N')]
    to_create_df = frame[frame['AccountId'].isnull()]
    bdg_update_df = frame[(frame['AccountId'].notnull()) & (
            frame['Licenses'].str.contains('Series 7') | frame['Licenses'].str.contains('Series 22'))]

    dict_elements['n_no_update'] = len(no_update_df.index)
    dict_elements['n_to_update'] = len(to_update_df.index)
    dict_elements['n_to_create'] = len(to_create_df.index)
    dict_elements['n_bdg_update'] = len(bdg_update_df.index)

    phelp.save_df(df=no_update_df, path=dict_elements['no_update_path'])
    phelp.save_df(df=to_update_df, path=dict_elements['update_path'])
    phelp.save_df(df=to_create_df, path=dict_elements['to_create_path'])
    phelp.save_df(df=bdg_update_df, path=dict_elements['bdg_update_path'])
    files_created = ['no_update_path', 'update_path', 'to_create_path', 'bdg_update_path']
    return dict_elements, files_created


def make_sc(path, frame, record_name, obj_id, obj, aid):
    sc_to_add = 'bdg_' + record_name + '_' + ghelp.yyyy_mm
    if 'to_create_path' in path:
        frame = ghelp.drop_unneeded_columns(frame, obj)
        to_create = len(frame.index)
        frame.loc[frame['AccountId'].isnull(), 'AccountId'] = aid
        frame.loc[frame['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add
    elif 'bdg_update_path' in path:
        frame = ghelp.drop_unneeded_columns(frame, obj, bdg=True)
        to_create = 0
        frame['BizDev Group'] = obj_id
    else:
        frame = ghelp.drop_unneeded_columns(frame, obj)
        to_create = 0
        frame['AccountId'] = aid
        frame['BizDev Group'] = obj_id

    move_to_bulk = ghelp.determine_move_to_bulk_processing(frame)
    return frame, move_to_bulk, to_create
