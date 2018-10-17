"""
campaigns.py
======================================
Contains functions relative to processing
lists requests sourced from the Campaign
object in Salesforce.
"""

from ListManagement.utility import general as ghelp
from ListManagement.utility import pandas_helper as phelp


def parse(_vars):
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
    _vars.campaign_member_status = 'Needs Follow-Up' if _vars.pre_or_post == 'Post' else 'Invited'

    _vars.create_path = ghelp.create_path_name(_vars.list_base_path, 'cmp_to_create')
    _vars.campaign_upload_path = ghelp.create_path_name(_vars.list_base_path, 'cmp_upload')

    _vars.campaign_upload_df = _vars.found_df[_vars.found_df['AccountId'].notnull()]
    _vars.create_df = _vars.found_df[_vars.found_df['AccountId'].isnull()]

    _vars.campaign_upload_records = len(_vars.campaign_upload_df.index)
    _vars.create_records = len(_vars.create_df.index)

    files_created = ['cmp_upload_path', 'to_create_path']
    return _vars, files_created


def make_sc(path, frame, _vars):
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
    sc_to_add = 'conference_' + _vars.object_name + '_' + ghelp.yyyy_mm
    if 'to_create_path' in path:
        frame = ghelp.drop_unneeded_columns(frame, _vars.list_type)
        frame.loc[frame['AccountId'].isnull(), 'AccountId'] = _vars.account_id
        frame.loc[frame['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add
        _vars.bulk_processing = ghelp.determine_move_to_bulk_processing(frame)
        if _vars.bulk_processing:
            ghelp.save_conf_creation_meta(sc=sc_to_add, objid=_vars.object_id, status=frame.iloc[0, 0])
    else:
        frame = ghelp.drop_unneeded_columns(frame, _vars.list_type, create=False)
        frame['CampaignId'] = _vars.object_id
    return frame, _vars
