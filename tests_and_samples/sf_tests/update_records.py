from cred import sfuser, sfpw, sf_token
from ListManagement.sf.sf_wrapper import SFPlatform
from ListManagement.utility.log_helper import ListManagementLogger

logger = ListManagementLogger().logger
sf = SFPlatform(sfuser, sfpw, sf_token, logger)

# test the update functionality by updating Ricky Schools'
# mobile phone number in Salesforce
data = [['003E000000sasOaIAI', '(813) 468-4960']]
upload_fields = ['Id', 'MobilePhone']

sf.update_records(obj='Contact', fields=upload_fields, upload_data=data)
