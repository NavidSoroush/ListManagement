"""
build_queue.py
====================================
Extracts necessary metadata from Salesforce
for pending list requests.
"""

import datetime as _dt
from ListManagement.utils import pandas_helper as _phelp
from ListManagement.utils import general as _ghelp
from ListManagement.core.models import lists as model

_LIST_FIELDS = ['Id', 'Related_Account__c', 'Related_BizDev_Group__c',
                'Related_Campaign__c', 'OwnerId', 'File_Name__c',
                'IsDeleted', 'Status__c']
_LIST_WHERE = "Status__c='In Queue'"

_OBJ_MAP = {'Attachment': {'obj_name': 'ContentDocument',
                           'fields': ['Id', 'CreatedDate', 'Title'],
                           'where_stmt': "Title='{1}'",
                           'rename': {'Id': 'AttachmentId', 'Title': 'File_Name__c', 'ParentId': 'ObjectId',
                                      'CreatedDate': 'Received Date'},
                           'merge_on': ['ObjectId', 'File_Name__c'],
                           'where_vars': ['ObjectId', 'File_Name__c']
                           },
            'User': {'obj_name': 'User',
                     'fields': ['Id', 'Name', 'Email'],
                     'where_stmt': "Id='{0}'",
                     'rename': {'Id': 'OwnerId', 'Name': 'Sender Name', 'Email': 'Sender Email'},
                     'merge_on': "OwnerId",
                     'where_vars': ['OwnerId']
                     },
            'Campaign': {'obj_name': 'Campaign',
                         'fields': ['Id', 'Name'],
                         'where_stmt': "Id='{0}'",
                         'rename': {'Id': 'ObjectId', 'Name': 'Record Name'},
                         'merge_on': 'ObjectId',
                         'where_vars': ['ObjectId']
                         },
            'Account': {'obj_name': 'Account',
                        'fields': ['Id', 'Name'],
                        'where_stmt': "Id='{0}'",
                        'rename': {'Id': 'ObjectId', 'Name': 'Record Name'},
                        'merge_on': 'ObjectId',
                        'where_vars': ['ObjectId']
                        },
            'BizDev Group': {'obj_name': 'BizDev__c',
                             'fields': ['Id', 'Name'],
                             'where_stmt': "Id='{0}'",
                             'rename': {'Id': 'ObjectId', 'Name': 'Record Name'},
                             'merge_on': 'ObjectId',
                             'where_vars': ['ObjectId']
                             },
            }

_STATIC_VARIABLES = {
    'Next Step': 'Pre-processing',
    'process_start': _dt.datetime.fromtimestamp(_ghelp.time.time()).strftime('%Y-%m-%d %H:%M:%S'),
    'CmpAccountName': str(), 'CmpAccountID': str(), 'Campaign Start Date': None, 'Pre_or_Post': str(),
    'ExtensionType': str(), 'File Path': str(),
}


def _determine_type(object_id):
    """
    Parses a string to determine the Salesforce object type.

    Parameters
    ----------
    object_id
        Typically, an 18-character id; references a single record within a Salesforce instance.

    Returns
    -------
        Dictionary containing metadata regarding a request to perform comparisons between
        a third party advisor list and our Salesforce CRM advisors.
    """
    if object_id[:3] == '001':
        return 'Account'
    elif object_id[:3] == 'a0v':
        return 'BizDev Group'
    elif object_id[:3] == '701':
        return 'Campaign'


def _build_clause(row, obj):
    """
    Helper method to build a dynamic 'where' statement for a SOQL query.

    Parameters
    ----------
    row
        A single row of a pandas dataframe/series.
    obj
        String; represents an object (table) name in Salesforce.

    Returns
    -------
        A populated, dynamic, string; used in a SOQL where clause.
    """
    if len(_OBJ_MAP[obj]['where_vars']) > 1:
        clause = _OBJ_MAP[obj]['where_stmt'].format(
            row[_OBJ_MAP[obj]['where_vars'][0]], row[_OBJ_MAP[obj]['where_vars'][1]])
    elif len(_OBJ_MAP[obj]['where_vars']) == 1:
        clause = _OBJ_MAP[obj]['where_stmt'].format(row[_OBJ_MAP[obj]['where_vars'][0]])
    else:
        clause = _OBJ_MAP[obj]['where_stmt']
    return clause


