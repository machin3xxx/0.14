
import logging

__title__ = 'requests-futures'
__version__ = '0.9.9'
__build__ = 0x000000
__author__ = 'Ross McFarland'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2013 Ross McFarland'

try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
