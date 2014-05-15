
from datetime import timedelta
from multiprocessing import Process
import cPickle as pickle
import os
import unittest
import time
import socket
import malacoda
import pst_storage

PST_FILE = '/tmp/pst_test.p'

class TestMalacoda(unittest.TestCase):
    def setUp(self):
        with open(PST_FILE, 'wb') as f:
            pickle.dump([('pst_list', [1])], f)
        
    def tearDown(self):
        os.system('rm /tmp/pst_test.p')

    def test_malacoda(self):
        p = Process(target=start_malacoda)
        p.start()
        zp = malacoda.get('SimpleMalacoda')
        self.assertEqual(zp.pst_list, [1])
        zp.update_pst_list([1, 2, 3])
        self.assertEqual(zp.constant, 5)
        zp.constant = 10
        self.assertEqual(zp.constant, 10)
        self.assertTrue(callable(zp.echo))
        self.assertEqual(zp.echo('hello'), 'hello')
        with self.assertRaises(AttributeError):
            zp.unknown()
        with self.assertRaises(socket.timeout):
            zp.timeout(1, timeout=0.1)
        time.sleep(5)
        zp.stop()
        with open(PST_FILE, 'rb') as f:
            self.assertEqual(pickle.load(f), [('pst_list', [1, 2, 3])])
        p.join()

    def test_get_by_port(self):
        p = Process(target=start_malacoda, kwargs={'port': 51001})
        p.start()
        zp = malacoda.get('SimpleMalacoda:51001')
        self.assertEqual(zp.pst_list, [1])
        zp.update_pst_list([1, 2, 3])
        time.sleep(5)
        zp.stop()
        with open(PST_FILE, 'rb') as f:
            self.assertEqual(pickle.load(f), [('pst_list', [1, 2, 3])])
        p.join()
            
def start_malacoda(port=None):
    SimpleMalacoda(daemonize=False, port=port)


class SimpleMalacoda(malacoda.Malacoda):
    def __init__(self, daemonize=False, port=None):
        self.constant = 5
        self.pst_list = None
        stdout = open('/tmp/stdout', 'w+')
        pst_config = {'class_name': 'PstFileStorage', 'frequency': timedelta(seconds=2),
                      'file_path': PST_FILE}
        super(SimpleMalacoda, self).__init__(pst_config=pst_config,
                                             daemonize=daemonize, stdout=stdout,
                                             stderr=stdout, files_preserve=[stdout],
                                             port=port)

    def _run(self):
        while self.running:
            time.sleep(5)

    def update_pst_list(self, new_list):
        self.pst_list = new_list

    def echo(self, text):
        return text

    def timeout(self, t=10):
        time.sleep(t)

    def fn(self):
        return self.echo


if __name__ == '__main__':
    unittest.main()
