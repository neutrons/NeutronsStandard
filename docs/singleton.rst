=============================
Singleton Decorator Pattern
=============================

Ensures only one instance of a decorated class exists throughout application lifecycle.

Quick Reference
===============

.. code-block:: python

    from neutrons_standard.decorators.singleton import Singleton, reset_singletons

    @Singleton
    class MyService:
        def __init__(self):
            self.state = {}

    # All references point to same instance
    s1 = MyService()
    s2 = MyService()
    assert s1 is s2  # True

    # Testing: reset before each test
    MyService._reset_singleton()                 # Reset one singleton
    reset_singletons()                           # Reset all singletons
    reset_singletons(fully_unwrap=True)          # Remove decorator behavior

Basic Usage
-----------

.. code-block:: python

    @Singleton
    class DatabaseConnection:
        def __init__(self):
            self.connection = self._connect()

        def _connect(self):
            return "Connected"

    db1 = DatabaseConnection()
    db2 = DatabaseConnection()

    assert db1 is db2  # Same object
    assert db1 is not DatabaseConnection()  # Never creates new instances

Key Behaviors
=============

Single Instance
---------------

Only one object created, all calls reuse it:

.. code-block:: python

    @Singleton
    class Logger:
        def __init__(self):
            print("Initialized")

    Logger()  # Prints "Initialized"
    Logger()  # No print - reuses existing
    Logger()  # No print - reuses existing

Initialization Guard
--------------------

``__init__`` runs only on first instantiation, skipped on subsequent calls:

.. code-block:: python

    @Singleton
    class Counter:
        def __init__(self):
            self.count = 0

    c1 = Counter()
    c1.count = 5

    c2 = Counter()  # __init__ not called
    c2.count        # 5, not 0 - same instance

Reset and Testing
-----------------

Reset individual singleton (allows re-initialization):

.. code-block:: python

    MyClass._reset_singleton()              # Next call creates new instance
    MyClass._reset_singleton(fully_unwrap=True)  # Remove Singleton behavior

Reset all singletons:

.. code-block:: python

    from neutrons_standard.decorators.singleton import reset_singletons

    reset_singletons()                      # Reset all
    reset_singletons(fully_unwrap=True)     # Fully unwrap all

Examples
========

Pytest Fixture
--------------

.. code-block:: python

    import pytest
    from neutrons_standard.decorators.singleton import reset_singletons

    @pytest.fixture(autouse=True)
    def reset_all_singletons():
        """Fresh instance for each test."""
        reset_singletons()
        yield
        reset_singletons()

    def test_one():
        obj1 = MyClass()
        obj1.value = "test1"

    def test_two():
        obj2 = MyClass()
        assert obj2.value != "test1"  # Fresh instance

Selective Reset
---------------

.. code-block:: python

    @pytest.fixture
    def fresh_database():
        """Fresh database instance."""
        DatabaseConnection._reset_singleton()
        db = DatabaseConnection()
        yield db
        DatabaseConnection._reset_singleton()

    def test_with_fresh_db(fresh_database):
        # fresh_database is guaranteed new instance
        pass

Use Cases
=========

Shared Resource Pools
---------------------

.. code-block:: python

    @Singleton
    class ConnectionPool:
        def __init__(self):
            self.connections = self._create_pool(10)

        def get_connection(self):
            return self.connections.pop()

    # Entire app shares same pool
    pool = ConnectionPool()

Logging and Monitoring
----------------------

.. code-block:: python

    @Singleton
    class ApplicationLogger:
        def __init__(self):
            self.messages = []

        def log(self, msg):
            self.messages.append(msg)

    # All modules log to same instance
    logger = ApplicationLogger()

State Management
----------------

.. code-block:: python

    @Singleton
    class SessionManager:
        def __init__(self):
            self.sessions = {}
            self.current_user = None

        def set_user(self, user):
            self.current_user = user

    # Application-wide state
    mgr = SessionManager()

Configuration Objects
---------------------

.. code-block:: python

    from neutrons_standard import Config  # Already a Singleton

    # Config is single instance across app
    cfg = Config
    cfg.reload()
    host = cfg["database.host"]

Thread Safety
=============

Not thread-safe by default. For multi-threaded use, add locking:

.. code-block:: python

    import threading

    @Singleton
    class ThreadSafeResource:
        def __init__(self):
            self.lock = threading.Lock()
            self.data = []

        def append(self, value):
            with self.lock:
                self.data.append(value)

Common Patterns
===============

Lazy Initialization
-------------------

.. code-block:: python

    @Singleton
    class ExpensiveResource:
        def __init__(self):
            self.resource = None

        def get_resource(self):
            if self.resource is None:
                self.resource = self._load()
            return self.resource

Service Factory
---------------

.. code-block:: python

    @Singleton
    class ServiceFactory:
        def __init__(self):
            self.services = {}

        def register(self, name, service):
            self.services[name] = service

        def get(self, name):
            return self.services.get(name)

Pitfalls
========

State Pollution Between Tests
-----------------------------

Always reset singletons in test fixtures to prevent state leakage between tests.

Over-Use
--------

Too many singletons make code harder to test and reason about. Use when truly needed for application-wide shared resources.

Mutable Class Variables
-----------------------

.. code-block:: python

    # Bad - shared mutable
    @Singleton
    class BadClass:
        items = []  # Shared across all

    # Good - instance variable
    @Singleton
    class GoodClass:
        def __init__(self):
            self.items = []
