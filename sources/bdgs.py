"""
bdgs.py
======================================
Contains functions relative to processing
lists requests sourced from the BizDev Group
object in Salesforce.
"""

from ListManagement.utility import general as ghelp


def parse(_vars):
    """
    Function to help parse BizDev Group list requests into
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
    _vars.no_update_path = ghelp.create_path_name(_vars.list_base_path, 'no_updates')
    _vars.update_path = ghelp.create_path_name(_vars.list_base_path, 'to_update')
    _vars.create_path = ghelp.create_path_name(_vars.list_base_path, 'to_create')
    _vars.src_object_upload_path = ghelp.create_path_name(_vars.list_base_path, 'bdg_update')

    _vars.no_update_df = _vars.found_df[
        (_vars.found_df['AccountId'].notnull()) & (_vars.found_df['Needs Info Updated?'] == 'N')]
    _vars.update_df = _vars.found_df[
        (_vars.found_df['AccountId'].notnull()) & (_vars.found_df['Needs Info Updated?'] != 'N')]
    _vars.create_df = _vars.found_df[_vars.found_df['AccountId'].isnull()]
    _vars.src_object_upload_path = _vars.found_df[(_vars.found_df['AccountId'].notnull()) & (
            _vars.found_df['Licenses'].str.contains('Series 7') | _vars.found_df['Licenses'].str.contains('Series 22'))]

    return _vars


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
    aid
        String; Represents the Id of an Account object in Salesforce.

    Returns
    -------
        Tuple; updated pandas dataframe, move to bulk (boolean), and to_create_path (string)
    """
    if len(frame.index) > 0:
        sc_to_add = 'bdg_' + _vars.object_name + '_' + ghelp.yyyy_mm
        if 'to_create_path' in path:
            frame = ghelp.drop_unneeded_columns(frame,  _vars.list_type)
            frame.loc[frame['AccountId'].isnull(), 'AccountId'] = _vars.account_id
            frame.loc[frame['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add
        elif 'bdg_update_path' in path:
            frame = ghelp.drop_unneeded_columns(frame, _vars.list_type, bdg=True)
            frame['BizDev Group'] = _vars.object_id
        else:
            frame = ghelp.drop_unneeded_columns(frame, _vars.list_type)
            frame['AccountId'] = _vars.account_id
            frame['BizDev Group'] = _vars.object_id

        _vars.bulk_processing = ghelp.determine_move_to_bulk_processing(frame)
    return frame, _vars
