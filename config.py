import pip


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
            pip.main(['install', r])
    print('All requirements are successfully installed.')

ensure_requirements_met()