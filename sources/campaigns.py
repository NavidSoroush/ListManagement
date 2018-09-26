"""
campaigns.py
======================================
Contains functions relative to processing
lists requests sourced from the Campaign
object in Salesforce.
"""

from ListManagement.utility import general as ghelp
from ListManagement.utility import pandas_helper as phelp


def parse(path, frame, dict_elements, event_timing):
    """
    Function to help parse Campaign list requests into
    actionable Salesforce jobs (update, create).

    Parameters
    ----------
    path
        String; Represents a full file path to the source list.
    frame
        Pandas data frame
    dict_elements
        Dictionary; Contains metadata generated during list processing.
    event_timing
        String; Denotes whether a campaign has happened or not.

    Returns
    -------
        Tuple; updated dictionary and list of files created.
    """
    if event_timing == 'Post':
        dict_elements['cmp_status'] = 'Needs Follow-Up'
    else:
        dict_elements['cmp_status'] = 'Invited'
    dict_elements['to_create_path'] = ghelp.create_path_name(path, 'cmp_to_create')
    dict_elements['cmp_upload_path'] = ghelp.create_path_name(path, 'cmp_upload')

    cmp_upload_df = frame[frame['AccountId'].notnull()]
    to_create_df = frame[frame['AccountId'].isnull()]

    dict_elements['n_cmp_upload'] = len(cmp_upload_df.index)
    dict_elements['n_to_create'] = len(to_create_df.index)
    cmp_upload_df['Status'] = dict_elements['cmp_status']

    phelp.save_df(df=cmp_upload_df, path=dict_elements['cmp_upload_path'])
    phelp.save_df(df=to_create_df, path=dict_elements['to_create_path'])
    files_created = ['cmp_upload_path', 'to_create_path']
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
    move_to_bulk = False
    sc_to_add = 'conference_' + record_name + '_' + ghelp.yyyy_mm
    if 'to_create_path' in path:
        frame = ghelp.drop_unneeded_columns(frame, obj)
        to_create = 0
        frame.loc[frame['AccountId'].isnull(), 'AccountId'] = obj_id
        frame.loc[frame['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add
        move_to_bulk = ghelp.determine_move_to_bulk_processing(frame)
        if move_to_bulk:
            ghelp.save_conf_creation_meta(sc=sc_to_add, objid=obj_id, status=frame.iloc[0, 0])
    else:
        list_df = ghelp.drop_unneeded_columns(frame, obj, create=False)
        to_create = 0
        list_df['CampaignId'] = obj_id
    return frame, move_to_bulk, to_create