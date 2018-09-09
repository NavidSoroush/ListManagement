from ListManagement.utility import pandas_helper as phelp
from ListManagement.config import Config as con

LIST_FIELDS = ['Id', 'Related_Account__c', 'Related_BizDev_Group__c',
               'Related_Campaign__c', 'OwnerId', 'File_Name__c',
               'IsDeleted', 'Status__c']
LIST_WHERE = "Status__c='In Queue'"

obj_map = {'Attachment': {'fields': ['Id, CreatedDate', 'Name'],
                          'where_stmt': "ParentId='{0}' and Name='{1}'",
                          'rename': {'Id': 'AttachmentId', 'Name': 'File_Name__c'},
                          'merge_on': 'File_Name__c',
                          'where_vars': ['ObjectId', 'File_Name__c']
                          },
           'User': {'fields': [],
                    'where_stmt': "",
                    'rename': {},
                    'merge_on': "",
                    'where_vars': []
                    }
           }


def determine_type(Id):
    if Id[:3] == '001':
        return 'Account'
    elif Id[:3] == 'a0v':
        return 'BizDev Group'
    elif Id[:3] == '701':
        return 'Campaign'


def get_metadata_ids(sfdc, frame, obj):
    # TODO: make this function work. Practically it should, but there's a pandas error that doesn't make sense.
    assert obj in obj_map
    meta_dfs = list()
    for index, row in frame.iterrows():
        meta_dfs.append(
            sfdc.query('Attachment', obj_map[obj]['fields'], obj_map[obj]['where'].format(
                row[obj_map[obj]['where_vars'][0]], row[obj_map[obj]['where_vars'][1]])
                       )
        )
    meta_dfs = phelp.concat_dfs(meta_dfs)
    meta_dfs.rename(columns=obj_map[obj]['rename'], inplace=True)
    frame = frame.merge(meta_dfs, on=obj_map[obj]['merge_on'])
    return frame


def build_queue(sfdc, log=None):
    """
    Queries Salesforce to extract any pending lists (and necessary metadata).

    Parameters
    ----------
    sf_session
        PythonUtilities.salesforcipy session to interact with Salesforce via REST.

    Returns
    -------
        Dictionary of pending lists in the queue and necessary metadata.
    """
    data = sfdc.query('List__c', fields=LIST_FIELDS, where=LIST_WHERE)
    if len(data.index) == 0:
        return dict()
    else:
        data.loc[:, 'ObjectId'] = data.Related_Campaign__c.combine_first(
            data.Related_BizDev_Group__c.combine_first(data.Related_Account__c))
        data.drop(columns=['Related_Account__c', 'Related_BizDev_Group__c', 'Related_Campaign__c'], inplace=True)
        data.loc[:, 'Object'] = data.ObjectId.apply(determine_type)
        data = get_metadata_ids(sfdc, data, 'Attachment')
        print(data.head())

        # Items = [ReturnDict('Object', obj), ReturnDict('Record Name', obj_rec_name),
        #          ReturnDict('Sender Email', sent_from), ReturnDict('Sender Name', sender_name),
        #          ReturnDict('Received Date', rec_date), ReturnDict('File Path', file_path),
        #          ReturnDict('Campaign Start Date', start_date), ReturnDict('Next Step', 'Pre-processing'),
        #          ReturnDict('Found Path', None), ReturnDict('ObjectId', obj_rec_link),
        #          ReturnDict('Pre_or_Post', pre_or_post), ReturnDict('process_start', pstart),
        #          ReturnDict('CmpAccountName', a_name), ReturnDict('CmpAccountID', a_id),
        #          ReturnDict('Found in SFDC Search #2', 0), ReturnDict('Num Adding', 0),
        #          ReturnDict('Num Removing', 0), ReturnDict('Num Updating/Staying', 0),
        #          ReturnDict('Review Path', None), ReturnDict('SFDC Session', sfdc),
        #          ReturnDict('AttachmentId', att_link), ReturnDict('ListObjId', list_obj),
        #          ReturnDict('ExtensionType', ext)]


# if __name__ == '__main__':
#     from PythonUtilities.salesforcipy import SFPy
#     sfdc = SFPy(user=con.SFUser, pw=con.SFPass, token=con.SFToken, log=None, domain=con.SFDomain)
#     extract_queue(sfdc)
