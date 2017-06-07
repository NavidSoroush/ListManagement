import os
import sys
import unicodedata


def strip_unicode_chars(row):
    """
    attempts to remove all unicode data from the row values.

    :param row: cell value with unicode chars
    :return: transformed cell value without unicode chars
    """
    return [unicodedata.normalize('NFKD', str(r)).encode('utf-8', 'ignore') for r in row]


def find_chrome_driver_location(filename='chromedriver'):
    """
    finds the file path location of the 'chromedriver' on the local machine
    :param filename: default='chromedriver'
    :return: file path string
    """
    path = os.path.join(os.path.dirname(sys._getframe(1).f_code.co_filename), filename)
    return path