def _get_metadata_ids(sfdc, frame=None, obj=None, parent_obj=None):
    """
    Generic method to extract metadata from a Salesforce object. Uses the _OBJ_MAP
    variable above to define what (and how) information get's extracted (and blended)
    from Salesforce into an existing data structure.

    Parameters
    ----------
    sfdc
        Authenticated Salesforce REST API session.
    frame
        Pandas data frame object.
    obj
        String; represents an object (table) name in Salesforce.
    parent_obj
        Optional. Can overwrite the obj parameter, if necessary.

    Returns
    -------
        Metadata regarding a Salesforce object, as defined by _OBJ_MAP['fields'] values.
    """
    assert obj in _OBJ_MAP
    if parent_obj is not None:
        obj = parent_obj
    meta_dfs = list()
    for index, row in frame.iterrows():
        clause = _build_clause(row, obj)
        queried_data = sfdc.query(_OBJ_MAP[obj]['obj_name'], _OBJ_MAP[obj]['fields'], where=clause)
        if len(queried_data.index) > 0:
            if obj == 'Attachment':
                queried_data['ParentId'] = row['ObjectId']
            meta_dfs.append(queried_data)
    if len(meta_dfs) > 1:
        meta_dfs = _phelp.concat_dfs(meta_dfs)
    else:
        meta_dfs = meta_dfs[0]
    meta_dfs.rename(columns=_OBJ_MAP[obj]['rename'], inplace=True)
    if _OBJ_MAP[obj]['merge_on'] is None and frame is None:
        frame = meta_dfs
    else:
        frame = frame.merge(meta_dfs, on=_OBJ_MAP[obj]['merge_on'])
    return frame


def _get_attachments(sfdc, frame):
    """
    Helper method to download attachments and populate a single-row's meta data values
    for a list request.

    Parameters
    ----------
    sfdc
        Authenticated Salesforce REST API session.
    frame
        Pandas data frame object.

    Returns
    -------
        An updated frame object.
    """
    for index, row in frame.iterrows():
        file_path, start_date, pre_or_post, a_name, a_id = sfdc.download_attachments(att_id=row['AttachmentId'],
                                                                                     obj=row['Object'],
                                                                                     obj_url=row['ObjectId'])
        ext_len, ext = _ghelp.determine_ext(f_name=file_path)
        frame.at[index, 'File Path'] = file_path
        frame.at[index, 'Campaign Start Date'] = start_date
        frame.at[index, 'Pre_or_Post'] = pre_or_post
        frame.at[index, 'CmpAccountName'] = a_name
        frame.at[index, 'CmpAccountID'] = a_id
        frame.at[index, 'ExtensionType'] = ext
    return frame


def queue_metadata_to_list(data):
    list_queue = list()
    for pi in data:
        item = model.ListBase(id=pi['ListIndex'], list_id=pi['ListObjId'], owner_id=pi['OwnerId']
                              , file_name=pi['File_Name__c'], account_name=pi['CmpAccountName']
                              , account_id=pi['CmpAccountID'], event_start=pi['Campaign Start Date']
                              , pre_or_post=pi['Pre_or_Post'], requested_by=pi['Sender Name']
                              , requested_by_email=pi['Sender Email'], received_date=pi['Received Date']
                              , list_type=pi['Object'], object_id=pi['ObjectId'], object_name=pi['Record Name']
                              , file_path=pi['File Path'], extension=pi['ExtensionType']
                              , attachment_id=pi['AttachmentId'])
        list_queue.append(item)
    return list_queue


def establish_queue(sfdc, log=None):
    """
    Queries Salesforce to extract any pending lists (and necessary metadata).

    Parameters
    ----------
    sfdc
        Authenticated Salesforce REST API session.
    log
        log object.

    Returns
    -------
        Dictionary of pending lists in the queue and necessary metadata.
    """
    log.info('Attempting to build list queue.')
    data = sfdc.query('List__c', fields=_LIST_FIELDS, where=_LIST_WHERE)
    data.rename(columns={'Id': 'ListObjId'}, inplace=True)
    if len(data.index) == 0:
        log.info('There are no pending lists.')
        return list()
    else:
        # establish all of L.I.M.A.'s required variables.
        for k, v in _STATIC_VARIABLES.items():
            data.loc[:, k] = v
        data.loc[:, 'SFDC Session'] = sfdc

        data.loc[:, 'ObjectId'] = data.Related_Campaign__c.combine_first(
            data.Related_BizDev_Group__c.combine_first(data.Related_Account__c))
        data.drop(columns=['Related_Account__c', 'Related_BizDev_Group__c', 'Related_Campaign__c'], inplace=True)
        data.loc[:, 'Object'] = data.ObjectId.apply(_determine_type)
        data = _get_metadata_ids(sfdc, data, 'Attachment')
        data = _get_metadata_ids(sfdc, data, 'User')
        data.drop_duplicates(inplace=True)
        data = _get_metadata_ids(sfdc, data, data['Object'][0])
        data = _get_attachments(sfdc, data)
        data.insert(0, 'ListIndex', range(1, 1 + len(data)))
        data = queue_metadata_to_list(data.to_dict('rows'))
        log.info('There are {0} items pending in the queue.'.format(len(data)))
        return data
