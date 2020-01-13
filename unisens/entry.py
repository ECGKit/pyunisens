# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 21:15:53 2020

@author: skjerns
"""

import os
import csv
import logging
import pandas as pd
import numpy as np
from misc import AttrDict
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element
# import unisens
#
lowercase = lambda s: s[:1].lower() + s[1:] if s else ''

def strip(string):
    """
    Strip a unisense identifier string of unnecessary elements
    such as version string {https://www.unisens.org/unisens2.0}
    this is done to remove namespace in ill-formated xml
    this function should at some point be replaced by a better way
    to deal with this weird behaviour of some unisens.xml files
    """
    if '}' in string:
        string = string.split('}')[-1]
    return string    
   
    
def validkey(key):
    """
    Check if a tag or a key is valid.
    In XML this basically means that the 
    key does not start with a number
    """
    assert isinstance(key, str), 'Key must be string'
    if key[0].isdigit():
        raise ValueError('Key cannot start with a number: {}'.format(key))
    return key

class Entry(Element):
    
    def __init__(self, folder='.', id=None, element=None):
        if element is not None:
            self.attrib = element.attrib
            self.tag  = strip(element.tag)
            self.text = element.text
            self.tail = element.tail
            for elem in element:
                self.append(elem)
            self.__dict__.update(element.attrib)
            
            self._folder = folder
            self._filename = os.path.join(self._folder, self.id)
            
            if not os.path.exists(self._filename):
                logging.error('File for {} does not exist'.format(self.id))
        elif id:
            if os.path.splitext(str(id))[-1]=='':
                logging.warning('id should be a filename, ie. .bin/.csv/...')
            self.set('id', id)
            self.tail='\n  \n  \n  \n  '
            self.text='\n'
        else:
            raise ValueError('Either existing element or id must be supplied')
            
    def __setattr__(self, name, value):
        """
        This will allow to set new attributes with .attrname = value
        while warning the user if builtin methods are overwritten
        """
        methods = dir(type(self))
        super.__setattr__(self, name, value)
        # do not overwrite if it's a builtin method
        if name not in methods and not name.startswith('_') and \
            isinstance(value, (int, float, bool, bytes)):
            self.set(name, value)

    def set(self, name, value):
        """
        XML only allows strings as entries and xml.ElementTree
        will not convert numbers to strings implicitly, 
        so this behaviour is replaced here.
        """
        name  = str(name)
        value = str(value)
        Element.set(self, name, value)
        self.__dict__.update(self.attrib)
                   
        
    def __repr__(self):
        owntype = type(self).__name__
        return "<{}({})>".format(owntype, self.id)
    
    
    def to_xml(self):
        return ET.tostring(self).decode()
    
    
    def remove_attr(self, key):
        """
        Removes a custom attribute/value of this entry.
        
        :param key: The name of the custom attribute
        """
        if key in self.attrib: 
            del self.attrib[key]
            del self.__dict__[key]
        else:
            logging.error('{} not in attrib'.format(key))
        return self

        
        
class SignalEntry(Entry):
    
    def __init__(self, folder='.', **kwargs):
        super().__init__(folder, **kwargs)
        self.tag = lowercase(type(self).__name__)
        
    def get_data(self, scaled=True):
        """
        Will try to load the binary data using numpy.
        This might not always work as endianess can't be determined
        with numpy
        
        :param scaled: Scale values using scaling factor or return raw numbers
        """
        dtypestr = self.dataType
        dtype = np.__dict__.get(dtypestr)
        data = np.fromfile(self._filename, dtype=dtype)
        if scaled:
            data = (data * float(self.lsbValue)).astype(dtype)
        return data
    
    def set_data(self, data:np.ndarray, sampleRate:int=None, lsbValue:float=1,
                 unit=None, comment=None, contentClass=None):
        """
        Set the data that is connected to this SignalEntry.
        The data will in any case be saved with Endianness LITTLE,
        as this is the default for numpy. Data will be saved using
        numpy binary data output.
        
        :param data: an numpy array or list with values
        :param sampleRate: the sample rate of this data
        :param lsbValue: the value with which this data is scaled.
                         this means that 
                         
        """
        raise NotImplementedError


class ValuesEntry(Entry):
    def __init__(self, folder='.' , **kwargs):
        super().__init__(folder, **kwargs)
        self.tag = lowercase(type(self).__name__)
        # if not hasattr(self, 'csvFileFormat'):
        #     logging.warnings('csvFileFormat information missing for {}'\
        #                      ' assuming decimal=. and sep=;'.format(self.id))
        #     self.csvFileFormat = AttrDict({'decimalSeparator':'.',
        #                                    'separator':';'}) 
        
    def get_data(self, mode:str='list'):
        """
        Will try to load the csv data using pandas.
        
        :param mode: select the return type
                     valid options: ['list', 'pandas', 'numpy']
        :returns: a list, dataframe or numpy array
        """
        separator = self.csvFileFormat.separator
        if mode in ('numpy', 'np', 'array'):
            data = np.genfromtxt(self._filename, delimiter=separator, dtype=str)
        elif mode in ('pandas', 'pd', 'dataframe'):
            data = pd.read_csv(self._filename, sep=separator,header=None,index_col=0)
        elif mode == 'list':
            dialect = csv.Dialect(csv.Dialect.excel)
            with open(self._filename, 'r') as f:
                dialect = csv.excel
                dialect.delimiter=separator
                reader = csv.reader(f, dialect=dialect)
                data = list(reader)
                data = [[x for x in d if not x==''] for d in data]
        else:
            raise ValueError('Invalid mode: {}, select from'
                             '["numpy", "pandas", "list"]'.format(mode))
        return data
    
class EventEntry(Entry):
    
    def __init__(self, folder='.', **kwargs):
        super().__init__(folder, **kwargs)
        self.tag = lowercase(type(self).__name__)
        # print(element[])
        # self[:] = element
        # self._children = element._children
        # if not 'csvFileFormat' in self.elements:
        #     logging.warnings('csvFileFormat information missing for {}'\
        #                       ' assuming decimal=. and sep=;'.format(self.id))
        #     self.csvFileFormat = AttrDict({'decimalSeparator':'.',
        #                                     'separator':';'}) 
            
    def get_data(self, mode:str='list'):
        """
        Will try to load the csv data using pandas.
        
        :param mode: select the return type
                     valid options: ['list', 'pandas', 'numpy']
        :returns: a list, dataframe or numpy array
        """
        separator = self.csvFileFormat.separator
        if mode in ('numpy', 'np', 'array'):
            data = np.genfromtxt(self._filename, delimiter=separator, dtype=str)
        elif mode in ('pandas', 'pd', 'dataframe'):
            data = pd.read_csv(self._filename, sep=separator,header=None,index_col=0)
        elif mode == 'list':
            dialect = csv.excel
            dialect.delimiter=separator
            with open(self._filename, 'r') as f:
                reader = csv.reader(f, dialect=dialect)
                data = list(reader)
                data = [[x for x in d if not x==''] for d in data]
                data = [[float(d[0])] + d[1:] for d in data]
        else:
            raise ValueError('Invalid mode: {}, select from'
                             '["numpy", "pandas", "list"]'.format(mode))
        return data


class group(Entry):
    pass

class CustomEntry(Entry):
    pass


class CustomAttribute(Element):
    def __repr__(self):
        return 'customAttribute({}:{})'.format(*self.attrib.values())

class CustomAttributes(Entry):
    def __init__(self, element=None):
        """
        """
        
        self.tag = element.tag
        self.tail = element.tail
        self.text = element.text
        attrib = AttrDict()
        for cattr in element:
            key = cattr.attrib['key']
            value = cattr.attrib['value']
            attrib[key] = value
            # self.append(cattr)
        # actually we do not have attribs in CustomAttributes,
        # so save them hidden
        self._attrib = attrib
        self.__dict__.update(attrib)
        self._update()
        
    def __setattr__(self, name, value):
        """
        This will allow to set new attributes with .attrname = value
        while warning the user if builtin methods are overwritten
        """
        print('setting attr')
        methods = dir(type(self))
        super.__setattr__(self, name, value)
        # do not overwrite if it's a builtin method
        if name not in methods and not name.startswith('_') and \
            isinstance(value, (int, float, bool, bytes)):
            print('calling set')
            self.set(name, value)


    def set(self, key, value):
        """
        dsfv
        """
        validkey(key)
        key = str(key)
        value = str(value)
        self._attrib[key] = value
        self._update()
        
    def remove(self, key):
        if key in self._attrib:
            del self._attrib[key]
            Entry.remove(self, key)
            self._update()
        else:
            Entry.remove(self, key)
    
    def _update(self):
        """
        This will reconstruct the children of this CustomAttributes
        such that they can be converted to proper XML later on.
        """
        print('here', self._attrib, list(self))
        
        for child in list(self):
            Entry.remove(self, child)
            
        for key, value in self._attrib.items():
            attrib = {'key':key, 'value':value}
            customAttribute = CustomAttribute('customAttribute', attrib=attrib)
            self.append(customAttribute)
            print(1)
        print(list(self))
        
    def __repr__(self):
        attrib = ', '.join([x for x in self._attrib])
        s = '<CustomAttributes({})>'.format(attrib)
        return s
    
class MiscEntry(Element):
    def __init__(self, name=None, element=None):
        self.attrib = element.attrib
        self.text = element.text
        self.tail = element.tail
        self.tag = lowercase(element.tag) if name is None else lowercase(name)
        for elem in list(element):
            self.append(MiscEntry(element=elem))
        self.__dict__.update(self.attrib)
        
    def __repr__(self):
        attrib = ', '.join([x for x in self.attrib])
        s = '<{}({})>'.format(self.tag,attrib)
        return s
    
class Group(Entry):
    def __init__(self, key=None, value=None, element=None):
        self.attrib = element.attrib
        self.text = element.text
        self.tail = element.tail
        self.tag = 'group'
        self.__dict__.update(self.attrib)
    
    def __repr__(self):
        attrib = ', '.join([x for x in self.attrib])
        s = '<{}({})>'.format(self.tag,attrib)
        return s
    
class Context(Entry):
    
    def __init__(self, key=None, value=None, element=None):
        self.attrib = element.attrib
        self.text = element.text
        self.tail = element.tail
        self.tag = 'context'
        self.__dict__.update(self.attrib)
    
    def __repr__(self):
        attrib = ', '.join([x for x in self.attrib])
        s = '<context({})>'.format(attrib)
        return s
    # def __init__(self, attrib:dict=None):
    #     self.__dict__.update(attrib)
