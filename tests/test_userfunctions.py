# -*- coding: iso-8859-1 -*-
# monetdbe/test/userfunctions.py: tests for user-defined functions and
#                                  aggregates.
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
import unittest.mock

import monetdbe as monetdbe


def func_returntext():
    return "foo"


def func_returnunicode():
    return "bar"


def func_returnint():
    return 42


def func_returnfloat():
    return 3.14


def func_returnnull():
    return None


def func_returnblob():
    return b"blob"


def func_returnlonglong():
    return 1 << 31


def func_raiseexception():
    5 / 0


def func_isstring(v):
    return type(v) is str


def func_isint(v):
    return type(v) is int


def func_isfloat(v):
    return type(v) is float


def func_isnone(v):
    return isinstance(v, type(None))


def func_isblob(v):
    return isinstance(v, (bytes, memoryview))


def func_islonglong(v):
    return isinstance(v, int) and v >= 1 << 31


def func(*args):
    return len(args)


class AggrNoStep:
    def __init__(self):
        pass

    def finalize(self):
        return 1


class AggrNoFinalize:
    def __init__(self):
        pass

    def step(self, x):
        pass


class AggrExceptionInInit:
    def __init__(self):
        5 / 0

    def step(self, x):
        pass

    def finalize(self):
        pass


class AggrExceptionInStep:
    def __init__(self):
        pass

    def step(self, x):
        5 / 0

    def finalize(self):
        return 42


class AggrExceptionInFinalize:
    def __init__(self):
        pass

    def step(self, x):
        pass

    def finalize(self):
        5 / 0


class AggrCheckType:
    def __init__(self):
        self.val = None

    def step(self, whichType, val):
        theType = {"str": str, "int": int, "float": float, "None": type(None),
                   "blob": bytes}
        self.val = int(theType[whichType] is type(val))

    def finalize(self):
        return self.val


class AggrCheckTypes:
    def __init__(self):
        self.val = 0

    def step(self, whichType, *vals):
        theType = {"str": str, "int": int, "float": float, "None": type(None),
                   "blob": bytes}
        for val in vals:
            self.val += int(theType[whichType] is type(val))

    def finalize(self):
        return self.val


class AggrSum:
    def __init__(self):
        self.val = 0.0

    def step(self, val):
        self.val += val

    def finalize(self):
        return self.val


