"""
general.py
====================================
Houses functions that are used
throughout the list processing process.
"""

import os
import sys
import re
import time
import datetime
from dateutil.parser import parse
import shutil
import errno
import ntpath

import pandas as pd
from sqlalchemy import create_engine

from cred import *

userName = userName
userEmail = userEmail
userPhone = userPhone

user = os.environ.get("USERNAME")
today = datetime.datetime.strftime(datetime.datetime.now(), '%m_%d_%Y')
m_d_y = format(datetime.datetime.now(), '%m-%d-%y')
time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
yyyy_mm = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m')
_accepted_cols = [
    'CRDNumber', 'FirstName', 'LastName', 'AccountId'
    , 'MailingStreet', 'MailingCity', 'MailingState', 'MailingPostalCode'
    , 'SourceChannel', 'Email', 'Website', 'AUM', 'GDC', 'Fax'
    , 'HomePhone', 'MobilePhone', 'Phone'
]
_necessary_cols = _accepted_cols[:8]
_bdg_accepted_cols = ['ContactID', 'BizDev Group', 'Licenses']
_cmp_accepted_cols = ['ContactID', 'CampaignId', 'Status']
_new_path_names = ['_nocrd', '_finrasec_found', '_FINRA_ambiguous',
                   '_review_contacts', '_foundcontacts', 'cmp_to_create',
                   'cmp_upload', 'no_updates', 'to_update', 'to_create', 'bdg_update',
                   'to_add', 'to_stay', 'current_members', 'to_remove']


def is_path(path):
    """
    Checks if a given path is a file.

    Parameters
    ----------
    path
        A string. Should be a path to a directory or file.

    Returns
    -------
        Boolean (True or False)
    """
    if os.path.isfile(path):
        return True
    else:
        return False


def duration(start, end):
    """
    Creates a string representation of the time elapsed between start and end.

    Parameters
    ----------
    start
        Timestamp/datetime object of when a process began.
    end
        Timestamp/datetime object of when a process ended.
    Returns
    -------
        A formatted time representing the elapsed time in hours, minutes, and seconds.
    """
    _min, _sec = divmod((end - start), 60)
    _hour, _min = divmod(_min, 60)
    string_duration = "%02d:%02d:%02d" % (_hour, _min, _sec)
    return string_duration


def date_parsing(str_date_value):
    """
    Converts a string to a datetime object.

    Parameters
    ----------
    str_date_value
        String representation of a date.
    Returns
    -------
        Datetime object of given date.
    """
    return datetime.datetime.strptime(str_date_value, '%a, %d %b %Y %H:%M:%S %z')


def split_dir_name(full_path):
    """
    Provides a file name given a full path.

    Parameters
    ----------
    full_path
        A string representation of a full file path.

    Returns
    -------
        A file name.
    """
    f_name = os.path.split(os.path.abspath(full_path))
    return f_name[1]


def determine_ext(f_name):
    """
    Determines the extension of a file given a file name.

    Parameters
    ----------
    f_name
        Name of a file.
        Examples: ABC_1234.xlsx, my_file.csv

    Returns
    -------
        The extension of a file and it's length.
        Examples: (5, .xlsx), (4, .csv)

    """
    filename, file_ext = os.path.splitext(f_name)
    del filename
    return len(file_ext), file_ext.lower()


def last_list_uploaded_data(object_id):
    """
    Builds a list containing the 'object_id' and the current time (in ISO-format).

    Parameters
    ----------
    object_id
        A string representation of a Salesforce object id.

    Returns
    -------
        A list.
        Examples: [object_id, current time in ISO-format.]
    """
    uploaded_date = datetime.datetime.utcnow().isoformat()
    return [object_id, uploaded_date]


def shorten_fname_to_95chars(f_name):
    """
    Shortens a filename to less than 95 characters.

    Parameters
    ----------
    f_name
        A string representing a file name.

    Returns
    -------
        A string representing a file name (updated, if necessary).
    """
    ext_len, file_ext = determine_ext(f_name)
    f_name = f_name[:-ext_len]
    max_len = 95 - ext_len

    if len(f_name) > max_len:
        f_name = f_name[:max_len] + file_ext

    return f_name


def split_name(path):
    """
    Splits a path into 1) the containing folder and 2) the file name.

    Parameters
    ----------
    path
        A string representing a full file path.

    Returns
    -------
        A string representing a file name.
    """
    name = os.path.split(os.path.abspath(path))
    if name[1][-1] == ' ':
        name[1] = name[1][:-1]
    return name[1]


