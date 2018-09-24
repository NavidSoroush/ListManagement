"""
accounts.py
======================================
Contains functions relative to processing
lists requests sourced from the Account
object in Salesforce.
"""

from ListManagement.utility import general as ghelp
from ListManagement.utility import pandas_helper as phelp


def parse(path, frame, dict_elements):
    """
    Function to help parse Account list requests into
    actionable Salesforce jobs (update, create).

    Parameters
    ----------
    path
        String; Represents a full file path to the source list.
    frame
        Pandas data frame
    dict_elements
        Dictionary; Contains metadata generated during list processing.

    Returns
    -------
        Tuple; updated dictionary and list of files created.
    """
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


def make_sc(path, frame, record_name, obj_id, obj):
    """
    Function to manufacture a 'source_channel' for contacts
    that need to be created.

    A source channel gives FS Investments the ability to see
    from where and when a contact record was sourced from.

    Parameters
    ----------
    path
        String; Represents a full file path.
    frame
        Pandas data frame; Object containing relational data.
    record_name
        String; Represents the name of a salesforce record.
    obj_id
        String; Represents the id of a Salesforce record
    obj
        String; Represents the name of a Salesforce object.

    Returns
    -------
        Tuple; updated pandas dataframe, move to bulk (boolean), and to_create_path (string)
    """
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
    return frame, move_to_bulk, to_create