@unittest.skip("user functions not yet supported (see issue #20)")
class FunctionTests(unittest.TestCase):
    def setUp(self):
        self.con = monetdbe.connect(":memory:")

        self.con.create_function("returntext", 0, func_returntext)
        self.con.create_function("returnunicode", 0, func_returnunicode)
        self.con.create_function("returnint", 0, func_returnint)
        self.con.create_function("returnfloat", 0, func_returnfloat)
        self.con.create_function("returnnull", 0, func_returnnull)
        self.con.create_function("returnblob", 0, func_returnblob)
        self.con.create_function("returnlonglong", 0, func_returnlonglong)
        self.con.create_function("raiseexception", 0, func_raiseexception)

        self.con.create_function("isstring", 1, func_isstring)
        self.con.create_function("isint", 1, func_isint)
        self.con.create_function("isfloat", 1, func_isfloat)
        self.con.create_function("isnone", 1, func_isnone)
        self.con.create_function("isblob", 1, func_isblob)
        self.con.create_function("islonglong", 1, func_islonglong)
        self.con.create_function("spam", -1, func)

    def tearDown(self):
        self.con.close()

    def test_FuncErrorOnCreate(self):
        with self.assertRaises(monetdbe.OperationalError):
            self.con.create_function("bla", -100, lambda x: 2 * x)

    def test_FuncRefCount(self):
        def getfunc():
            def f():
                return 1

            return f

        f = getfunc()
        globals()["foo"] = f
        # self.con.create_function("reftest", 0, getfunc())
        self.con.create_function("reftest", 0, f)
        cur = self.con.cursor()
        cur.execute("select reftest()")

    def test_FuncReturnText(self):
        cur = self.con.cursor()
        cur.execute("select returntext()")
        val = cur.fetchone()[0]
        self.assertEqual(type(val), str)
        self.assertEqual(val, "foo")

    def test_FuncReturnUnicode(self):
        cur = self.con.cursor()
        cur.execute("select returnunicode()")
        val = cur.fetchone()[0]
        self.assertEqual(type(val), str)
        self.assertEqual(val, "bar")

    def test_FuncReturnInt(self):
        cur = self.con.cursor()
        cur.execute("select returnint()")
        val = cur.fetchone()[0]
        self.assertEqual(type(val), int)
        self.assertEqual(val, 42)

    def test_FuncReturnFloat(self):
        cur = self.con.cursor()
        cur.execute("select returnfloat()")
        val = cur.fetchone()[0]
        self.assertEqual(type(val), float)
        if val < 3.139 or val > 3.141:
            self.fail("wrong value")

    def test_FuncReturnNull(self):
        cur = self.con.cursor()
        cur.execute("select returnnull()")
        val = cur.fetchone()[0]
        self.assertEqual(type(val), type(None))
        self.assertEqual(val, None)

    def test_FuncReturnBlob(self):
        cur = self.con.cursor()
        cur.execute("select returnblob()")
        val = cur.fetchone()[0]
        self.assertEqual(type(val), bytes)
        self.assertEqual(val, b"blob")

    def test_FuncReturnLongLong(self):
        cur = self.con.cursor()
        cur.execute("select returnlonglong()")
        val = cur.fetchone()[0]
        self.assertEqual(val, 1 << 31)

    def test_FuncException(self):
        cur = self.con.cursor()
        with self.assertRaises(monetdbe.OperationalError) as cm:
            cur.execute("select raiseexception()")
            cur.fetchone()
        self.assertEqual(str(cm.exception), 'user-defined function raised exception')

    def test_ParamString(self):
        cur = self.con.cursor()
        cur.execute("select isstring(?)", ("foo",))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_ParamInt(self):
        cur = self.con.cursor()
        cur.execute("select isint(?)", (42,))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_ParamFloat(self):
        cur = self.con.cursor()
        cur.execute("select isfloat(?)", (3.14,))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_ParamNone(self):
        cur = self.con.cursor()
        cur.execute("select isnone(?)", (None,))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_ParamBlob(self):
        cur = self.con.cursor()
        cur.execute("select isblob(?)", (memoryview(b"blob"),))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_ParamLongLong(self):
        cur = self.con.cursor()
        cur.execute("select islonglong(?)", (1 << 42,))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_AnyArguments(self):
        cur = self.con.cursor()
        cur.execute("select spam(?, ?)", (1, 2))
        val = cur.fetchone()[0]
        self.assertEqual(val, 2)

    def test_FuncNonDeterministic(self):
        mock = unittest.mock.Mock(return_value=None)
        self.con.create_function("deterministic", 0, mock, deterministic=False)
        self.con.execute("select deterministic() = deterministic()")
        self.assertEqual(mock.call_count, 2)

    def test_FuncDeterministicNotSupported(self):
        with self.assertRaises(monetdbe.NotSupportedError):
            self.con.create_function("deterministic", 0, int, deterministic=True)

    def test_FuncDeterministicKeywordOnly(self):
        with self.assertRaises(TypeError):
            self.con.create_function("deterministic", 0, int, True)


