from ListManagement.utility import gen_helper as ghelp
from ListManagement.utility import pandas_helper as phelp


def parse_acct(path, frame, dict_elements):
    dict_elements['no_update_path'] = ghelp.create_path_name(path, 'no_updates')
    dict_elements['update_path'] = ghelp.create_path_name(path, 'to_update')

    no_update_df = frame[frame['Needs Info Updated?'] == 'N']
    to_update_df = frame[frame['Needs Info Updated?'] != 'N']

    dict_elements['n_no_update'] = len(no_update_df.index)
    dict_elements['n_to_update'] = len(to_update_df.index)

    phelp.save_df(df=no_update_df, path=dict_elements['no_update_path'])
    phelp.save_df(df=to_update_df, path=dict_elements['update_path'])
    files_created = ['no_update_path', 'update_path']
    return dict_elements, files_created


def make_sc_acct(path, frame, record_name, obj_id, obj):
    if path[-14:] == 'to_create.xlsx':
        frame['AccountId'] = None
        frame['SourceChannel'] = None
    sc_to_add = 'firm_' + record_name + '_' + ghelp.yyyy_mm
    frame = ghelp.drop_unneeded_columns(frame, obj)
    new_contact_df = frame[frame['AccountId'].isnull()]
    crd_sc = new_contact_df[['CRDNumber', 'SourceChannel']]
    to_create = len(new_contact_df.index)
    frame.loc[frame['AccountId'].isnull(), 'AccountId'] = obj_id
    frame.loc[frame['AccountId'].notnull(), 'AccountId'] = obj_id
    frame.loc[frame['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add

    frame = frame.merge(crd_sc, how='left', on='CRDNumber')
    del frame['SourceChannel_y']
    frame.rename(columns={'SourceChannel_x': 'SourceChannel'}, inplace=True)
    move_to_bulk = ghelp.determine_move_to_bulk_processing(frame)
    del crd_sc
    del new_contact_df
    return frame, move_to_bulk
