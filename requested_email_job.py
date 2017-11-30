import traceback

try:
    from ListManagement.utility.email_reader import MailBoxReader
    from ListManagement.utility.log_helper import ListManagementLogger
    from ListManagement.utility.email_wrapper import Email
except:
    from utility.email_reader import MailBoxReader
    from utility.log_helper import ListManagementLogger
    from utility.email_wrapper import Email


log = ListManagementLogger().logger
mb = MailBoxReader(log=log)
try:
    mb.extract_pending_lists(mailbox=mb.mailbox, folder=mb.new_requests_folder)
except:
    sub = 'LMA: Requested Email Notification - Unable to Process'
    Email(subject=sub, to=['ricky.schools@fsinvestments.com'], body=str(traceback.format_exc()), attachment_path=None)
