"""
processes.py
====================================
Contains core processes that are used
throughout the processing of a given list.
"""

from __future__ import absolute_import
import traceback

from PythonUtilities.EmailHandling import EmailHandler as Email

try:
    from ListManagement.config import Config as con
    from ListManagement.sources import campaigns, accounts, bdgs
    from ListManagement.utility import general as _ghelp
    from ListManagement.utility.email_helper import craft_notification_email
    from ListManagement.utility.pandas_helper import read_df, save_df, make_df, determine_num_records, crud
    from ListManagement.utility.sf_helper import *
except:

    from config import Config as con
    from sources import campaigns, accounts, bdgs
    from utility import general as _ghelp
    from utility.email_helper import craft_notification_email
    from utility.pandas_helper import read_df, save_df, make_df, determine_num_records
    from utility.sf_helper import *

upload_map = {
    'Campaign': {
        'sf_query': {
            'object': 'CampaignMember'
            , 'fields': ['ContactId', 'Status', 'CampaignId', 'Id']
            , 'where': "CampaignId='{0}'"
        }
        , 'sf_create': {
            'object': 'CampaignMember'
            , 'fields': ['ContactId', 'Status', 'CampaignId']
        }
        , 'sf_update': {
            'object': 'CampaignMember'
            , 'fields': ['ContactId', 'Status', 'CampaignId', 'ID']

        }
        , 'filenames': {
            'current_members': 'current_members'
            , 'to_add': 'to_add'
            , 'to_stay': 'to_stay'
            , 'to_remove': 'to_remove'
        }
        , 'slicer': 3
    }
    , 'BizDev Group': {
        'sf_query': {
            'object': 'Contact'
            , 'fields': ['Id', 'Biz_Dev_Group__c', 'Licences__c']
            , 'where': "Biz_Dev_Group__c ='{0}'"
        }
        , 'sf_create': {
            'object': 'Contact'
            , 'fields': ['Id', 'Biz_Dev_Group__c', 'Licences__c']
        }
        , 'sf_update': {
            'object': 'Contact'
            , 'fields': ['Id', 'Biz_Dev_Group__c', 'Licences__c']
        }
        , 'filenames': {
            'current_members': 'current_members'
            , 'to_add': 'to_add'
            , 'to_stay': 'to_stay'
            , 'to_remove': 'to_remove'
        }
        , 'slicer': 0

    }
}


def parse_list_based_on_type(_vars, log=None):
    """
    Serves as a routing point to parse a list, dependent on the sources object.

    Parameters
    ----------
    path
        A string representing a full file path.
    l_type
        A string containing the source Salesforce object for the list request.
    pre_or_post
        A string containing 'Pre' or 'Post'.
    log
        A logger instance.
    to_create_path
        The name of file ending with the '_to_create' suffix.

    Returns
    -------
        An updated dictionary mapper object.
    """
    if _vars.list_type == 'Campaign':
        _vars, files_created = campaigns.parse(_vars)

    # elif _vars.list_type == 'Account':
    #     dict_elements, files_created = accounts.parse(path=path, frame=df, dict_elements=dict_elements)
    #
    # elif _vars.list_type == 'BizDev Group':
    #     dict_elements, files_created = bdgs.parse(path=path, frame=df, dict_elements=dict_elements)

    log.info('Parsed the %s list in to the the below files: %s' % (_vars.list_type, '\n'.join(files_created)))
    return _vars


