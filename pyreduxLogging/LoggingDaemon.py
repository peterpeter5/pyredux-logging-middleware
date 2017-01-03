from __future__ import absolute_import, unicode_literals

from collections import deque
from threading import Thread
import logging
import time
from socketclusterclient import Socketcluster


class SCServerStateBase(object):

    def __init__(self, log_history):
        self.log_history = log_history

    def start_new_log(self, initial_state):
        self.log_history.append({
            "type": "INIT",
            "payload": initial_state,
        })

    def log_action(self, action, state):
        new_action_state = self._format_action_state_for_sc_server(action, state)
        self.log_history.append(new_action_state)
        return new_action_state

    def resend_history(self):
        raise NotImplementedError()

    def _get_history(self):
        return [history for history in self.log_history]

    @staticmethod
    def _format_action_state_for_sc_server(action, state):
        """
        :type action: collections.Mapping
        :type state: collections.Mapping
        :return: dict
        """
        return {
            "type": "ACTION",
            "payload": state,
            "action": {
                "timestamp": int(time.time()*1000),
                "action": action
            },

        }


class NotConnectedToScServer(SCServerStateBase):

    def __init__(self, log_history):
        super(NotConnectedToScServer, self).__init__(log_history)

    def log_action(self, action, state):
        return super(NotConnectedToScServer, self).log_action(action, state)

    def resend_history(self):
        raise EnvironmentError("No Connection to SC-Server establish! Therefor unable to resend data!")


class ConnectedToScServer(SCServerStateBase):

    def __init__(self, log_history, server_socket):
        super(ConnectedToScServer, self).__init__(log_history)
        self.server_socket = server_socket

    def log_action(self, action, state):
        action_state = super(ConnectedToScServer, self).log_action(action, state)
        self.server_socket.emit("log-noid", action_state)
        return action_state

    def resend_history(self):
        for event in self._get_history():
            self.server_socket.emit("log-noid", event)


class SocketClusterServer(object):

    def __init__(self, socket_address, on_established, on_closed, on_server_message):
        self.on_server_message = on_server_message
        self.on_closed = on_closed
        self.on_established = on_established
        self.socket_address = socket_address
        self._socket = None
        self.__start_up_socket = self._make_configured_initial_socket(socket_address)

    def _make_configured_initial_socket(self, socket_address):
        initial_socket = Socketcluster.socket(socket_address)
        initial_socket.setAuthenticationListener(None, self._sc_on_authentication)
        initial_socket.setBasicListener(self._sc_on_connect, self._sc_connection_closed, self._sc_connection_closed)
        return initial_socket

    def _sc_connection_closed(self, socket, error=None):
        self.on_closed(socket, error)

    def _sc_on_authentication(self, socket, is_authenticated):
        assert is_authenticated is False
        self._socket = socket
        socket.emitack('login', 'master', self._sc_on_login)

    def _sc_on_login(self, key, error, channel_name):
        self._socket.subscribe(channel_name)
        self._socket.onchannel(channel_name, self._sc_handle_server_messages)
        self._socket.on(channel_name, self._sc_handle_server_messages)
        self.on_established(self._socket)

    def _sc_handle_server_messages(self, channel, message):
        logging.info("Handle ServerMessage: %s from channel %s" % (message, channel))
        self.on_server_message(channel, message)

    def _sc_on_connect(self, socket):
        logging.info("Connected to SC-Server. Waiting for authentication")

    def connect(self):
        self.__start_up_socket.connect()


class ReduxDevToolsLogger(Thread):

    def __init__(self, socket_address=None):
        super(ReduxDevToolsLogger, self).__init__()
        self.log_history = deque([], maxlen=1000)
        if socket_address is None:
            socket_address = "ws://localhost:8000/socketcluster/"

        self._socket_server = SocketClusterServer(
            socket_address,
            self._on_connection_established,
            self._on_connection_closed,
            self._on_connection_closed
        )
        self._connection = NotConnectedToScServer(self.log_history)

    def run(self):
        self._socket_server.connect()

    def _on_connection_established(self, socket):
        logging.info("Successfully logged in and subscribed")

        self._connection = ConnectedToScServer(self.log_history, socket)
        self._connection.resend_history()

    def _on_connection_closed(self, socket, error=None):
        self._connection = NotConnectedToScServer(self.log_history)

    def log_action_state(self, action, state):
        self._connection.log_action(action, state)

    def start_new_log(self, initial_state):
        self._connection.start_new_log(initial_state)


def get_new_remote_redux_logger(initial_state):
    logger = ReduxDevToolsLogger()
    logger.start()
    logger.start_new_log(initial_state)
    return logger


if __name__ == '__main__':
    import random
    logger = get_new_remote_redux_logger({"todos": []})
    time.sleep(1)
    logger.log_action_state({"type": "ADD_TODO"}, {"todos": [1]})
    logger.log_action_state({"type": "ADD_TODO"}, {"todos": [1, 2, random.randint(0, 50)]})
