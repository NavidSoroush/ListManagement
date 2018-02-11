import traceback

try:
    from utility.email_reader import MailBoxReader
    from utility.log_helper import ListManagementLogger
    from utility.email_wrapper import Email
    from utility.gen_helper import duration, time

except:
    from ListManagement.utility.email_reader import MailBoxReader
    from ListManagement.utility.log_helper import ListManagementLogger
    from ListManagement.utility.email_wrapper import Email
    from ListManagement.utility.gen_helper import duration, time

log = ListManagementLogger().logger
start = time.time()
log.info('AUTOMATED LIST REQUEST ROUTING STARTED.')
log.info('Setting up the Mailbox Reader object.')
mb = MailBoxReader(log=log)
log.info('  > Mailbox Reader successfully configured and setup.')
try:
    log.info('Attempting to extract pending lists.')
    mb.extract_pending_lists(mailbox=mb.mailbox, folder=mb.new_requests_folder)
except:
    log.error('ERROR OCCURRED. Unable to appropriately '
              'handle and route the request. Error message below:\n'
              '%s' % str(traceback.format_exc()))
    sub = 'LMA: Requested Email Notification - Unable to Process'
    Email(subject=sub, to=['ricky.schools@fsinvestments.com'], body=str(traceback.format_exc()), attachment_path=None)
finally:
    log.info('AUTOMATED JOB COMPLETED IN %s.\n\n' % duration(start, time.time()))
