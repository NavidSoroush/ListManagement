from utility.email_reader import MailBoxReader
from utility.log_helper import ListManagementLogger


log = ListManagementLogger().logger
mb = MailBoxReader(log=log)
mb.extract_pending_lists(mailbox=mb.mailbox, folder=mb.new_requests_folder)