@unittest.skip("user functions not yet supported (see issue #20)")
class AggregateTests(unittest.TestCase):
    def setUp(self):
        self.con = monetdbe.connect(":memory:")
        cur = self.con.cursor()
        cur.execute("""
            create table test(
                t text,
                i integer,
                f float,
                n text,
                b blob
                )
            """)
        cur.execute("insert into test(t, i, f, n, b) values (?, ?, ?, ?, ?)",
                    ("foo", 5, 3.14, None, memoryview(b"blob"),))

        self.con.create_aggregate("nostep", 1, AggrNoStep)
        self.con.create_aggregate("nofinalize", 1, AggrNoFinalize)
        self.con.create_aggregate("excInit", 1, AggrExceptionInInit)
        self.con.create_aggregate("excStep", 1, AggrExceptionInStep)
        self.con.create_aggregate("excFinalize", 1, AggrExceptionInFinalize)
        self.con.create_aggregate("checkType", 2, AggrCheckType)
        self.con.create_aggregate("checkTypes", -1, AggrCheckTypes)
        self.con.create_aggregate("mysum", 1, AggrSum)

    def tearDown(self):
        # self.cur.close()
        # self.con.close()
        pass

    def test_AggrErrorOnCreate(self):
        with self.assertRaises(monetdbe.OperationalError):
            self.con.create_function("bla", -100, AggrSum)

    def test_AggrNoStep(self):
        cur = self.con.cursor()
        with self.assertRaises(AttributeError) as cm:
            cur.execute("select nostep(t) from test")
        self.assertEqual(str(cm.exception), "'AggrNoStep' object has no attribute 'step'")

    def test_AggrNoFinalize(self):
        cur = self.con.cursor()
        with self.assertRaises(monetdbe.OperationalError) as cm:
            cur.execute("select nofinalize(t) from test")
            val = cur.fetchone()[0]
        self.assertEqual(str(cm.exception), "user-defined aggregate's 'finalize' method raised error")

    def test_AggrExceptionInInit(self):
        cur = self.con.cursor()
        with self.assertRaises(monetdbe.OperationalError) as cm:
            cur.execute("select excInit(t) from test")
            val = cur.fetchone()[0]
        self.assertEqual(str(cm.exception), "user-defined aggregate's '__init__' method raised error")

    def test_AggrExceptionInStep(self):
        cur = self.con.cursor()
        with self.assertRaises(monetdbe.OperationalError) as cm:
            cur.execute("select excStep(t) from test")
            val = cur.fetchone()[0]
        self.assertEqual(str(cm.exception), "user-defined aggregate's 'step' method raised error")

    def test_AggrExceptionInFinalize(self):
        cur = self.con.cursor()
        with self.assertRaises(monetdbe.OperationalError) as cm:
            cur.execute("select excFinalize(t) from test")
            val = cur.fetchone()[0]
        self.assertEqual(str(cm.exception), "user-defined aggregate's 'finalize' method raised error")

    def test_AggrCheckParamStr(self):
        cur = self.con.cursor()
        cur.execute("select checkType('str', ?)", ("foo",))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_AggrCheckParamInt(self):
        cur = self.con.cursor()
        cur.execute("select checkType('int', ?)", (42,))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_AggrCheckParamsInt(self):
        cur = self.con.cursor()
        cur.execute("select checkTypes('int', ?, ?)", (42, 24))
        val = cur.fetchone()[0]
        self.assertEqual(val, 2)

    def test_AggrCheckParamFloat(self):
        cur = self.con.cursor()
        cur.execute("select checkType('float', ?)", (3.14,))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_AggrCheckParamNone(self):
        cur = self.con.cursor()
        cur.execute("select checkType('None', ?)", (None,))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_AggrCheckParamBlob(self):
        cur = self.con.cursor()
        cur.execute("select checkType('blob', ?)", (memoryview(b"blob"),))
        val = cur.fetchone()[0]
        self.assertEqual(val, 1)

    def test_AggrCheckAggrSum(self):
        cur = self.con.cursor()
        cur.execute("delete from test")
        cur.executemany("insert into test(i) values (?)", [(10,), (20,), (30,)])
        cur.execute("select mysum(i) from test")
        val = cur.fetchone()[0]
        self.assertEqual(val, 60)


@unittest.skip("user functions not yet supported (see issue #20)")
class AuthorizerTests(unittest.TestCase):
    @staticmethod
    def authorizer_cb(action, arg1, arg2, dbname, source):
        if action != monetdbe.monetdbe_SELECT:
            return monetdbe.monetdbe_DENY
        if arg2 == 'c2' or arg1 == 't2':
            return monetdbe.monetdbe_DENY
        return monetdbe.monetdbe_OK

    def setUp(self):
        self.con = monetdbe.connect(":memory:")
        self.con.executescript("""
            create table t1 (c1, c2);
            create table t2 (c1, c2);
            insert into t1 (c1, c2) values (1, 2);
            insert into t2 (c1, c2) values (4, 5);
            """)

        # For our security test:
        self.con.execute("select c2 from t2")

        self.con.set_authorizer(self.authorizer_cb)

    def tearDown(self):
        pass

    def test_table_access(self):
        with self.assertRaises(monetdbe.DatabaseError) as cm:
            self.con.execute("select * from t2")
        self.assertIn('prohibited', str(cm.exception))

    def test_column_access(self):
        with self.assertRaises(monetdbe.DatabaseError) as cm:
            self.con.execute("select c2 from t1")
        self.assertIn('prohibited', str(cm.exception))


@unittest.skip("user functions not yet supported (see issue #20)")
class AuthorizerRaiseExceptionTests(AuthorizerTests):
    @staticmethod
    def authorizer_cb(action, arg1, arg2, dbname, source):
        if action != monetdbe.monetdbe_SELECT:
            raise ValueError
        if arg2 == 'c2' or arg1 == 't2':
            raise ValueError
        return monetdbe.monetdbe_OK


@unittest.skip("user functions not yet supported (see issue #20)")
class AuthorizerIllegalTypeTests(AuthorizerTests):
    @staticmethod
    def authorizer_cb(action, arg1, arg2, dbname, source):
        if action != monetdbe.monetdbe_SELECT:
            return 0.0
        if arg2 == 'c2' or arg1 == 't2':
            return 0.0
        return monetdbe.monetdbe_OK


@unittest.skip("user functions not yet supported (see issue #20)")
class AuthorizerLargeIntegerTests(AuthorizerTests):
    @staticmethod
    def authorizer_cb(action, arg1, arg2, dbname, source):
        if action != monetdbe.monetdbe_SELECT:
            return 2 ** 32
        if arg2 == 'c2' or arg1 == 't2':
            return 2 ** 32
        return monetdbe.monetdbe_OK


if __name__ == "__main__":
    unittest.main()
