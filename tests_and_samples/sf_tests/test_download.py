from cred import sfuser, sfpw, sf_token
from ListManagement.sf.sf_wrapper import SFPlatform
from ListManagement.utility.log_helper import ListManagementLogger

logger = ListManagementLogger().logger
sf = SFPlatform(sfuser, sfpw, sf_token, logger)

# att_id = '00P0L00000a1a76UAA'
# sf.download_attachments(att_id, obj='Contact', obj_url='003E000000sasOaIAI')

_list_upload_data = {'Id': ['a310L0000008uegQAA', 'a310L0000008ukdQAA'], 'Advisors_on_List__c': [112, 4306],
                     'Contacts_Added_to_Related_Record__c': [67, 0], 'Contacts_Created__c': [0, 0],
                     'Contacts_Found_in_SF__c': [67, 3740], 'Contacts_Not_Found__c': [45, 566],
                     'Contacts_to_Research__c': [45, 566], 'Contacts_Updated__c': [67, 3355],
                     'Processed_By__c': ['005E00000048KFUIA2', '005E00000048KFUIA2']
                     }

sf.update_records(obj='List__c', upload_data=_list_upload_data, fields=None)
