from ListManagement.finra.api import Finra
from ListManagement.utility.log_helper import ListManagementLogger

logger = ListManagementLogger().logger
fin = Finra(log=logger)

path = 'T:/Shared/FS2 Business Operations/Python Search Program/' \
       'New Lists/test_finra_scrape/test_scrape.xlsx'

fin.scrape(path, scrape_type='crd', parse_list=True, save=True)
