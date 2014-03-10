
Malacoda
========

Malacoda is an extension of ordinary Python Daemons that adds methods for communicating
between daemons, even across network, and storage of persistant data.

A Malacoda in its simplest form is a class that inherits the base class Malacoda, defines a __init__-method that calls __init__ on the base class and defines a method _run that performs the actual work.
The following is an example of a simple daemon, (you can find the code in the examples directory).

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
            
The daemon is started simply by instantiating the class:
    MessageDaemon(False)

We can then connect to the daemon, even from another server, by creating a proxy that uses a ZeroMQ-socket to communicate with the daemon. Using the proxy you can access the daemons methods and variables in (almost) the same way as if you had an instance of the real class:

    import malacoda
    d = malacoda.get('MessageDaemon')
    d.insert_message('hello world')
    >> Message received!
    d.pst_counter
    >> 1
    d.stop()

    
Initializing a daemon
---------------------
You need to initialize the parent class in the constructor of your daemon, in its simplest form
this is done as follows:

    super(MessageDaemon, self).__init__(self)

Init can take a number of optional keyword arguments:
 - name: The name of the daemon, defaults to class name. This name is used for finding the
 daemon when creating a proxy to it.
 - bind_address: Address to bind communication socket to, default is 0.0.0.0.
 - port: Bind communication socket to this port. By default a port in the range 51000-51100 is selected.
 - daemonize: Whether to go into daemon context or not. Can be useful to set this to False when
 testing or if the program needs to run in the foreground.
 - pst_config: Dictionary for configurating the persistant storage. To activate persistant storage send in a dict containing the class name of the persistant storer and any parameters to the storer. Default is a persister that saves variables to a file every minute.
 - kwargs: Any remaining kwargs are sent into daemon.DaemonContext and can be used for more exact control of the daemon. (See [here](http://legacy.python.org/dev/peps/pep-3143/#daemoncontext-objects) for information about available parameters.)

 The run-method
 --------------
 You need to override the method _run in your daemon class. This method should define the main loop of your program and should follow this pattern:

    while self.running:
        do work
    self.finished = True

The main loop will execute until *self.running* is set to False, which is done when someone calls the stop-method or kills the daemon with a KILL signal (TODO).
If you forget to set *self.finished = True* at the end, the daemon will never exit properly.

Connecting to a running daemon
------------------------------
After your daemon has started you can create a proxy that communicates with the daemon through a ZeroMQ-socket. This makes it possible to call methods and access variables in the daemon in almost the same way as if you had a real instance of the class. You can even connect to daemons that run on other servers by providing the hostname or IP when connecting.

To connect to a running daemon, use the get-method in malacoda.py:

    d = malacoda.get(<daemon name>:<hostname>)

You can leave out the hostname if the daemon runs on localhost.
Any keyword arguments given to the get-method is forwarded to the SSH-clients connect-method, see the documentation [here](http://docs.paramiko.org/en/latest/api/client.html#paramiko.client.SSHClient.connect) for available commands. 

Calling methods and accessing variables
---------------------------------------
When you have a proxy you can call methods and access variables on this.
A keyword argument named *timeout* can be given to all method calls, this sets the timeout of the remote execution call to this many seconds.

    d.insert_message('hello world', timeout=2)

The default timeout is None, meaning no timeout will be used.
You can call methods, access class attributes, and set class attributes just as you would with a real instance of the class:

    print d.pst_counter
    d.pst_counter = 0

Stopping a daemon
-----------------
If you have started your daemon with the argument *daemonize=True* you need to connect to the daemon in order to stop it safely.
If you have a proxy connected you can call the method *stop()*, there is also a helper function in malacoda.py named *stop* that connects to and stops the daemon with given name.

Persistant storage
------------------
All variables that starts with 'pst' are saved according to the settings of the chosen persister. The keyword argument *pst_config* that is given to init controls which persister class is used. By default this uses a scheme that saves the pst-variables to a file once a minute.
To modify this, pst_config should be a dict with the key *class_name* and value the name of a persisting class from the file *pst_storage.py*, any other key-values are used for setting up the persister class. 
When a Malacoda class is instantiated any saved pst-variables are loaded and replaces the default values in the constructor.

Testing and examples
--------------------
Basic unittests exist in the tests directory.
The above example can be found in the examples directory.

Requirements
------------
pip install setproctitle, cloud, paramiko, pyzmq

It also requires lsof for remote lookup of port.

Future improvements
-------------------
 - Better handling of timeout and automatic reconnection if connection is lost.
 - Handle received commands in separate threads to allow better concurrency.
 - Keep cache of ongoing commands to stop duplicates.
 - Lookup server so that one can find daemon on other hosts without knowing hostname.
 - Persister to S3.
 - Possible to start more than one *run*-methods.
 - Doc-strings should be visible through proxy.
 - Better unittests.
 