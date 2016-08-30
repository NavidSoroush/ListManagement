from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import re
import pandas as pd
from functions import splitname
import unicodedata


def strip_unicode_chars(row):
    '''
    attempts to remove all unicode data from the row values.

    :param row: cell value with unicode chars
    :return: transformed cell value without unicode chars
    '''
    return [unicodedata.normalize('NFKD', r).encode('utf-8', 'ignore') for r in row]


def no_crd_path(path):
    '''
    creates a new file for advisors without CRD numbers.

    :param path: original path
    :return: new path for no_crd file
    '''
    fname = splitname(path)
    rootpath = path[:len(path) - len(fname)]
    fname = fname[:-5] + '_nocrd.xlsx'
    found_path = rootpath + fname
    return found_path


def found_finra_sec_path(path):
    '''
    creates a new file for advisors found by FINRA / SEC scraping.

    :param path: original path
    :return: new path for found file
    '''
    fname = splitname(path)
    rootpath = path[:len(path) - len(fname)]
    fname = fname[:-5] + '_finrasec_found.xlsx'
    found_path = rootpath + fname
    return found_path


def finra_ambiguous_path(path):
    '''
    creates a new file for advisors found by FINRA with more than one
    suggestion in the FINRA search.

    :param path: original path
    :return: new path for ambiguous file file
    '''
    fname = splitname(path)
    rootpath = path[:len(path) - len(fname)]
    fname = fname[:-5] + '_FINRA_ambiguous.xlsx'
    found_path = rootpath + fname
    return found_path


class Finra_Scrape:
    def __init__(self):