def convert_unicode_to_date(date_string):
    """
    Transforms a string containing a date into a datetime object. Decides if
    the date is in the future or in the past.

    Parameters
    ----------
    date_string
        A string representing a date.

    Returns
    -------
        A tuple containing the 1) datetime object and 2) if the date is in the future or past.
    """
    date_string = parse(date_string)
    today = datetime.datetime.now()
    diff = today - date_string
    if diff.days > 0:
        time_type = 'Post'
    else:
        time_type = 'Pre'
    return date_string, time_type


def create_dir_move_file(path):
    """
    Creates and moves a given file from it's current directory to a child directory.

    Parameters
    ----------
    path
        A string representing a full file path.

    Returns
    -------
        A string representing the new full file path location.
    """
    og_path = path[0]
    name = split_name(path[0])
    ext_len, file_ext = determine_ext(name)
    new_path = og_path[:-int(ext_len)]
    if not os.path.isdir(new_path):
        try:
            os.makedirs(new_path)
        except OSError:
            if OSError.errno == errno.EEXIST and os.path.isdir(new_path):
                pass
            else:
                raise

    shutil.copy(og_path, new_path)
    new_path = new_path + '/' + name
    os.remove(og_path)
    return new_path


def clean_phone_number(number):
    """
    Aims to normalize the formatting of a phone number.

    Parameters
    ----------
    number
        A string representation of a phone number.

    Returns
    -------
        A normalized & updated string representation of a phone number.
    """
    phone = re.sub(r'\D', '', str(number))
    phone = phone.lstrip('1')
    if len(phone) > 10:
        return '({}) {}-{}x{}'.format(phone[0:3], phone[3:6], phone[6:10], phone[10:])

    elif len(phone) < 10:
        return ''
    else:
        return '({}) {}-{}'.format(phone[0:3], phone[3:6], phone[6:])


def drop_unneeded_columns(df, obj, ac=_accepted_cols, create=True, bdg=False):
    """
    Removes all columns that are not needed by Business Solutions' Salesforce
    bulk uploading tool.

    Parameters
    ----------
    df
        A pandas data frame containing a list.
    obj
        A string representing a Salesforce object.
    ac
        A list containing the columns accepted by the bulk tool.
    create
        Boolean. Denotes if this call is coming from a 'to_create' contacts
        request or not.
    bdg
        Boolean. Denotes if this call is coming from a BizDev Group request
        or not.

    Returns
    -------
        An updated pandas data frame object containing only the
        bulk tool's accepted columns.
    """
    if bdg:
        ac = _bdg_accepted_cols
    headers = df.columns.values
    if obj != 'Campaign' or create:
        for header in headers:
            if header not in ac:
                del df[header]
        return df
    else:
        for header in headers:
            if header not in _cmp_accepted_cols:
                del df[header]
        return df


def determine_move_to_bulk_processing(df):
    """
    Determines of a list request contains the necessary columns (meta-data)
    to be passed to Business Solutions' Salesforce bulk processing tool.

    Parameters
    ----------
    df
        A pandas data frame containing a list.
    Returns
    -------
        Boolean (True or False).
    """
    headers = df.columns.values
    for ac in _necessary_cols:
        if ac not in headers:
            move = False
            break
        else:
            move = True
    if len(df.index) == 0:
        move = False
    return move


def save_conf_creation_meta(sc, objid, status):
    engine = create_engine('mssql+pyodbc://DPHL-PROPSCORE/ListManagement?driver=SQL+Server')
    data_package = [['Date', 'ObjId', 'SourceChannel', 'Status', 'AddedToCampaign'],
                    [time_now, objid, sc, status, False]]
    df = pd.DataFrame(data_package[1], data_package[0]).T
    df.to_sql('ConferenceCreation', con=engine, index=False, if_exists='append')
    engine.dispose()
    del df


def remove_underscores(line):
    """
    Replaces underscores with spaces.

    Parameters
    ----------
    line
        A string representing a single cell of a pandas data frame.
    Returns
    -------
        A updated string, without underscores.
    """
    try:
        if "_" in str(line):
            line = str(line.replace("_", " "))
    except:
        pass
    return line


