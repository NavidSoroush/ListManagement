from cred import sfuser, sfpw, sf_token
from ListManagement.sf.sf_wrapper import SFPlatform
from ListManagement.utility.log_helper import ListManagementLogger

logger = ListManagementLogger().logger
sf = SFPlatform(sfuser, sfpw, sf_token, logger)

att_id = '00P0L00000a1a76UAA'
sf.download_attachments(att_id, obj='Contact', obj_url='003E000000sasOaIAI')

