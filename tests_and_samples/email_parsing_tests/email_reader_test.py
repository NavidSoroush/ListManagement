from ListManagement.utility.email_reader import MailBoxReader
from ListManagement.utility.log_helper import ListManagementLogger

log = ListManagementLogger().logger

log.debug('Setting up objects for email reader/parsing tests.')
mb = MailBoxReader(log)
lists_in_queue = mb.extract_pending_lists(mb.mailbox, mb.email_folder)
mb.iterative_processing(lists_in_queue['Lists_Data'][0])
