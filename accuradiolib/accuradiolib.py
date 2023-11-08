#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: accuradiolib.py
#
# Copyright 2023 Costas Tyfoxylos
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
#

"""
Main code for accuradiolib.

.. _Google Python Style Guide:
   https://google.github.io/styleguide/pyguide.html

"""

import json
import logging
import requests
from dataclasses import dataclass

from sonosaudioservicelib.sonosaudioservicelib import SonosAudioService, SonosAudioChannel

from .accuradiolibexceptions import MarkerNotFound, InvalidData

__author__ = '''Costas Tyfoxylos <costas.tyf@gmail.com>'''
__docformat__ = '''google'''
__date__ = '''08-11-2023'''
__copyright__ = '''Copyright 2023, Costas Tyfoxylos'''
__credits__ = ["Costas Tyfoxylos"]
__license__ = '''MIT'''
__maintainer__ = '''Costas Tyfoxylos'''
__email__ = '''<costas.tyf@gmail.com>'''
__status__ = '''Development'''  # "Prototype", "Development", "Production".

# This is the main prefix used for logging
LOGGER_BASENAME = '''accuradiolib'''
LOGGER = logging.getLogger(LOGGER_BASENAME)
LOGGER.addHandler(logging.NullHandler())


@dataclass
class Brand:
    channels: int
    _id: dict
    canonical_url: str
    param: str
    name: str

    @property
    def oid(self):
        return self._id.get('$oid')


class Service(SonosAudioService):

    def __init__(self):
        self.url = 'https://www.accuradio.com'

    @property
    def _data(self):
        response = requests.get(self.url)
        return self._parse_configuration_from_source(response.text)

    @property
    def _brands(self):
        for brand in self._data.get('content').get('genres', {}).get('brands'):
            yield Brand(**brand)

    @staticmethod
    def _parse_configuration_from_source(text):
        start_marker = '__PRELOADED_STATE__ ='
        end_marker = '}</script>'
        start = text.find(start_marker)
        if start == -1:
            raise MarkerNotFound(f'Could not find starting marker {start_marker} in text: {text}')
        start = start + len(start_marker)
        end = text.find(end_marker, start)
        if end == -1:
            raise MarkerNotFound(f'Could not find end marker {end_marker} in text: {text}')
        # we add the last curly brace to fix the above matching.
        data = f'{text[start: end]}}}'
        try:
            data = json.loads(data)
        except ValueError:
            LOGGER.error('Unable to parse data as json.')
            raise InvalidData(data)
        return data

    @property
    def channels(self):
        for brand in self._brands:
            url = f'{self.url}/c/m/json/genre/?param={brand.param}'
            response = requests.get(url)
            for channel in response.json().get('channels'):
                yield Channel(self, channel)

    def get_channel_by_id(self, channel_id):
        """Should retrieve a channel by the provided id."""
        return next((channel for channel in self.channels if channel.id == channel_id), None)


class Channel(SonosAudioChannel):

    def __init__(self, service, data):
        self.service = service
        self._data = data

    @property
    def id(self):
        """The id of the channel."""
        return self._data.get('_id', {}).get('$oid')

    @property
    def name(self):
        """The name of the channel."""
        return self._data.get('name')

    @property
    def media_uri(self):
        """The uri of the media of the channel."""
        # this just fetches the accuradio ad...
        url = f'{self.service.url}/sweeper/json/fetch/?ucoid={self.id}'
        return requests.get(url).json().get('creative', {}).get('audio')

    @property
    def description(self):
        """The description of the channel."""
        return self._data.get('description')

    @property
    def logo(self):
        """The logo of the channel."""
        return None
