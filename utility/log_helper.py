import logging
import datetime
import os


class ListManagementLogger:
    def __init__(self):
        self.dir = 'T:/Shared/FS2 Business Operations/Python Search Program/logs/'
        self.__make_dir__()
        self.today = datetime.datetime.today().date().isoformat()
        self.log_name = '%s%s_List_Management.log' % (self.dir, self.today)
        self.config = logging.basicConfig(filename=self.log_name, filemode='w', level=logging.DEBUG,
                                          format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

    def __make_dir__(self):
        if not os.path.isdir(self.dir):
            os.mkdir(self.dir)