def source_channel(_vars, log):
    """
    Prepares a list for Salesforce upload and/or contact creation.

    Parameters
    ----------
    path
        A string representing a full file path.
    record_name
        A string; name of a Salesforce record.
    obj_id
        An 18-char string; Id of a Salesforce Object.
    obj
        A string; Name of a Salesforce Object.
    aid
        An 18-char string; Optional. Parent Id (or Account Id) related to an Object in Salesforce.
    log
        A logger instance.

    Returns
    -------
        A python dictionary containing next steps for the list processing tool.
    """
    if _vars.list_type == 'Campaign':
        _vars.src_object_upload_df, _vars = campaigns.make_sc(path=_vars.src_object_upload_path,
                                                              frame=_vars.src_object_upload_df,
                                                              _vars=_vars)
        _vars.create_df, _vars = campaigns.make_sc(path=_vars.create_path,
                                                   frame=_vars.create_df,
                                                   _vars=_vars)
    elif _vars.list_type == 'BizDev Group':
        _vars.update_df, _vars = bdgs.make_sc(path=_vars.update_path,
                                              frame=_vars.update_df,
                                              _vars=_vars)
        _vars.create_df, _vars = bdgs.make_sc(path=_vars.create_path,
                                              frame=_vars.create_df,
                                              _vars=_vars)
        _vars.src_object_upload_df, _vars = bdgs.make_sc(path=_vars.src_object_upload_path,
                                                         frame=_vars.src_object_upload_df,
                                                         _vars=_vars)
    else:
        _vars.update_df, _vars = bdgs.make_sc(path=_vars.update_path,
                                              frame=_vars.update_df,
                                              _vars=_vars)
    # log.info("Preparing data prep for the %s list's action files, based list type. %s" % (obj, msg))
    # list_df = read_df(path)

    # if _vars.list_type == 'Account' and _ghelp.is_path(path):
    #     frame, move_to_bulk, to_create = accounts.make_sc(path, list_df, record_name, obj_id, obj)
    #
    # elif _vars.list_type == 'Campaign':
    #     frame, move_to_bulk, to_create = campaigns.make_sc(path, list_df, record_name, obj_id, obj)
    #
    # elif _vars.list_type == 'BizDev Group':
    #     frame, move_to_bulk, to_create = bdgs.make_sc(path, list_df, record_name, obj_id, obj, aid)

    # n_head = ['Phone', 'Fax']
    # for ph in n_head:
    #     if ph in list_df.columns.values:
    #         try:
    #             list_df[ph].astype(str)
    #             for index, row in list_df.iterrows():
    #                 list_df.loc[index, ph] = _ghelp.clean_phone_number(row[ph])
    #         except:
    #             log.info("Can't clean up %s numbers due to %s." % (ph, Exception.message))

    return _vars


