import os
import time

_accepted_cols = [
    'CRDNumber', 'FirstName', 'LastName', 'AccountId'
    , 'MailingStreet', 'MailingCity', 'MailingState', 'MailingPostalCode'
    , 'SourceChannel', 'Email', 'Website', 'AUM', 'GDC', 'Fax'
    , 'HomePhone', 'MobilePhone', 'Phone'
]

_CORE_PATH = r'T:\Shared\FS2 Business Operations\Python Search Program'
_CORE_ALT = os.path.expanduser('~Documents')

_CORE_DIR = _CORE_PATH if os.path.isdir(_CORE_PATH) else _CORE_ALT


class Config(object):
    def __init__(self):
        self.AppName = 'L.I.M.A'
        self.FullName = 'ListManagementApp'
        self.NameAbbr = 'FS_LMA'
        self.CoreDir = _CORE_DIR
        self.LogDrive = os.path.join(self.CoreDir, 'logs')
        self.BaseDir = os.path.join(self.CoreDir, 'New Lists')
        self.SFDCDir = os.path.join(self.CoreDir, 'Salesforce Data Files')
        self.SFDCLoc = os.path.join(self.SFDCDir, 'SFDC Advisor List as of ' + time.strftime("%m-%d-%y") + '.csv')
        self.ListTeam = ['ricky.schools@fsinvestments.com']  # , salesops@fsinvestments.com]
        self.DevTeam = ['ricky.schools@fsinvestments.com']
        self.SFDomain = 'fsinvestments.my.salesforce.com'
        self.SFUser = os.environ['SFUSER']
        self.SFPass = os.environ['SFPASS']
        self.SFToken = os.environ['SFTOKEN']
        self.SFUserId = os.environ['SFUSERID']
        self.SMTPUser = os.environ['SMTP_EMAIL']
        self.SMTPPass = os.environ['SMTP_PASS']
        self.RunningUser = os.environ.get("USERNAME")
        self.AcceptedCols = _accepted_cols
        self.NecessaryCols = _accepted_cols[:8]
        self.BDG_ACCEPTED_COLS = ['ContactID', 'BizDev Group', 'Licenses']
        self.CMP_ACCEPTED_COLS = ['ContactID', 'CampaignId', 'Status']
        self.NEW_PATH_NAMES = ['_nocrd', '_finrasec_found', '_FINRA_ambiguous',
                               '_review_contacts', '_foundcontacts', 'cmp_to_create',
                               'cmp_upload', 'no_updates', 'to_update', 'to_create', 'bdg_update',
                               'toAdd', 'bdg_toStay', 'current_bdg_members', 'to_remove']
        self.ACCEPTED_FILE_TYPES = ['.csv', '.txt', '.tsv', '.xlsx', '.xls', '.xlm']
        self._create_directories()

    def _create_directories(self):
        for path in [self.CoreDir, self.LogDrive, self.BaseDir, self.SFDCDir]:
            if not os.path.isdir(path):
                os.mkdir(path)
