import email
import datetime
from dateutil.parser import parse
import imaplib
import sys
from cred import outlook_userEmail, password
import pandas as pd
import sqlalchemy
from progress_bar import myprogressbar
from email_handler.email_wrapper import Email

_acceptable_types = ['lsx', 'pdf', 'csv', 'xls', 'zip', 'ocx', 'txt']
_email_account = outlook_userEmail + '/Lists'
_email_folder = [['INBOX/New Lists/', 'ReceivedLists'],
                 ['INBOX/Auto Processed Lists/', 'ProcessedLists'],
                 ['INBOX/Salesforce Contact Creation Logs/', 'ContactCreationResponses']
                 ]


def get_msg_part(msg_part, array):
    """
    decodes the email_handler body from the email_handler data

    :param msg_part: coded message string (required)
    :param array: items to parse
    :return: decoded text of email_handler message
    """
    msg = email.message_from_string(array[1])
    decode = email.Header.decode_header(msg[msg_part])[0]
    try:
        tmp = unicode(decode[0], 'utf-8')
    except:
        tmp = decode[0]
    if msg_part == 'date':
        tmp = date_to_string(tmp)
    return tmp


def email_parser(sender_name, look1, look2=None):
    """
    parses the body text of an email_handler message

    :param sender_name: text of an email_handler message (required)
    :param look1: start / end location of the text to parse (required)
    :param look2: optional - takes a secondary substring if finding text
    :return: parsed substring
    """
    finder = sender_name.find(look1)
    if look2 is not None:
        finder2 = sender_name.find(look2)
        tmpStr = sender_name[finder + 1:finder2]
    else:
        tmpStr = sender_name[:finder]

    return tmpStr


def clean_date_values(d_value):
    """
    parses time value and returns date
    :param d_value: timestamp
    :return: transformed timestamp value
    """
    d_value = parse(d_value)
    return d_value


def date_to_string(d_value):
    """
    take timestamp and return string version of value.
    :param d_value: timestamp
    :return: string value of time stamp
    """
    d = clean_date_values(d_value)
    return datetime.datetime.strftime(d, '%m/%d/%Y %H:%M:%S')


m = imaplib.IMAP4_SSL('outlook.office365.com')
try:
    rv, data = m.login(_email_account, password)
except imaplib.IMAP4.error:
    print("LOGIN FAILED!!! ")
    sys.exit(1)
print('Mailbox: %s, %s' % (rv, data))

for ef in _email_folder:
    _elements = []
    print
    rv, data = m.select(ef[0])
    if rv == 'OK':
        rv, data = m.search(None, "(UNSEEN)")
        if rv == 'OK':
            num_emails = len(data[0].split())
            count = 1
            for i in data[0].split():
                myprogressbar(count, num_emails, message='%s Extraction' % ef[1])
                tmp_dict = {}
                rv, data = m.fetch(i, '(RFC822)')
                if rv != 'OK':
                    print("ERROR getting message", i)
                    sys.exit()
                else:
                    tmp_dict['Id'] = i
                    tmp_dict['Subject'] = get_msg_part('Subject', data[0])
                    tmp_dict['InboxFolder'] = ef[0]
                    tmp_dict['ReceivedDate'] = get_msg_part('date', data[0])
                    tmp_dict['SenderEmail'] = get_msg_part('From', data[0])
                    tmp_dict['SenderName'] = email_parser(tmp_dict['SenderEmail'], ' <')
                    tmp_dict['SenderEmail'] = email_parser(tmp_dict['SenderEmail'], '<', '>')
                    e_item = email.message_from_string(data[0][1])
                    attachments = []
                    for part in e_item.walk():
                        file_name = None
                        if part.get_content_maintype() == 'multipart': continue
                        if part.get('Content-Disposition') is None: continue
                        attachments.append(part.get_filename())
                    if len(attachments) > 0:
                        attachments = [a for a in attachments if a[-3:].lower() in _acceptable_types]
                        for a in range(0, len(attachments)):
                            k = 'AttachmentName' + str(a + 1)
                            tmp_dict[k] = attachments[a]
                    _elements.append(tmp_dict)
                del e_item
                del tmp_dict
                del attachments
                count += 1
                m.store(i, '+FLAGS', r'(\SEEN)')
    if num_emails > 0:
        engine = sqlalchemy.create_engine('mssql+pyodbc://DPHL-PROPSCORE/ListManagement?driver=SQL+Server')
        notification = "\nWriting %s records to the '%s' table in the ListManagement DB." % (num_emails, ef[1])
        print(notification)
        df = pd.DataFrame(data=_elements)
        cols = df.columns.values.tolist()
        cols = cols[-6:] + cols[:-6]
        df = df[cols]
        df.to_sql(name=ef[1], con=engine, index=False, if_exists='append')
        Email(subject='LMA: New %s' % ef[1], to=['ricky.schools@fsinvestments.com'], body=notification,
              attachment_path=None)
        del _elements
        del df
        del cols