def extract_dictionary_values(dict_data, log=None):
    """
    This function leverages the dictionary, filled with meta data regarding a list and it's processing
    and extracts specific elements that will be used to:
        1) Organize all list processing statistics to record and store. Ex. (Num names on list, match rate, et al).
        2) Send a notification of process completion to the originator of a list request.

    Parameters
    ----------
    dict_data
        A python dictionary containing meta data regarding a single list in the queue.
    log
        A logger instance.

    Returns
    -------
        A python dictionary containing next steps for the list program.
    """
    log.info('Extracting stats from the %s data dictionary.' % dict_data['Object'])
    if dict_data['Object'] == 'Campaign':

        to_update = dict_data['n_cmp_upload']
        to_create = dict_data['n_to_create']
        obj_to_add = dict_data['Num Adding']
        obj_to_remove = dict_data['Num Removing']
        obj_to_update = dict_data['Num Updating/Staying']

    else:
        to_update = dict_data['n_to_update']
        to_create = dict_data['n_to_create']
        obj_to_add = dict_data['Num Adding']
        obj_to_remove = dict_data['Num Removing']
        obj_to_update = dict_data['Num Updating/Staying']

    log.info(' > Organized %s specific metrics.' % dict_data['Object'])

    if not dict_data['Move To Bulk']:
        create_advisors_note = 'Contacts will not be created. Not enough information provided.'
        log.info('For %s list, %s' % (dict_data['Object'], create_advisors_note))
    else:
        create_advisors_note = ''

    obj = dict_data['Object']
    if obj == 'BizDev Group':
        if not dict_data['FINRA?']:
            att_paths = [dict_data['Review Path'], dict_data['BDG Remove'],
                         dict_data['BDG Add'], dict_data['BDG Stay'], dict_data['Current Members']]
        else:
            att_paths = [dict_data['No CRD'], dict_data['FINRA Ambiguous'],
                         dict_data['BDG Remove'], dict_data['BDG Add'],
                         dict_data['BDG Stay'], dict_data['Current Members']]
    elif dict_data['FINRA?']:
        att_paths = [dict_data['No CRD'], dict_data['FINRA Ambiguous']]
    else:
        att_paths = [dict_data['Review Path']]

    total = dict_data['Total Records']
    file_name = _ghelp.split_name(dict_data['File Path'])
    # num_found_in_sfdc = dictValues['Found in SFDC Search #2'] + dictValues['SFDC_Found'] - toCreate
    num_found_in_sfdc = determine_num_records(dict_data['Found Path'])
    need_research = total - num_found_in_sfdc - to_create
    received = _ghelp.clean_date_values(dict_data['Received Date'])
    ts_received = _ghelp.date_to_string(received)
    process_start = dict_data['process_start']

    completed = _ghelp.time_now
    processing_completed = _ghelp.datetime.datetime.utcnow().isoformat()
    processing_time = _ghelp.clean_date_values(process_start) - _ghelp.clean_date_values(completed)
    processing_string = _ghelp.timedelta_to_processing_str(processing_time)
    obj_name = dict_data['Record Name']
    obj = dict_data['Object']
    num_not_updating = dict_data['n_no_update']
    sender_name = dict_data['Sender Name']
    sender_email = dict_data['Sender Email']
    match_rate = (num_found_in_sfdc + to_create) / float(total)
    items_to_email = [sender_name, obj_name, 'Strategy & Analytics team', 'salesops@fsinvestments.com',
                      total, num_found_in_sfdc, to_update,
                      num_not_updating, to_create, obj_to_add, obj_to_update,
                      obj_to_remove, need_research, received, process_start,
                      completed, processing_string, create_advisors_note]
    body_string = craft_notification_email(items_to_email)

    items_for_stats = {
        'File Name': file_name, 'Received Date': ts_received, 'Received From': sender_name
        , 'Created By': _ghelp.os.environ['USERNAME'], 'File Type': obj, 'Advisors on List': total
        , 'Advisors w/CID': num_found_in_sfdc, 'Advisors w/CID old Contact Info': num_not_updating
        , 'CRD Found Not in SFDC': to_create, 'Creating': to_create
        , 'Unable to Find': need_research, 'Last Search Date': completed
        , 'Match Rate': match_rate, 'Processing Time': processing_string
    }

    log.info('Extracted stats data:\n%s' % items_for_stats)

    listobj_cols = ['Id', 'Status__c', 'Advisors_on_List__c', 'Contacts_Added_to_Related_Record__c',
                    'Contacts_Created__c', 'Contacts_Found_in_SF__c', 'Contacts_Not_Found__c',
                    'Contacts_to_Research__c', 'Contacts_Updated__c', 'Match_Rate__c', 'List_Process_Completed_At__c',
                    'Processed_By__c']

    listobj_data = [dict_data['ListObjId'], 'Process Completed', total, obj_to_add, to_create, num_found_in_sfdc,
                    need_research, need_research, to_update, match_rate * 100, processing_completed,
                    _ghelp.os.environ['SFUSERID']]

    log.info('Updating the List record for Id: %s' % dict_data['ListObjId'])
    dict_data['SFDC Session'].update_records(obj='List__c', fields=listobj_cols, upload_data=[listobj_data])
    if len(att_paths) > 0:
        log.info('Attempting to attach %s files to the List record.' % len(att_paths))
        dict_data['SFDC Session'].upload_attachments(obj_id=dict_data['ListObjId'], attachments=att_paths)

    subject = "ALM Notification: %s list processed." % obj_name

    log.info('Sending notification email to requestor to notify of completion.')
    Email(con.SMTPUser, con.SMTPPass, log).send_new_email(
        subject=subject, to=[sender_email, _ghelp.userEmail], body=body_string,
        attachments=att_paths, name=con.FullName
    )
    return {'Next Step': 'Record Stats',
            'Stats Data': items_for_stats}


def sfdc_upload(path, obj, obj_id, session, _vars=None, log=None, ):
    # Todo: consider refactoring.
    """
    A routing method which performs final preparation and orchestrates a Salesforce upload
    for a given file.

    Parameters
    ----------
    path
        A string representing a full file path.
    obj
        A string representing the name of a Salesforce object.
    obj_id
        An 18-char string; The id of a Salesforce object.
    session
        An authenticated Salesforce REST API session.
    log
        A logger instance.

    Returns
    -------
        A python dictionary containing metadata and next steps for the list program.
    """
    df = _vars.src_object_upload_df
    if obj == 'BizDev Group':
        df.rename(columns={'BizDev Group': 'BizDev_Group__c', 'Licenses': 'Licenses__c'}, inplace=True)
        df = df[['ContactID', 'BizDev_Group__c', 'Licenses__c']]
    elif obj == 'Campaign':
        df.rename(columns={'ContactID': 'ContactId'}, inplace=True)
        df = df[['ContactId', 'Status', 'CampaignId']]

    if len(df.index) > 0:
        log.info('Attempting to upload data to SalesForce for the %s object.' % obj)
        try:
            paths, stats = upload(session, df, _vars.object_id, _vars.list_type, _vars)
        except:
            sub = 'LMA: %s upload fail for %s' % (path, obj)
            body = 'Experienced an error upload the %s file to the %s object in SFDC. Please' \
                   'manually upload this file at your earliest convenience.' % (path, obj)
            log.error(body)
            log.error(str(traceback.format_exc()))
            Email(con.SMTPUser, con.SMTPPass, log).send_new_email(
                subject=sub, to=con.ListTeam, body=body,
                attachments=[path], name=con.FullName
            )
    else:
        log.info('There is no data to upload to the %s object.' % obj)

    return {'Next Step': 'Send Email',
            'BDG Remove': paths[0],
            'BDG Add': paths[1],
            'BDG Stay': paths[2],
            'Current Members': paths[3],
            'Num Removing': stats[0],
            'Num Adding': stats[1],
            'Num Updating/Staying': stats[2]}


