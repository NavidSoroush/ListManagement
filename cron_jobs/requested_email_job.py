import sys
import traceback
import datetime as dt

from PythonUtilities.LoggingUtility import Logging
from PythonUtilities.EmailHandling import EmailHandler as Email

from ListManagement.utils.email_reader import MailBoxReader
from ListManagement.config import Config as con
from ListManagement.utils.general import duration, time

if __name__ == '__main__':
    log = Logging(name=con.AppName, abbr=con.NameAbbr, dir_=con.LogDrive, level='debug').logger
    start = time.time()
    log.info('AUTOMATED LIST REQUEST ROUTING STARTED.')
    log.info('Setting up the Mailbox Reader object.')
    mb = MailBoxReader(log=log)
    log.info('  > Mailbox Reader successfully configured and setup.')
    state, begin = 1, dt.datetime.now()
    try:
        log.info('Attempting to extract pending lists.')
        mb.extract_pending_lists(mailbox=mb.mailbox, folder=mb.new_requests_folder)
    except:
        state = -1
        log.error('ERROR OCCURRED. Unable to appropriately '
                  'handle and route the request. Error message below:\n'
                  '%s' % str(traceback.format_exc()))
        sub = 'LMA: Requested Email Notification - Unable to Process'
        Email(con.SMTPUser, con.SMTPPass, log=log).send_new_email(
            subject=sub, to=['ricky.schools@fsinvestments.com']
            , body=str(traceback.format_exc()), attachments=None
        )
    finally:
        end = dt.datetime.now()
        log.info('AUTOMATED JOB COMPLETED IN %s.\n\n' % duration(start, time.time()))
