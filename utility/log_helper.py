import logging
from logging.handlers import TimedRotatingFileHandler
import datetime
import os

from cred import username


class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.
    """

    def filter(self, record):
        record.user = username
        return True


class ListManagementLogger:
    def __init__(self):
        self.dir = 'T:/Shared/FS2 Business Operations/Python Search Program/logs/'
        self.__make_dir__()
        self._maintain(self.dir)
        self.today = datetime.datetime.today().date().isoformat()
        self.log_name = '%s%s_%s_List_Management.log' % (self.dir, self.today, username)
        self.logger = self.config()

    def config(self):
        """
        helps to setup the configuration of the FS_LMA logger
        1) create a logger object
        2) create a file handler and set the level
        3) create a stream (console) handler and set the level
        4) dictate the formatting of the handler
        :return: configured logger object
        """
        logger = logging.getLogger('FS_LMA')
        logger.setLevel(logging.DEBUG)

        file_handler = TimedRotatingFileHandler(filename=self.log_name, when='midnight', backupCount=1)
        file_handler.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        log_format = logging.Formatter(
            fmt='%(asctime)s_%(user)s_%(module)s__%(levelname)s__: %(message)s',
            datefmt='%m/%d/%Y %I:%M:%S %p')
        file_handler.setFormatter(log_format)

        logger.addFilter(ContextFilter())
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger

    def __make_dir__(self):
        if not os.path.isdir(self.dir):
            os.mkdir(self.dir)

    @staticmethod
    def _maintain(_dir):
        from datetime import datetime as dt
        for f in os.listdir(_dir):
            delta = dt.now() - dt.fromtimestamp(os.path.getmtime(os.path.join(_dir, f)))
            if delta.days > 30:
                os.remove(os.path.join(_dir, f))