def upload(session, data, obj_id, obj, path, _vars):
    """
    import pandas as pd
    source_data = {'A': [1, 2, 3], 'B': ['X', 'Y', 'Z']}
    target_data = {'A': [2, 3, 4], 'B': ['A', 'Z', 'S'], 'C': [9, 7, 3]}
    source, target = pd.DataFrame(source_data), pd.DataFrame(target_data)
    on = 'A'
    Parameters
    ----------
    session
    data
    obj_id
    obj
    path

    Returns
    -------

    """
    current_path, add_path, update_path, remove_path = '', '', '', ''
    if len(data.index) > 0:
        current_members = session.query(sfdc_object=upload_map[obj]['sf_query']['object']
                                        , fields=upload_map[obj]['sf_query']['fields']
                                        , where=upload_map[obj]['sf_query']['where'].format(obj_id))

        save_df(current_members, _ghelp.create_path_name(path, 'current_members'))
        insert, update, remove = crud(data, current_members, on=upload_map[obj]['sf_query']['fields'][0])
        n_add, n_up, n_re = len(insert.index), len(update.index), len(remove.index)
        if n_up > 0:
            update_path = _ghelp.create_path_name(path, 'to_stay')
            save_df(update, update_path)
            session.update_records(upload_map[obj]['sf_update']['object'], upload_map[obj]['sf_update']['fields'],
                                   update.values.tolist())

        if n_re > 0:
            remove_path = _ghelp.create_path_name(path, 'to_remove')
            save_df(remove, remove_path)

        if n_add > 0:
            add_path = _ghelp.create_path_name(path, 'to_add')
            save_df(insert, add_path)
            session.create_records(upload_map[obj]['sf_create']['object'], upload_map[obj]['sf_create']['fields'],
                                   insert.values.tolist())

        if any(x > 0 for x in [n_up, n_add]):
            if obj == 'Campaign':
                session.update_records(obj='Campaign', fields=['Id', 'Post_Event_Leads_Uploaded__c'],
                                       upload_data=[[data.values.tolist()[0][2], 'true']])
            else:
                session.last_list_uploaded(obj_id=obj_id, obj=obj)
        return [remove_path, add_path, update_path, current_path], [n_re, n_add, n_up]


def id_preprocessing_needs(path):
    # should be comprised of three steps.
    # 1. Evaluate path extension type.
    # 2. If file is of appropriate type - check if:
    # a. top row is blank
    # b. remove any random blank rows
    # c. identify if there is a bad header row
    # 3. Notify user of needs / actions performed

    _accepted_file_ext = ['.xlsx', '.xls', '.csv']
    has_bad_file_ext = False
    needs_manual_intervention = False
    has_malformed_header_row = False
    has_blank_rows = False

    extension = _ghelp.os.path.splitext(path)[1]
    if extension not in _accepted_file_ext:
        has_bad_file_ext = True

    if not has_bad_file_ext:
        df = read_df(path)

        if df.shape[0] - df.dropna().shape[0] > 0:
            has_blank_rows = True

    if has_bad_file_ext or has_malformed_header_row or has_blank_rows:
        needs_manual_intervention = True

    print({'needs_intervention': needs_manual_intervention,
           'bad_ext': has_bad_file_ext,
           'blank_rows': has_blank_rows,
           'malformed_header': has_malformed_header_row})