def split_by_uppers(line):
    """
    Takes a string and if no spaces are present, splits them by the present
    upper case values.

    Parameters
    ----------
    line
        A string value.
    Returns
    -------
        An updated string value.
    """
    line = remove_underscores(line)
    try:
        x = 0
        sum(x + 1 for i in range(len(line)) if line[i].isupper() == True)
        if len(line) > 5 and x / len(line) >= .7 and (" " not in line):
            tmp = re.findall('[A-Z][^A-Z]*', line)
            return_words = " ".join(tmp)
        else:
            return_words = line

    except:
        return_words = line

    return return_words


def lower_head_values(lname):
    """
    Converts a string to lower-case.
    Parameters
    ----------
    lname
        A string.

    Returns
    -------
        A lower-case string.
    """
    tmp = []
    for i in lname:
        i = split_by_uppers(i)

        try:
            tmp.append(str(i.lower()))
        except:
            tmp.append(str(i))
    return tmp


def path_leaf(path):
    """
    Dynamic function to return a file or folder name.
    Parameters
    ----------
    path
        A string representing a file name.
    Returns
    -------
        A file name or a directory.
    """
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def create_path_name(path, new_name):
    """
    Creates a new file name given a path and a new name.
    Parameters
    ----------
    path
        A string representing the original name of a file.
    new_name
        A string representing a new suffix to append to the existing file name.
    Returns
    -------
        An updated string representing the new file name.
    """
    if new_name not in _new_path_names:
        raise TypeError("new_name of '%s' is not valid. Must be in %s." % (new_name, ', '.join(_new_path_names)))
    name = split_dir_name(path)
    root = path[:len(path) - len(name)]
    name = name[:-5] + new_name + '.xlsx'
    return root + name


def drop_in_bulk_processing(path, log):
    """
    Drops a file and passes it to the bulk tool Business Solution built.
    Parameters
    ----------
    path
        A string representing a full file name.
    log
        A log instance.
    Returns
    -------
        Nothing
    """
    if path is not None:
        dest = '//sc12-fsphl-01/BulkImports/'
        # \\sc12-fsphl-01\BulkImports\
        name = shorten_fname_to_95chars(split_name(path=path))
        log.info('Dropping %s for bulk processing.' % name)
        shutil.copy(path, dest + name)


def clean_date_values(d_value):
    """
    Transforms a string into a datetime object.
    Parameters
    ----------
    d_value
        A string representing a date.
    Returns
    -------
        A datetime object.

    """
    d_value = parse(d_value)
    return d_value


def date_to_string(d_value):
    """
    Turns a datetime object into a string.
    Parameters
    ----------
    d_value
        A datetime object.
    Returns
    -------
        The string representation of a date.
    """
    return datetime.datetime.strftime(d_value, '%m/%d/%Y %H:%M:%S')


def timedelta_to_processing_str(duration):
    """
    Transforms a timestamp into a string representing the time in days, hours, minutes, & seconds.
    Parameters
    ----------
    duration
        A timestamp object.
    Returns
    -------
        String representation of duration.
    """
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    return '{} days {} hours {} minutes {} seconds'.format(days, hours, minutes, seconds)


def auto_maintain(directory, destination=None, ndays=30, log=None):
    """
    This function helps to maintain a given directory by deleting files older than ndays old.

    Parameters
    ----------
    directory
        A string representing the directory (folder) to maintain.
    destination
        Optional. A string representing the directory to move a file to.
    ndays
        An integer representing a ceiling for the age of files to keep.
    log
        A logger instance.

    Returns
    -------
        Nothing
    """
    cleaned = 0
    dt = datetime.datetime
    for f in os.listdir(directory):
        delta = dt.now() - dt.fromtimestamp(os.path.getmtime(os.path.join(directory, f)))
        if delta.days > ndays:
            cleaned += 1
            if destination is None:
                os.remove(os.path.join(directory, f))
            else:
                shutil.move(os.path.join(directory, f), os.path.join(destination, f))
    msg = 'Removed %s old files from %s.' % (cleaned, directory)
    if log is not None:
        log.info(msg)
    else:
        print(msg)


