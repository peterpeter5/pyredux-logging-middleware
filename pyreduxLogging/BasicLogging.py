from __future__ import absolute_import, unicode_literals

import json
import logging
import logging.config


from pyrsistent import thaw
from pyreduxLogging.Middlewares.Logging import ColoringConsole


class PrettyConsoleFormatter(logging.Formatter):

    def formatTime(self, record, datefmt=None):
        return super(PrettyConsoleFormatter, self).formatTime(record, datefmt)

    def format(self, record):
        std_format = super(PrettyConsoleFormatter, self).format(record)
        if record.msg.startswith("[Action: <"):
            std_format = ColoringConsole.cformat("#CYAN;" + std_format)
        elif record.msg.startswith("[StoreState]"):
            std_format = ColoringConsole.cformat("#MAGENTA;" + std_format)
        return std_format


logging.config.dictConfig({
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "simple": {
                    "format": "[%(asctime)s] :: [%(name)s] :: [%(levelname)s] :: %(message)s"
                },
                "action_state": {
                    "format": "[%(asctime)s] :: %(message)s"}
            },

            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout"
                },

                "action_logger_console": {
                    "class": "logging.StreamHandler",
                    "level": 5,
                    "formatter": "action_state",
                    "stream": "ext://sys.stdout"
                },

                "application_state_logger": {
                        "class": "logging.handlers.RotatingFileHandler",
                        "level": 5,
                        "formatter": "action_state",
                        "filename": "state-history.log",
                        "maxBytes": 10485760,
                        "backupCount": 20,
                        "encoding": "utf8"
                },
            },

            "loggers": {
                "@pyredux-action-state-logging@": {
                    "level": 5,
                    "handlers": ["action_logger_console", "application_state_logger"],
                    "propagate": "no"
                }
            },
        })


class PyReduxLogger(object):

    def __init__(self):
        self.console = logging.getLogger("@pyredux-action-state-logging@")
        for handler in self.console.handlers:
            if handler.name == 'action_logger_console':
                handler.setFormatter(PrettyConsoleFormatter("[%(asctime)s] :: %(message)s"))

    def log_action(self, action):
        log_message = self.action_serializer(action)
        self.console.log(5, log_message)

    def log_state(self, old_state, new_state):
        old_state_dict = thaw(old_state)
        new_state_dict = {(key, value) for key, value in thaw(new_state).items()}
        
        log_message = "[StoreState] :: %s " % json.dumps(new_state_dict)
        self.console.log(5, log_message)

    @staticmethod
    def action_serializer(action):
        return "[Action: <%s>] :: {type: <%s>, payload: <%s>}" % \
               (str(action.__class__.__name__), str(action.type), str(action.payload))
