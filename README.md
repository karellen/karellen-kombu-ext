# Karellen Kombu extensions

[![Gitter chat](https://badges.gitter.im/karellen/gitter.svg)](https://gitter.im/karellen/lobby)

## About

This project contains [Karellen](https://www.karellen.co/karellen/) [Kombu](https://github.com/celery/kombu)
broker extensions.

In June 2016 Celery team has removed support for a variety of auxilliary brokers from
Kombu project citing the lack of funding. While in-memory broker still exists for testing,
this removal made it harder to develop standalone pure-Python applications utilizing Celery and Kombu.

This project recovered the brokers for
[Django](https://github.com/celery/kombu/commit/65f982ccf31b86157c39a8feb42081410b83abe2) and
[SQLAlchemy](https://github.com/celery/kombu/commit/1cd4e07f9ebb2fdbde0f86054e963f6bbd17e698).

## Transport Comparison

| Client | Type | Direct | Topic | Fanout | Priority | TTL |
| --- | --- | --- | --- | --- | --- | --- |
| django | Virtual | Yes  | Yes * | No | No | No |
| sqlalchemy | Virtual | Yes | Yes * | No | No | No |

\* Declarations only kept in memory, so exchanges/queues must be declared by all clients that needs them.

### Documentation

Standard Kombu documentation applies and is using Sphinx. The latest documentation can be found
[here](https://kombu.readthedocs.io/).

### Quick overview
```python
from kombu import Connection
from karellen.kombu import register_transports

register_transports()

conn = Connection('sqlalchemy+sqlite:///:memory:')
conn.connect()
```

## Installation

Firstly, you need to install Kombu.

### Installing Kombu
You can install Kombu either via the Python Package Index (PyPI) or from
source.

To install using pip:
```bash
$ pip install kombu
```

To install using easy_install:
```bash
$ easy_install kombu
```

If you have downloaded a source tarball you can install it by doing the
following:
```bash
$ python setup.py build
# python setup.py install # as root
```

Secondly, you need to install Karellen Kombu extension.

### Installing Karellen Kombu Extensions

```bash
$ pip install karellen-kombu-ext
$ pip install --pre karellen-kombu-ext      # if you're looking for the latest dev version
$ pip install django        # if using Django
$ pip install sqlalchemy    # if using SQL Alchemy
```

## Getting Help

You can ask for help on Gitter or by filing an issue.


## Bug tracker

If you have any suggestions, bug reports or annoyances please report
them to our [Issue Tracker](http://github.com/karellen/karellen-kombu-ext/issues/)

## Contributing

Development of Karellen Kombu Extensions happens at [Github](http://github.com/karellen/karellen-kombu-ext/)

You are highly encouraged to participate in the development. If you
don't like Github (for some reason) you're welcome to send regular
patches.

## License

This software is licensed under the New BSD License in part that is inherited from Kombu and Apache 2.0 
as developed by Karellen. See the LICENSE.bsd3 and LICENSE.apache files respectively in the top distribution directory 
for the full license text.

