import os

# import importlib
# import pip
# import sys
#
# try:
#     from ListManagement.utility.chromedriver_installer import install_chromedriver
# except:
#     from utility.chromedriver_installer import install_chromedriver


# def ensure_requirements_met():
#     '''
#     this function is meant to ensure that if the requirements of the list program
#     are automatically checked, and met, prior to running the program.
#
#     :return: n/a
#     '''
#     install_reqs = pip.req.parse_requirements('requirements.txt', session='hack')
#     reqs = [str(ir.req) for ir in install_reqs]
#     for r in reqs:
#         r_name, r_version = r.split('=')[0].lower().replace('_', '-'), r.split('=')[-1]
#         try:
#             if r_name == 'beautifulsoup4':
#                 r_name = 'bs4'
#             importlib.import_module(name=r_name, package=r_version)
#
#         except ImportError:
#             pip.main(['install', r_name + '==' + r_version])
#
#         except RuntimeError:
#             install_chromedriver()
#
#         except ModuleNotFoundError:
#             print('Unable to install %s. Please paste the below into the command-line.\n%s' %
#                   (r_name, ' '.join([sys.executable, '-m', 'pip', 'install',
#                                      '=='.join([r_name, r_version])])))
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
    ListTeam = ['ricky.schools@fsinvestments.com']  # , salesops@fsinvestments.com]
    SFDomain = 'fsinvestments.my.salesforce.com'
    SFUser = os.environ['SFUSER']
    SFPass = os.environ['SFPASS']
    SFToken = os.environ['SFTOKEN']
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
