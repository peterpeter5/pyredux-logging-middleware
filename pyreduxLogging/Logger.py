from __future__ import absolute_import, unicode_literals
from pyreduxLogging import middleware
from pyreduxLogging.Middlewares.Logging.BasicLogging import PyReduxLogger

logger = PyReduxLogger()


@middleware
def redux_logger(store, next_middleware, action):
    logger.log_action(action)
    old_state = store.state
    next_middleware(action)
    new_state = store.state
    logger.log_state(old_state, new_state)