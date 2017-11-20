from ListManagement import SFPlatform, ListManagementLogger
from cred import *

_test_object = ['Contact']
_test_columns = ['Id', 'FirstName', 'Last Name', 'Phone']
_test_upload_data = [['123456789123456', 'John', 'Doe', '(555) 555-5555'],
                     ['213456789123456', 'Jane', 'Doe', '(555) 555-5555']]
_test_create_data = [dat[1:] for dat in _test_upload_data]

log = ListManagementLogger().logger

# below are examples of how to use the SFPlatform API. these all are leveraging dummy data.
# Please use examples of real data to actually leverage the tool.

# logging into the SF API
sf = SFPlatform(user=sfuser, pw=sfpw, token=sf_token, log=log)

# to create records
sf.create_records(obj=_test_object, fields=_test_columns, upload_data=_test_create_data)

# to query records
query_results = sf.query(sfdc_object=_test_object, fields=['Id', 'FirstName', 'LastName', 'Phone'],
                         where='LastName=Doe')

# to update records
sf.update_records(obj=_test_object, fields=_test_columns, upload_data=query_results)

# to upload an attachment, assuming you have a file named 'upload_me.txt' in the current directory
# and your instance has an object id of 1234.
sf.upload_attachments(obj_id='1234', attachments=['upload_me.txt'])

# to download attachments, assuming the att_id = 1234 and the obj_id = 4321
sf.download_attachments(att_id='1234', obj=_test_object, obj_url='4321')
