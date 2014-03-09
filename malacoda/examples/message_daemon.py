
import time
from threading import RLock
from malacoda import Malacoda


class MessageDaemon(Malacoda):
    def __init__(self, daemonize=False):
        self.messages = []
        self.pst_counter = 0
        self.lock = RLock()
        super(MessageDaemon, self).__init__(daemonize=daemonize,
                                            pst_config={'class_name': 'PstFileStorage'})

    def _run(self):
        while self.running:
            with self.lock:
                if self.messages:
                    print 'Found %s new messages' % len(self.messages)
                    for msg in self.messages:
                        print msg
                    self.messages = []
            time.sleep(5)

    def insert_message(self, msg):
        with self.lock:
            self.messages.append(msg)
        return 'Message received!'


if __name__ == '__main__':
    MessageDaemon(False)
