#!/bin/env python
# -*- coding: utf-8 -*-
try:
    import validators
    have_validators = True
except ImportError:
    have_validators = False

MAXCHARLENGTH = 512
INFINITY = 10**10

import re
import sys
import locale
import os
import types
import cPickle
import datetime
import threading
import time
import cStringIO
import csv
import copy
import logging
import copy_reg
import base64
import shutil
import marshal
import decimal
import struct
import urllib
import hashlib
from hashfunc import web2py_uuid
from storage import Storage

DEFAULT = lambda:0
class SQLCustomType(object):
    """
    allows defining of custom SQL types

    Example::

        decimal = SQLCustomType(
            type ='double',
            native ='integer',
            encoder =(lambda x: int(float(x) * 100)),
            decoder = (lambda x: Decimal("0.00") + Decimal(str(float(x)/100)) )
            )

        db.define_table(
            'example',
            Field('value', type=decimal)
            )

    :param type: the web2py type (default = 'string')
    :param native: the backend type
    :param encoder: how to encode the value to store it in the backend
    :param decoder: how to decode the value retrieved from the backend
    :param validator: what validators to use ( default = None, will use the
        default validator for type)
    """

    def __init__(
        self,
        type='string',
        native=None,
        encoder=None,
        decoder=None,
        validator=None,
        _class=None,
        ):

        self.type = type
        self.native = native
        self.encoder = encoder or (lambda x: x)
        self.decoder = decoder or (lambda x: x)
        self.validator = validator
        self._class = _class or type

    def startswith(self, dummy=None):
        return False

    def __getslice__(self, a=0, b=100):
        return None

    def __getitem__(self, i):
        return None

    def __str__(self):
        return self._class

def cleanup(text):
    """
    validates that the given text is clean: only contains [0-9a-zA-Z_]
    """

    if re.compile('[^0-9a-zA-Z_]').findall(text):
        raise SyntaxError, \
            'only [0-9a-zA-Z_] allowed in table and field names, received %s' \
            % text
    return text

class Field(dict):
    def __init__(
        self,
        fieldname,
        type='string',
        length=None,
        default=DEFAULT,
        requires=DEFAULT,
        widget=None,
        label=None,
        comment=None,
        writable=True,
        readable=True,
        update=None,
        represent=None,
        custom_store=None,
        custom_retrieve=None,
        ):
        self.db = None
        self.op = None
        self.first = None
        self.second = None
        self.name = fieldname = cleanup(fieldname)
        self.type = type  # 'string', 'integer'
        self.length = (length==None) and MAXCHARLENGTH or length
        if default==DEFAULT:
            self.default = update or None
        else:
            self.default = default
        self.widget = widget
        self.label = label or ' '.join(item.capitalize() for item in fieldname.split('_'))
        self.comment = comment
        self.writable = writable
        self.readable = readable
        self.update = update
        if not represent and type in ('list:integer','list:string'):
            represent=lambda x: ', '.join(str(y) for y in x or [])
        self.represent = represent
        self.isattachment = True
        self.custom_store = custom_store
        self.custom_retrieve = custom_retrieve
        if self.label == None:
            self.label = ' '.join([x.capitalize() for x in
                                  fieldname.split('_')])
        if requires is None:
            self.requires = []
        else:
            self.requires = requires

    def store(self, file, filename=None, path=None):
        if callable(self.custom_store):
            return self.custom_store(file,filename,path)
        else:
            raise Exception("you must write your store yourself")

    def retrieve(self, name, path=None):
        if callable(self.custom_retrieve):
            return self.custom_retrieve(name,path)
        else:
            return name
        # raise Exception("you must write your retrive yourself")

    def formatter(self, value):
        if value is None or not self.requires:
            return value
        if not isinstance(self.requires, (list, tuple)):
            requires = [self.requires]
        elif isinstance(self.requires, tuple):
            requires = list(self.requires)
        else:
            requires = copy.copy(self.requires)
        requires.reverse()
        for item in requires:
            if hasattr(item, 'formatter'):
                value = item.formatter(value)
        return value

    def validate(self, value):
        if not self.requires:
            return (value, None)
        requires = self.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        for validator in requires:
            (value, error) = validator(value)
            if error:
                return (value, error)
        return (value, None)

    def __str__(self):
        try:
            return '%s.%s' % (self.tablename, self.name)
        except:
            return '<no table>.%s' % self.name

    def __setattr__(self, k, v):
        dict.__setitem__(self,k,v)

    def __getattr__(self, k):
        try:
            return dict.__getitem__(self,k)
        except KeyError:
            return None

def buildform(_table_name, *field):
    form = Storage()
    form._tablename = _table_name
    for f in field:
        f._tablename = _table_name
        form[f.name] = f
    form.fields = [f.name for f in field]
    return form

