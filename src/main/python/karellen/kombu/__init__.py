#
#  -*- coding: utf-8 -*-
#
# (C) Copyright 2016 Karellen, Inc. (http://karellen.co/)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

PATCH_MARKER = "_KARELLEN_KOMBU_EXT_PATCHED"
TRANSPORTS = {
    'django': 'karellen.kombu.transport.django:Transport',
    'sqlalchemy': 'karellen.kombu.transport.sqlalchemy:Transport',
    'sqla': 'karellen.kombu.transport.sqlalchemy:Transport',
}


def register_transports():
    from kombu import transport

    if not hasattr(transport, PATCH_MARKER):
        transport.TRANSPORT_ALIASES.update(TRANSPORTS)

        setattr(transport, PATCH_MARKER, None)


def unregister_transports():
    from kombu import transport

    if hasattr(transport, PATCH_MARKER):
        for k in TRANSPORTS:
            del transport.TRANSPORT_ALIASES[k]

        delattr(transport, PATCH_MARKER)
