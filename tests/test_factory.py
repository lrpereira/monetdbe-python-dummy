# bala
# -*- coding: iso-8859-1 -*-
# monetdbe/test/test_factory.py: tests for the various factories in pymonetdbe
#
# Copyright (C) 2005-2007 Gerhard H�ring <gh@ghaering.de>
#
# This file is part of pymonetdbe.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

import unittest
from monetdbe.connection import Connection
from monetdbe.cursors import Cursor  # type: ignore[attr-defined]
from monetdbe.row import Row
from monetdbe import connect
from collections.abc import Sequence

from tests.util import get_cached_connection, flush_cached_connection


class MyConnection(Connection):
    def __init__(self, *args, **kwargs):
        Connection.__init__(self, *args, **kwargs)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class MyCursor(Cursor):
    def __init__(self, *args, **kwargs):
        Cursor.__init__(self, *args, **kwargs)
        self.row_factory = dict_factory


class ConnectionFactoryTests(unittest.TestCase):
    def setUp(self):
        self.con = connect(":memory:", factory=MyConnection)

    def tearDown(self):
        self.con.close()

    def test_IsInstance(self):
        self.assertIsInstance(self.con, MyConnection)


class CursorFactoryTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        flush_cached_connection()

    def setUp(self):
        self.con = get_cached_connection()

    def test_IsInstance(self):
        cur = self.con.cursor()
        self.assertIsInstance(cur, Cursor)
        cur = self.con.cursor(MyCursor)
        self.assertIsInstance(cur, MyCursor)
        cur = self.con.cursor(factory=lambda con: MyCursor(con))
        self.assertIsInstance(cur, MyCursor)

    def test_InvalidFactory(self):

        # note: disabled this test, since I think None is a good default argument to indicate you don't want a factory.
        # not a callable at all
        # self.assertRaises(TypeError, self.con.cursor, None)

        # invalid callable with not exact one argument
        self.assertRaises(TypeError, self.con.cursor, lambda: None)
        # invalid callable returning non-cursor
        self.assertRaises(TypeError, self.con.cursor, lambda con: None)


class RowFactoryTestsBackwardsCompat(unittest.TestCase):
    def setUp(self):
        self.con = connect(":memory:")

    def test_IsProducedByFactory(self):
        cur = self.con.cursor(factory=MyCursor)
        cur.execute("select 4+5 as foo")
        row = cur.fetchone()
        self.assertIsInstance(row, dict)
        cur.close()

    def tearDown(self):
        self.con.close()


class RowFactoryTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        flush_cached_connection()

    def setUp(self):
        self.con = get_cached_connection()

    def test_CustomFactory(self):
        self.con.row_factory = lambda cur, row: list(row)
        row = self.con.execute("select 1, 2").fetchone()
        self.assertIsInstance(row, list)

    def test_monetdbeRowIndex(self):
        self.con.row_factory = Row
        row = self.con.execute("select 1 as a_1, 2 as b").fetchone()
        self.assertIsInstance(row, Row)

        self.assertEqual(row["a_1"], 1, "by name: wrong result for column 'a_1'")
        self.assertEqual(row["b"], 2, "by name: wrong result for column 'b'")

        # - skip, we are case sensitive
        # self.assertEqual(row["A_1"], 1, "by name: wrong result for column 'A_1'")
        # self.assertEqual(row["B"], 2, "by name: wrong result for column 'B'")

        self.assertEqual(row[0], 1, "by index: wrong result for column 0")
        self.assertEqual(row[1], 2, "by index: wrong result for column 1")
        self.assertEqual(row[-1], 2, "by index: wrong result for column -1")
        self.assertEqual(row[-2], 1, "by index: wrong result for column -2")

        with self.assertRaises(IndexError):
            row['c']
        with self.assertRaises(IndexError):
            row['a_\x11']
        with self.assertRaises(IndexError):
            row['a\x7f1']
        with self.assertRaises(IndexError):
            row[2]
        with self.assertRaises(IndexError):
            row[-3]
        with self.assertRaises(IndexError):
            row[2 ** 1000]

    @unittest.skip("issue #99")
    def test_monetdbeRowIndexUnicode(self):
        self.con.row_factory = Row
        row = self.con.execute("select 1 as \xff").fetchone()
        self.assertEqual(row["\xff"], 1)
        with self.assertRaises(IndexError):
            row['\u0178']
        with self.assertRaises(IndexError):
            row['\xdf']

    def test_monetdbeRowSlice(self):
        # A Row can be sliced like a list.
        self.con.row_factory = Row
        row = self.con.execute("select 1, 2, 3, 4").fetchone()
        self.assertEqual(row[0:0], ())
        self.assertEqual(row[0:1], (1,))
        self.assertEqual(row[1:3], (2, 3))
        self.assertEqual(row[3:1], ())
        # Explicit bounds are optional.
        self.assertEqual(row[1:], (2, 3, 4))
        self.assertEqual(row[:3], (1, 2, 3))
        # Slices can use negative indices.
        self.assertEqual(row[-2:-1], (3,))
        self.assertEqual(row[-2:], (3, 4))
        # Slicing supports steps.
        self.assertEqual(row[0:4:2], (1, 3))
        self.assertEqual(row[3:0:-2], (4, 2))

    def test_monetdbeRowIter(self):
        """Checks if the row object is iterable"""
        self.con.row_factory = Row
        row = self.con.execute("select 1 as a, 2 as b").fetchone()
        for col in row:
            pass

    def test_monetdbeRowAsTuple(self):
        """Checks if the row object can be converted to a tuple"""
        self.con.row_factory = Row
        row = self.con.execute("select 1 as a, 2 as b").fetchone()
        t = tuple(row)
        self.assertEqual(t, (row['a'], row['b']))

    def test_monetdbeRowAsDict(self):
        """Checks if the row object can be correctly converted to a dictionary"""
        self.con.row_factory = Row
        row = self.con.execute("select 1 as a, 2 as b").fetchone()
        d = dict(row)
        self.assertEqual(d["a"], row["a"])
        self.assertEqual(d["b"], row["b"])

    def test_monetdbeRowHashCmp(self):
        """Checks if the row object compares and hashes correctly"""
        self.con.row_factory = Row
        row_1 = self.con.execute("select 1 as a, 2 as b").fetchone()
        row_2 = self.con.execute("select 1 as a, 2 as b").fetchone()
        row_3 = self.con.execute("select 1 as a, 3 as b").fetchone()
        row_4 = self.con.execute("select 1 as b, 2 as a").fetchone()
        row_5 = self.con.execute("select 2 as b, 1 as a").fetchone()

        self.assertTrue(row_1 == row_1)
        self.assertTrue(row_1 == row_2)
        self.assertFalse(row_1 == row_3)
        self.assertFalse(row_1 == row_4)
        self.assertFalse(row_1 == row_5)
        self.assertFalse(row_1 == object())

        self.assertFalse(row_1 != row_1)
        self.assertFalse(row_1 != row_2)
        self.assertTrue(row_1 != row_3)
        self.assertTrue(row_1 != row_4)
        self.assertTrue(row_1 != row_5)
        self.assertTrue(row_1 != object())

        with self.assertRaises(TypeError):
            row_1 > row_2
        with self.assertRaises(TypeError):
            row_1 < row_2
        with self.assertRaises(TypeError):
            row_1 >= row_2
        with self.assertRaises(TypeError):
            row_1 <= row_2

        self.assertEqual(hash(row_1), hash(row_2))

    def test_monetdbeRowAsSequence(self):
        """ Checks if the row object can act like a sequence """
        self.con.row_factory = Row
        row = self.con.execute("select 1 as a, 2 as b").fetchone()

        as_tuple = tuple(row)
        self.assertEqual(list(reversed(row)), list(reversed(as_tuple)))
        self.assertIsInstance(row, Sequence)

    def test_FakeCursorClass(self):
        # Issue #24257: Incorrect use of PyObject_IsInstance() caused
        # segmentation fault.
        # Issue #27861: Also applies for cursor factory.
        class FakeCursor(str):
            __class__ = Cursor

        self.con.row_factory = Row
        self.assertRaises(TypeError, self.con.cursor, FakeCursor)
        self.assertRaises(TypeError, Row, FakeCursor(), ())


