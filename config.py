import os

_accepted_cols = [
    'CRDNumber', 'FirstName', 'LastName', 'AccountId'
    , 'MailingStreet', 'MailingCity', 'MailingState', 'MailingPostalCode'
    , 'SourceChannel', 'Email', 'Website', 'AUM', 'GDC', 'Fax'
    , 'HomePhone', 'MobilePhone', 'Phone'
]


class Config(object):
    AppName = 'L.I.M.A'
    FullName = 'ListManagementApp'
    NameAbbr = 'FS_LMA'
    LogDrive = 'T:\\Shared\\FS2 Business Operations\\Python Search Program\\logs\\'
    BaseDir = 'T:\\Shared\\FS2 Business Operations\\Python Search Program\\New Lists\\'
    ListTeam = ['ricky.schools@fsinvestments.com']  # , salesops@fsinvestments.com]
    SFDomain = 'fsinvestments.my.salesforce.com'
    SFUser = os.environ['SFUSER']
    SFPass = os.environ['SFPASS']
    SFToken = os.environ['SFTOKEN']
    SFUserId = os.environ['SFUSERID']
    SMTPUser = os.environ['SMTP_EMAIL']
    SMTPPass = os.environ['SMTP_PASS']
    RunningUser = os.environ.get("USERNAME")
    AcceptedCols = _accepted_cols
    NecessaryCols = _accepted_cols[:8]
    BDG_ACCEPTED_COLS = ['ContactID', 'BizDev Group', 'Licenses']
    CMP_ACCEPTED_COLS = ['ContactID', 'CampaignId', 'Status']
    NEW_PATH_NAMES = ['_nocrd', '_finrasec_found', '_FINRA_ambiguous',
                      '_review_contacts', '_foundcontacts', 'cmp_to_create',
                      'cmp_upload', 'no_updates', 'to_update', 'to_create', 'bdg_update',
                      'toAdd', 'bdg_toStay', 'current_bdg_members', 'to_remove']
