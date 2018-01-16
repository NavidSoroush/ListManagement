from cred import sfuser, sfpw, sf_token
from ListManagement.sf.sf_wrapper import SFPlatform
from ListManagement.utility.log_helper import ListManagementLogger

logger = ListManagementLogger().logger
sf = SFPlatform(sfuser, sfpw, sf_token, logger)

campaign_id = '701E0000001EPi7IAG'
data = [
    ['003E000000VsCelIAF', 'Attending', campaign_id]
    , ['003E000001P0oQEIAZ', 'Attending', campaign_id]
]
columns = ['ContactId', 'Status', 'CampaignId']

sf.create_records(obj='CampaignMember', fields=columns, upload_data=data)
