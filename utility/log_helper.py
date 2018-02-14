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
    def __init__(self, name=None, abbr=None, dir_=None, level='debug', maintain=True):
        self.tmp_dir = 'C:\\'
        self.name, self.abbr, self.dir = self._default_dir(name, abbr, dir_)
        self.dir = self.__make_dir__(dir_=self.dir, maintain=maintain)
        self.today = datetime.datetime.today().date().isoformat()
        self.log_name = '%s%s_%s_%s.log' % (self.dir, self.today, username, self.name)
        self.logger = self.config(self.abbr, level)

    @staticmethod
    def set_level(logger, level):
        if level == 'debug':
            logger.setLevel(logging.DEBUG)
        elif level == 'info':
            logger.setLevel(logging.INFO)
        elif level == 'warn':
            logger.setLevel(logging.WARN)
        return logger

    @staticmethod
    def _default_dir(name, abbr, _dir):
        if None in [name, abbr, _dir]:
            return 'ListManagement', 'FS_LMA', \
                   'T:\\Shared\\FS2 Business Operations\\Python Search Program\\logs\\'
        else:
            return name, abbr, _dir

    def config(self, name, level):
        """
        helps to setup the configuration of the FS_LMA logger
        1) create a logger object
        2) create a file handler and set the level
        3) create a stream (console) handler and set the level
        4) dictate the formatting of the handler
        :return: configured logger object
        """
        logger = logging.getLogger(name)
        logger = self.set_level(logger, level)

        file_handler = TimedRotatingFileHandler(filename=self.log_name, when='midnight', backupCount=1)
        file_handler = self.set_level(file_handler, level)

        console_handler = logging.StreamHandler()
        console_handler = self.set_level(console_handler, level)

        log_format = logging.Formatter(
            fmt='%(asctime)s_%(user)s_%(module)s__%(levelname)s__: %(message)s',
            datefmt='%m/%d/%Y %I:%M:%S %p')
        file_handler.setFormatter(log_format)

        logger.addFilter(ContextFilter())
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger

    def __make_dir__(self, dir_, maintain):
        dir_ = self._determine_location(self.tmp_dir, dir_)
        if not os.path.isdir(dir_):
            os.mkdir(dir_)
        if maintain:
            self._maintain(dir_)
        return dir_

    @staticmethod
    def _determine_location(tmp, dir_):
        if dir_ is None or '\\' not in dir_:
            if dir_ is None:
                dir_ = tmp
            elif '\\' not in dir_:
                if not os.path.isdir(tmp):
                    os.mkdir(tmp)
                dir_ = tmp + dir_
        if dir_[-1] != '\\':
            dir_ = dir_ + '\\'
        return dir_

    @staticmethod
    def _maintain(_dir):
        from datetime import datetime as dt
        for f in os.listdir(_dir):
            delta = dt.now() - dt.fromtimestamp(os.path.getmtime(os.path.join(_dir, f)))
            if delta.days > 30:
                os.remove(os.path.join(_dir, f))
