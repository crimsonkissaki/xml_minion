"""
Classes/Data based on native Python structures
"""

# Standard Library
import traceback
from typing import Union

# Third Party
from lxml import etree

# Local

'''
Quick reference for type hinting - these show up as the `typing` class
    in PyCharm's documentation popup window, good for brevity and legibility. 
'Straddling code' annotations (# type: (...) -> ...) will replace the
    shorter name of the type with the assigned type, e.g.
    # type: (StrOrList) -> StrOrList
    will show in the tooltip as
    # type: (Union[str, list]) -> Union[str, list]
Unfortunately, it does not seem reStructuredText will do the same in :param
    doc block annotations, so we have to go with the PyCharm recommended syntax
    of `:param str | list foo:`
'''
StrOrList = Union[str, list]  # type: Union[str, list]
StrOrEtree = Union[str, etree._ElementTree, etree._Element]


class AttributeDict(dict):
    """
    Dictionary subclass enabling attribute lookup/assignment of keys/values
    like an object or the normal dict['key'] method.

    For example::
        >>> m = AttributeDict({'foo': 'bar'})
        >>> m.foo
        'bar'
        >>> m.foo = 'not bar'
        >>> m['foo']
        'not bar'
    """
    def __init__(self, *args, **kwargs):
        """
        Force all values to go through ``__setattr__``
        :param list args:
        :param dict kwargs:
        """
        self.update(*args, **kwargs)

    def __getitem__(self, key):
        """
        Called during [] access
        :param str key:
        """
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        """
        Called during [] access
        :param str key:
        """
        setattr(self, key, value)

    def __getattribute__(self, key):
        try:
            return object.__getattribute__(self, key)
        except Exception:
            pass

        try:
            return self[key]
        except KeyError as ex:
            raise AttributeError(ex.message)

    def __setattr__(self, key, value):
        try:
            # lazy-load conversion of sub-dicts
            if isinstance(value, dict) and not isinstance(value, AttributeDict):
                value = AttributeDict(value)
            super(AttributeDict, self).update({key: value})
        except Exception as ex:
            traceback.print_exc()
            print '\n\n'
            print ex
            print '\n\n'

    def copy(self):
        # type: () -> AttributeDict
        """
        Creates & returns a copy of the AttributeDict

        :rtype: AttributeDict
        """
        return AttributeDict(dict(self))