def record_processing_stats(values, save=True):
    """
    Records a backup of the metadata associated from processing a list in SQL and Excel.

    Parameters
    ----------
    values
        A collection of values to record related to a lists processing.
    save
        Boolean (True or False). Dictates whether to save or return a data frame.
    Returns
    -------
        A dictionary (if save=True) or pandas data frame representing
        the stats recorded during list processing (if save=False).
    """
    import sqlalchemy
    _stats_file_path = 'T:/Shared/FS2 Business Operations/Python Search Program/Search Program Stats2.xlsx'
    print('\nStep 11. Recording stats from processing.')
    df2 = pd.DataFrame.from_dict(values, orient='index').transpose()
    if save:
        df = pd.read_excel(_stats_file_path)
        engine = sqlalchemy.create_engine('mssql+pyodbc://DPHL-PROPSCORE/ListManagement?driver=SQL+Server')
        df2.to_sql(name='SearchStats', con=engine, if_exists='append', index=False)
        df = df.append(df2, ignore_index=True, sort=False)
        df.to_excel(_stats_file_path, index=False)
        del df
        del df2
        return {'Next Step': 'Done.'}
    else:
        return df2


def strip_unicode_chars(row):
    """
    Attempts to coerce all data to UTF-8.

    Parameters
    ----------
    row
        A string value, representing a single cell (value)
    Returns
    -------
        A coerced string value.
    """
    row.fillna('', inplace=True)
    row.astype(str)
    try:
        row.apply([r.encode('utf-8', 'ignore').strip() for r in row], axis=1)
    except:
        pass
    return row
    # return [unicodedata.normalize('NFKD', str(r)).encode('utf-8', 'ignore') for r in row]


def find_chrome_driver_location(filename='chromedriver'):
    """
    Helper method to find the location of 'chromedriver'.

    Parameters
    ----------
    filename
        The name of a file to find.
    Returns
    -------
        Location where given file is found.
    """
    """
    finds the file path location of the 'chromedriver' on the local machine
    :param filename: default='chromedriver'
    :return: file path string
    """
    path = os.path.join(os.path.dirname(sys._getframe(1).f_code.co_filename), filename)
    return path


def myprogressbar(batchsize, totalsize, barlength=25, message='', char="#"):
    """
    Helper method to display a progress bar.

    Parameters
    ----------
    batchsize
        An integer representing the number of records processed.
    totalsize
        An integer representing the size of a list.
    barlength
        A customizable integer representing the length of a bar.
    message
        A string customizing representing the name of the bar.
    char
        A string. The character to populate the progress bar.
    Returns
    -------
        Nothing
    """
    if totalsize == 0:
        raise ZeroDivisionError('%s division by zero in denominator.' % type(totalsize))
    addtooutput = cmdorgui()
    percent = batchsize / float(totalsize)
    chars = char * int(round(percent * barlength))
    spaces = " " * (barlength - len(chars))
    output = '\r' + message + '[{0}] {1:.1f}% ({2}/{3})'.format(chars + spaces,
                                                                round(percent * 100, 2),
                                                                batchsize,
                                                                totalsize) + addtooutput
    sys.stdout.write(output)
    sys.stdout.flush()


def cmdorgui():
    """
    Helper method to itentify if the running version of python is command line or GUI.

    Returns
    -------
        Nothing
    """
    a = sys.executable
    m = '\\'
    m = m[0]
    while True:
        b = len(a)
        c = a[(b - 1)]
        if c == m:
            break
        a = a[:(b - 1)]
    if sys.executable == a + 'pythonw.exe':
        # Running in IDLE GUI interface
        return '\n'
    else:
        # Running from the command line
        return ''

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


# import os
# import subprocess
#
# import requests
# from bs4 import BeautifulSoup
#
# downloads_loc = os.path.expanduser('~\Downloads')
#
#
# def download_chromewhl():
#     whl_url = 'https://pypi.python.org/pypi/chromedriver'
#     soup = BeautifulSoup(requests.get(whl_url).content, 'lxml')
#     links = soup.findAll('a')
#     whl_link = str([link for link in links if link.text[-4:] == '.whl'][0]).split('="')[1].split('">')[0]
#     whl_name = [link.text for link in links if link.text[-4:] == '.whl'][0]
#
#     resp = requests.get(whl_link)
#     with open(os.path.join(downloads_loc, whl_name), 'wb') as f:
#         f.write(resp.content)
#     return os.path.join(downloads_loc, whl_name)
#
#
# def install_whl(loc):
#     subprocess.call('python -m pip install %s' % loc)
#
#
# def install_chromedriver():
#     name = download_chromewhl()
#     install_whl(name)