class TextFactoryTests(unittest.TestCase):
    def setUp(self):
        self.con = connect(":memory:")

    def test_Unicode(self):
        austria = "�sterreich"
        row = self.con.execute("select cast(? as varchar(100))", (austria,)).fetchone()
        self.assertEqual(type(row[0]), str, "type of row[0] must be unicode")

    def test_String(self):
        self.con.text_factory = lambda x: bytes(x.encode('utf-8'))
        austria = "�sterreich"
        row = self.con.execute("select cast(? as varchar(100))", (austria,)).fetchone()
        self.assertEqual(type(row[0]), bytes, "type of row[0] must be bytes")
        self.assertEqual(row[0], austria.encode("utf-8"), "column must equal original data in UTF-8")

    def test_Custom(self):
        self.con.text_factory = lambda x: str(x) + str(x)
        austria = "�sterreich"
        # todo/note (gijs): added (? as varchar(20)) since monetdbe can't infer the type from the query
        row = self.con.execute("select cast(? as varchar(100))", (austria,)).fetchone()
        self.assertEqual(type(row[0]), str, "type of row[0] must be unicode")
        self.assertTrue(row[0].strip().endswith("reich"), "column must contain original data")

    def tearDown(self):
        self.con.close()


@unittest.skip("We don't support strings with zero byte (yet)")
class TextFactoryTestsWithEmbeddedZeroBytes(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        flush_cached_connection()

    @classmethod
    def setUpClass(cls):
        con = get_cached_connection()
        with con.cursor() as cur:
            cur.execute("create table test (value text)")
            cur.execute("insert into test (value) values (?)", ("a\x00b",))

    def setUp(self):
        self.con = get_cached_connection()

    def test_String(self):
        # text_factory defaults to str
        row = self.con.execute("select value from test").fetchone()
        self.assertIs(type(row[0]), str)
        self.assertEqual(row[0], "a\x00b")

    def test_Bytes(self):
        self.con.text_factory = bytes
        row = self.con.execute("select value from test").fetchone()
        self.assertIs(type(row[0]), bytes)
        self.assertEqual(row[0], b"a\x00b")

    def test_Bytearray(self):
        self.con.text_factory = bytearray
        row = self.con.execute("select value from test").fetchone()
        self.assertIs(type(row[0]), bytearray)
        self.assertEqual(row[0], b"a\x00b")

    def test_Custom(self):
        # A custom factory should receive a bytes argument
        self.con.text_factory = lambda x: x
        row = self.con.execute("select value from test").fetchone()
        self.assertIs(type(row[0]), bytes)
        self.assertEqual(row[0], b"a\x00b")

    def tearDown(self):
        self.con.close()


if __name__ == "__main__":
    unittest.main()
