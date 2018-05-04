from ListManagement.sf.sf_wrapper import SFPlatform
from ListManagement.utility.log_helper import ListManagementLogger
from ListManagement.utility.sf_helper import get_user_id
from cred import *

log = ListManagementLogger('SFWrapperTesting', 'SFWT').logger

sf = SFPlatform(sfuser, sfpw, sf_token, log=log)

query_email = 'kari.whitman@fsinvestments.com'
parent_id = '001E000000DuenSIAR'
att_name = 'C:/June Rep-Advisor List.xlsx'
# expected = {'Email': ['krista.bono@fsinvestments.com'], 'Id': ['005E0000000XyVMIA0']}

# results_df = sf.query(sfdc_object='User', fields=['Email', 'Id'], where="Email='%s'" % query_email)
# assert expected == results_df.to_dict(orient='list')

att_owner_and_id = get_user_id(sf, parent_id, att_name, query_email)
print(att_owner_and_id)
sf.update_records('Attachment', ['Id', 'OwnerId', 'CreatedById'], [att_owner_and_id])

del sf
