from PythonUtilities.EmailHandling import EmailHandler as Email

from ListManagement.config import Config
from ListManagement.static.notification_message import (
    complete_message, complete_subject, unable_to_process_message,
    unable_to_process_subject
)

Config = Config()


class Notify:
    def __init__(self, log):
        self.log = log

    @staticmethod
    def send_completion_message(item):
        subject = complete_subject.format(item.object_name)
        body = complete_message.format(requestor=item.requested_by, object_name=item.object_name,
                                       team='Strategy & Analytics team', email=Config.SFUser,
                                       total=item.total_records, found=item.found_records,
                                       updating=item.updating_records, not_updating=item.no_update_records,
                                       creating=item.create_records, adding=item.add_records,
                                       stayed=item.stay_records, remove=item.remove_records,
                                       research=item.need_research, received=item.requested_timestamp,
                                       started=item.process_start, ended=item.process_end,
                                       duration=item.duration, object=item.list_type, object_id=item.object_id,
                                       list_id=item.list_id
                                       )

        Email(Config.SMTPUser, Config.SMTPPass).send_new_email(
            subject=subject, to=Config.ListTeam + [item.requested_by_email]
            , body=body, attachments=item.generated_files, name=Config.FullName
        )

    @staticmethod
    def send_unable_to_process_message(item):
        subject = unable_to_process_subject.format(object_name=item.object_name)
        body = unable_to_process_message.format(requestor=item.requested_by, object_name=item.object_name,
                                                extension=item.extension,
                                                formats=', '.join(Config.ACCEPTED_FILE_TYPES))
        Email(Config.SMTPUser, Config.SMTPPass).send_new_email(
            subject=subject, to=Config.ListTeam + [item.requested_by_email]
            , body=body, attachments=item.list_source['path'], name=Config.FullName
        )
