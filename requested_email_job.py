import email
from email.parser import Parser
import os
import shutil
import datetime
from dateutil.parser import parse
import imaplib
import sys
from cred import outlook_userEmail, password
import pandas as pd
import sqlalchemy
from utility.progress_bar import myprogressbar
from email_handler.email_wrapper import Email

_acceptable_types = ['lsx', 'pdf', 'csv', 'xls', 'zip', 'ocx', 'txt']
_email_account = outlook_userEmail + '/Lists'
_email_folder = [
    ['INBOX/', 'Inbox'],
    ['INBOX/New Lists/', 'ReceivedLists'],
    ['INBOX/Auto Processed Lists/', 'ProcessedLists'],
    ['INBOX/Salesforce Contact Creation Logs/', 'ContactCreationResponses']
]
_temp_save_attachments = 'C:/save_att/'


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


def handle_email_attachments(remove=False, msg_part=None, att=None):
    if remove:
        if os.path.isdir(_temp_save_attachments):
            shutil.rmtree(_temp_save_attachments)
    else:
        if not os.path.isdir(_temp_save_attachments):
            os.mkdir(_temp_save_attachments)
        if att is not None:
            new_fname = _temp_save_attachments + att
            with file(_temp_save_attachments + att, mode='w') as f:
                f.write(msg_part.get_payload(decode=True))
            return new_fname


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


def move_received_list_to_processed_folder(mailbox, num):
    mailbox.copy(num, 'INBOX/New Lists')
    mailbox.store(num, '+FLAGS', r'(\Deleted)')
    mailbox.expunge()


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
                    msg_body = "Request from %s for %s list.\n\n" \
                               "Please look in the 'New Lists' folder of the list inbox " \
                               "for more details." % (tmp_dict['SenderName'],
                                                      tmp_dict['Subject'])
                    attachments = []
                    for part in e_item.walk():
                        if part.get_content_type() == "text/plain":
                            msg_body += part.get_payload(decode=True)
                        if part.get_content_maintype() == 'multipart': continue
                        if part.get('Content-Disposition') is None: continue
                        file_name = part.get_filename()
                        if file_name is not None:
                            file_name = handle_email_attachments(msg_part=part, att=file_name)
                            attachments.append(file_name)
                    if len(attachments) > 0:
                        attachments = [a for a in attachments if a[-3:].lower() in _acceptable_types]
                        for a in range(0, len(attachments)):
                            k = 'AttachmentName' + str(a + 1)
                            tmp_dict[k] = attachments[a]
                    _elements.append(tmp_dict)
                    if ef[0] == 'INBOX/':
                        email_to = ['rickyschools+v3lhm65etri76gwbn0sy@boards.trello.com',
                                    'max.charles@fsinvestments.com',
                                    'ricky.schools@fsinvestments.com']
                        sub = 'New List Received -' + tmp_dict['Subject']
                        e_item.replace_header('From', 'lists@fsinvestments.com')
                        e_item.replace_header('To', email_to)
                        e_item.replace_header('Subject', sub)
                        Email(subject=sub, to=email_to, body=msg_body, attachment_path=attachments)
                        move_received_list_to_processed_folder(mailbox=m, num=i)
                        handle_email_attachments(remove=True)
                del e_item
                del tmp_dict
                count += 1
                m.store(i, '+FLAGS', r'(\SEEN)')

    if num_emails > 0 and ef[0] != "INBOX/":
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
