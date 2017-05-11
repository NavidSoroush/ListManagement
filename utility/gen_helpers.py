import os
import re
import time
import datetime
import shutil
import errno
import ntpath
from dateutil.parser import parse
from cred import userPhone, userEmail, userName, sf_uid

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
    , 'HomePhone', 'MobilePhone', 'Phone', 'toAlternatives', 'toAdvisory'
]
_necessary_cols = _accepted_cols[:8]
_bdg_accepted_cols = ['ContactID', 'BizDev Group', 'Licenses']
_cmp_accepted_cols = ['ContactID', 'CampaignId', 'Status']
_new_path_names = ['_nocrd', '_finrasec_found', '_FINRA_ambiguous',
                   '_review_contacts', '_foundcontacts', 'cmp_to_create',
                   'cmp_upload', 'no_updates', 'to_update', 'to_create', 'bdg_update',
                   'toAdd', 'bdg_toStay', 'current_bdg_members', 'to_remove']


def split_dir_name(full_path):
    """
    receives a full path name splits it into directory, file name
    :param full_path: required
    :return: returns the file name (f_name)
    """
    f_name = os.path.split(os.path.abspath(full_path))
    return f_name[1]


def determine_ext(f_name):
    '''
    determines the extension type of the file.

    :param f_name: original file name (required)
    :return: tuple of shorten file name and file extension
    '''
    filename, file_ext = os.path.splitext(f_name)
    if file_ext == '.csv' or file_ext == '.pdf' or file_ext == '.xls':
        ext_len = 4
    elif file_ext == '.xlsx':
        ext_len = 5
    else:
        raise BaseException('No file name was passed. A variable could have been referenced before it was assigned.')

    del filename
    return ext_len, file_ext


def shorten_fname_to_95chars(f_name):
    """
    evaulates if the file name is longer than 95 characters.
    if so, then it shortens it so that AB's processing accepts it
    :param f_name: original file name
    :return: s_f_name (shortened file name)
    """
    ext_len, file_ext = determine_ext(f_name)
    f_name = f_name[:-ext_len]
    max_len = 95 - ext_len

    if len(f_name) > ():
        f_name = f_name[:max_len] + file_ext

    return f_name


def split_name(path):
    '''
    splits the directory name into folder location and file name.

    :param path: directory to a file
    :return: filename of path
    '''
    name = os.path.split(os.path.abspath(path))
    if name[1][-1] == ' ':
        name[1] = name[1][:-1]
    return name[1]


def convert_unicode_to_date(date_string):
    '''
    transforms a date-string to a date. based on the date
    determines if a campaign has happened or if it is upcoming.

    :param date_string: string of a date value.
    :return: variable, is the list pre or post.
    '''
    date_string = parse(date_string)
    today = datetime.datetime.now()
    diff = today - date_string
    if diff.days > 0:
        time_type = 'Post'
    else:
        time_type = 'Pre'
    return date_string, time_type


def create_dir_move_file(path):
    '''
    takes a file path, and from the file's name, it creates
    a new folder for the file.

    :param path: file path
    :return: the new path of the file passed to the function.
    '''
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
    phone = re.sub(r'\D', '', str(number))
    phone = phone.lstrip('1')
    if len(phone) > 10:
        return '({}) {}-{}x{}'.format(phone[0:3], phone[3:6], phone[6:10], phone[10:])

    elif len(phone) < 10:
        return ''
    else:
        return '({}) {}-{}'.format(phone[0:3], phone[3:6], phone[6:])


def drop_unneeded_columns(df, obj, ac=_accepted_cols, create=True, bdg=False):
    '''
    removes all columns that are not needed by Andrew's processing tool.

    :param df: list data frame
    :param obj: SFDC object or list type
    :param ac: accepted columns by Andrew's program
    :param create: boolean, default is true
    :return: updated data frame
    '''
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
    '''
    identifies if the list has all the headers needed to
    be pushed to Andrew's bulk processing tool

    :param df: list data frame
    :return: boolean
    '''
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


def remove_underscores(line):
    '''
    replaces underscores with spaces.
    :param line: original cell value
    :return: transformed cell value without '_' underscores
    '''
    try:
        if "_" in str(line):
            line = str(line.replace("_", " "))
    except:
        pass
    return line


def split_by_uppers(line):
    '''
    takes row of dataframe and if the entire word is upper case
    it attempts to split it if there are no spaces.
    :param line: dataframe cell value
    :return: split cell value
    '''
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
    '''
    transforms dataframe cell value to all lowercase letters.

    :param lname: value
    :return: returns lower-case format of value.
    '''
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
    :param path: path to a file
    :return: file name or file directory.
    """
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def create_path_name(path, new_name):
    """
    create a new file name, dynamically, based on the path and the name provided
    :param path: orignal dir and name of file
    :param new_name: name to append
    :return: new file name
    """
    if new_name not in _new_path_names:
        raise TypeError("new_name of '%s' is not valid. Must be in %s." % (new_name, ', '.join(_new_path_names)))
    name = split_dir_name(path)
    root = path[:len(path) - len(name)]
    name = name[:-5] + new_name + '.xlsx'
    return root + name


def drop_in_bulk_processing(path):
    dest = '//sc12-fsphl-01/BulkImports/'
    #\\sc12-fsphl-01\BulkImports\
    name = shorten_fname_to_95chars(split_name(path=path))
    shutil.copy(path, dest + name)


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
    return datetime.datetime.strftime(d_value, '%m/%d/%Y %H:%M:%S')


def timedelta_to_processing_str(duration):
    """
    returns the elapsed time for list processing
    :param duration: end time - start time
    :return: string of elapsed time
    """
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    return '{} days {} hours {} minutes {} seconds'.format(days, hours, minutes, seconds)
