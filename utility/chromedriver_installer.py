import os
import subprocess

import requests
from bs4 import BeautifulSoup

downloads_loc = os.path.expanduser('~\Downloads')


def download_chromewhl():
    whl_url = 'https://pypi.python.org/pypi/chromedriver'
    soup = BeautifulSoup(requests.get(whl_url).content, 'lxml')
    links = soup.findAll('a')
    whl_link = str([link for link in links if link.text[-4:] == '.whl'][0]).split('="')[1].split('">')[0]
    whl_name = [link.text for link in links if link.text[-4:] == '.whl'][0]

    resp = requests.get(whl_link)
    with open(os.path.join(downloads_loc, whl_name), 'wb') as f:
        f.write(resp.content)
    return os.path.join(downloads_loc, whl_name)


def install_whl(loc):
    subprocess.call('python -m pip install %s' % loc)


def install_chromedriver():
    name = download_chromewhl()
    install_whl(name)
