#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Copyright (c) 2002-2017 "Neo Technology,"
# Network Engine for Objects in Lund AB [http://neotechnology.com]
#
# This file is part of Neo4j.
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


from socket import create_connection

from neo4j.v1 import ConnectionPool, ServiceUnavailable, DirectConnectionErrorHandler

from test.integration.tools import IntegrationTestCase


class QuickConnection(object):

    def __init__(self, socket):
        self.socket = socket
        self.address = socket.getpeername()

    def reset(self):
        pass

    def close(self):
        self.socket.close()

    def closed(self):
        return False

    def defunct(self):
        return False


def connector(address, _):
    return QuickConnection(create_connection(address))


class ConnectionPoolTestCase(IntegrationTestCase):

    def setUp(self):
        self.pool = ConnectionPool(connector, DirectConnectionErrorHandler())

    def tearDown(self):
        self.pool.close()

    def assert_pool_size(self, address, expected_active, expected_inactive):
        try:
            connections = self.pool.connections[address]
        except KeyError:
            assert 0 == expected_active
            assert 0 == expected_inactive
        else:
            assert len([c for c in connections if c.in_use]) == expected_active
            assert len([c for c in connections if not c.in_use]) == expected_inactive

    def test_can_acquire(self):
        address = ("127.0.0.1", 7687)
        connection = self.pool.acquire_direct(address)
        assert connection.address == address
        self.assert_pool_size(address, 1, 0)

    def test_can_acquire_twice(self):
        address = ("127.0.0.1", 7687)
        connection_1 = self.pool.acquire_direct(address)
        connection_2 = self.pool.acquire_direct(address)
        assert connection_1.address == address
        assert connection_2.address == address
        assert connection_1 is not connection_2
        self.assert_pool_size(address, 2, 0)

    def test_can_acquire_two_addresses(self):
        address_1 = ("127.0.0.1", 7687)
        address_2 = ("127.0.0.1", 7474)
        connection_1 = self.pool.acquire_direct(address_1)
        connection_2 = self.pool.acquire_direct(address_2)
        assert connection_1.address == address_1
        assert connection_2.address == address_2
        self.assert_pool_size(address_1, 1, 0)
        self.assert_pool_size(address_2, 1, 0)

    def test_can_acquire_and_release(self):
        address = ("127.0.0.1", 7687)
        connection = self.pool.acquire_direct(address)
        self.assert_pool_size(address, 1, 0)
        self.pool.release(connection)
        self.assert_pool_size(address, 0, 1)

    def test_releasing_twice(self):
        address = ("127.0.0.1", 7687)
        connection = self.pool.acquire_direct(address)
        self.pool.release(connection)
        self.assert_pool_size(address, 0, 1)
        self.pool.release(connection)
        self.assert_pool_size(address, 0, 1)

    def test_cannot_acquire_after_close(self):
        with ConnectionPool(lambda a: QuickConnection(create_connection(a)), DirectConnectionErrorHandler()) as pool:
            pool.close()
            with self.assertRaises(ServiceUnavailable):
                _ = pool.acquire_direct("X")

    def test_in_use_count(self):
        address = ("127.0.0.1", 7687)
        self.assertEqual(self.pool.in_use_connection_count(address), 0)
        connection = self.pool.acquire_direct(address)
        self.assertEqual(self.pool.in_use_connection_count(address), 1)
        self.pool.release(connection)
        self.assertEqual(self.pool.in_use_connection_count(address), 0)
