import importlib
import pip
import sys

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
        r_name, r_version = r.split('=')[0].lower().replace('_', '-'), r.split('=')[-1]
        try:
            if r_name == 'beautifulsoup4':
                r_name = 'bs4'
            importlib.import_module(name=r_name, package=r_version)

        except ImportError:
            pip.main(['install', r_name + '==' + r_version])

        except RuntimeError:
            install_chromedriver()

        except ModuleNotFoundError:
            print('Unable to install %s. Please paste the below into the command-line.\n%s' %
                  (r_name, ' '.join([sys.executable, '-m', 'pip', 'install',
                                     '=='.join([r_name, r_version])])))