class SQLCallableList(list):
    def __call__(self):
        return copy.copy(self)

class SQLALL(object):
    """
    Helper class providing a comma-separated string having all the field names
    (prefixed by table name and '.')

    normally only called from within gluon.sql
    """

    def __init__(self, table):
        self.table = table

    def __str__(self):
        return ', '.join([str(field) for field in self.table])


def sqlhtml_validators(field):
    """
    Field type validation, using web2py's validators mechanism.

    makes sure the content of a field is in line with the declared
    fieldtype
    """
    if not have_validators:
        return []
    field_type, field_length = field.type, field.length
    if isinstance(field_type, SQLCustomType):
        if hasattr(field_type, 'validator'):
            return field_type.validator
        else:
            field_type = field_type.type
    elif not isinstance(field_type,str):
        return []
    requires=[]
    def ff(r,id):
        row=r(id)
        if not row:
            return id
        elif hasattr(r, '_format') and isinstance(r._format,str):
            return r._format % row
        elif hasattr(r, '_format') and callable(r._format):
            return r._format(row)
        else:
            return id
    if field_type == 'string':
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'text':
        requires.append(validators.IS_LENGTH(2 ** 16))
    elif field_type == 'password':
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'double':
        requires.append(validators.IS_FLOAT_IN_RANGE(-1e100, 1e100))
    elif field_type == 'integer':
        requires.append(validators.IS_INT_IN_RANGE(-1e100, 1e100))
    elif field_type.startswith('decimal'):
        requires.append(validators.IS_DECIMAL_IN_RANGE(-10**10, 10**10))
    elif field_type == 'date':
        requires.append(validators.IS_DATE())
    elif field_type == 'time':
        requires.append(validators.IS_TIME())
    elif field_type == 'datetime':
        requires.append(validators.IS_DATETIME())
    elif field_type.startswith('list:'):
        def repr_list(values): return', '.join(str(v) for v in (values or []))
        field.represent = field.represent or repr_list
    return requires


class Table(dict):
    def __init__(
        self,
        tablename,
        *fields,
        **args
        ):
        self._tablename = tablename
        new_fields = []
        for field in fields:
            if isinstance(field, Field):
                new_fields.append(field)
            elif isinstance(field, Table):
                new_fields += [copy.copy(field[f]) for f in
                               field.fields if field[f].type!='id']
            else:
                raise SyntaxError, \
                    'define_table argument is not a Field: %s' % field
        fields = new_fields
        self.fields = SQLCallableList()
        self.virtualfields = []
        fields = list(fields)

        for field in fields:
            self.fields.append(field.name)
            self[field.name] = field
            field.tablename = field._tablename = tablename
            field.table = field._table = self
            field.length = field.length
            if field.requires == DEFAULT:
                field.requires = sqlhtml_validators(field)
        self.ALL = SQLALL(self)


    def __getitem__(self, key):
        if not key:
            return None
        return dict.__getitem__(self, str(key))


    def __setitem__(self, key, value):
        if isinstance(key, dict) and isinstance(value, dict):
            """ option for keyed table """
            if set(key.keys()) == set(self._primarykey):
                value = self._filter_fields(value)
                kv = {}
                kv.update(value)
                kv.update(key)
            else:
                raise SyntaxError,\
                    'key must have all fields from primary key: %s'%\
                    (self._primarykey)
        elif str(key).isdigit():
            if key == 0:
                self.insert(**self._filter_fields(value))
            elif not self._db(self.id == key)\
                    .update(**self._filter_fields(value)):
                raise SyntaxError, 'No such record: %s' % key
        else:
            if isinstance(key, dict):
                raise SyntaxError,\
                    'value must be a dictionary: %s' % value
            dict.__setitem__(self, str(key), value)

    def __delitem__(self, key):
        if isinstance(key, dict):
            query = self._build_query(key)
            if not self._db(query).delete():
                raise SyntaxError, 'No such record: %s' % key
        elif not str(key).isdigit() or not self._db(self.id == key).delete():
            raise SyntaxError, 'No such record: %s' % key

    def __getattr__(self, key):
        return dict.__getitem__(self,key)

    def __setattr__(self, key, value):
        if key in self:
            raise SyntaxError, 'Object exists and cannot be redefined: %s' % key
        dict.__setitem__(self,key,value)

    def __iter__(self):
        for fieldname in self.fields:
            yield self[fieldname]

    def __repr__(self):
        return '<Table ' + dict.__repr__(self) + '>'

    def __str__(self):
        if self.get('_ot', None):
            return '%s AS %s' % (self._ot, self._tablename)
        return self._tablename

