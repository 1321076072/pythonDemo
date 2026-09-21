import logging


class LoggingUtil:

    def __init__(self, name):
        self.name = name
        self.logger = None

    def init_logger(self):
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, *args):
        if self.logger is None:
            self.init_logger()
        msg = " ".join(str(a) for a in args)
        self.logger.info(msg)

    def debug(self, *args):
        if self.logger is None:
            self.init_logger()
        msg = " ".join(str(a) for a in args)
        self.logger.debug(msg)

    def error(self, *args):
        if self.logger is None:
            self.init_logger()
        msg = " ".join(str(a) for a in args)
        self.logger.error(msg)
