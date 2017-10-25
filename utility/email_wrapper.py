import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

from cred import password, outlook_userEmail


class Email:
    def __init__(self, subject, to, body, attachment_path):
        self.login_email = outlook_userEmail
        self.password = password
        self.host = ''
        self.port = 587
        self.from_address = 'lists@fsinvestments.com'
        self.signature = '\n\n- List Management App'
        self.subject = subject
        self.to = to
        self.body = body + self.signature
        self.attachment = attachment_path
        self.msg = MIMEMultipart()
        self._craft_email()

    def _attachments(self, att_paths, msg):

        '''
        attach all files in email to send back to the list originator

        :param att_paths: list of file paths to attach
        :param msg: mail message
        :return: updated mail message
        '''
        for att in att_paths:
            if att is not None and len(att)>0:
                with open(str(att), 'rb') as f:
                    part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    part.set_payload(f.read())
                    part.add_header('Content-Disposition',
                                    'attachment; filename="%s"' % os.path.basename(str(att)))
                    encoders.encode_base64(part)
                    msg.attach(part)
        return msg

    def _send_email(self, FROM, TO, BODY, mess=None):
        '''
        executes the actual email send

        :param FROM: email from
        :param TO: email to
        :param BODY: body text of email
        :param mess: message data (attachments)
        :return: NONE
        '''
        server = smtplib.SMTP("smtp.office365.com", 587)
        server.ehlo()
        server.starttls()
        server.login(outlook_userEmail, password)
        if mess is None:
            server.sendmail([FROM], TO, [BODY])
        else:
            server.sendmail([FROM], TO, mess.as_string())
        server.quit()

    def _del_email_object(self, msg):
        del msg

    def _craft_email(self):
        msg = self.msg
        msg['From'] = self.from_address
        msg['To'] = ','.join(self.to)
        msg['Subject'] = self.subject
        msg.attach(MIMEText(''.join(self.body)))
        if self.attachment is not None:
            msg = self._attachments(self.attachment, msg)
        pre_body = (("From: %s" % self.from_address,
                            "To: %s" % self.to,
                            "Subject: %s" % self.subject,
                            "",

                            self.body), "\r\n")

        body = ' '.join(str(item) for item in pre_body)

        self._send_email(self.from_address, self.to, body, msg)
        print('%s email sent.' % self.subject)
        self._del_email_object(msg)
