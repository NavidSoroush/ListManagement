import pip

try:
    from ListManagement.utility.chromedriver_installer import install_chromedriver
except:
    from utility.chromedriver_installer import install_chromedriver


def ensure_requirements_met():
    '''
    this function is meant to ensure that if the requirements of the list program
    are automatically checked, and met, prior to running the program.

    :return: n/a
    '''
    install_reqs = pip.req.parse_requirements('requirements.txt', session='hack')
    reqs = [str(ir.req) for ir in install_reqs]
    for r in reqs:
        try:
            __import__(r)
        except:
            if r != 'chromedriver':
                pip.main(['install', r])
            else:
                install_chromedriver()
    print('All requirements are successfully installed.')


ensure_requirements_met()
