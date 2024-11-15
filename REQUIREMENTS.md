Requirements
============


Definitions and context
-----------------------

**[MonetDB]** is a fast analytics database.

Usually MonetDB is accessed through a client library API such as [pymonetdb],
ODBC or JDBC. **MonetDB/e** is an alternative API where MonetDB itself is
embedded in the application as a shared library (a DLL). MonetDB/e is part of the MonetDB codebase and can be used by C programs.

**[Python-MonetDBe]** is a project to make MonetDB/e available to Python
programs as a Python [DBAPI] compliant database library. It provides a Python
package called [monetdbe]. The package is available from the [PyPI] package
repository, so Python programmers can `pip install monetdbe` before they `import monetdbe`.

Precompiled binary distributions of Python packages are known as **wheels**.
They can be downloaded from [PyPI].


Requirements
------------

> **REQUIREMENT 1.** Python-MonetDBe makes MonetDB/e available to Python programs.
> with an API complying to the Python [DBAPI] specification.

> **REQUIREMENT 2A.** All supported MonetDB branches not older than Dec2023 MUST
> be supported when building from source. The development branch of MonetDB MUST
> also be supported.

The exact cut off might be subject to discussion.

> **REQUIREMENT 2B.** All Python versions &ge;3.8 MUST be supported, including
> BOTH flavors of Python 3.13.

Again, the exact cut off might be subject to discussion.

> **REQUIREMENT 2C.** Binary wheels for all MonetDB releases starting from
> Aug2024-SP1 MUST be available from [PyPI] for Linux (x86_64), Windows (x86_64)
> and MacOS (x86_64 and arm64).

> **REQUIREMENT 2D.** Exact platform requirements to be determined.

Not sure exactly what to promise here. For example Windows Server 2019 is easy
to test on GitHub but we should probably also specify Windows 10 here. Will we test that somehow? Hope for the best? Same for all the Linux distributions. They probably work fine if we build for manylinux_2_28, but...

> **REQUIREMENT 3A.** The version number of the package MUST indicate the
> underlying MonetDB version. It SHOULD be straightforward to determine the
> exact versions of Python-MonetDBe and MonetDB itself used to build a binary
> package.

Technically it's possible to have a single version of MonetDBe-Python and
generate binary packages for Dec2023, Aug2024-SP5 and Feb2025 simply by building
with different parameters. The second phrase of the requirement implies that it
is probably better to have a one-to-one correspondence between binary package
versions and commits in the projects Git history.

> **REQUIREMENT 4A.** There SHOULD be a single Python script or other entry
> point that can be run to build wheels for any supported platform, any
> supported Python version and any supported MonetDB version. The script MAY
> assume that MonetDB itself has already been installed. The script SHOULD give
> clear guidance if things need to be installed before it can work,and where to
> get them.

It's important that monetdbe packages are easy to build for people who just want
to play with or have some ad-hoc task.

> **REQUIREMENT 4B.** It SHOULD be trivial build and test binary packages for
> all platforms. The resulting packages SHOULD be ready to upload to PyPI.

In other words, we build the packages in GitHub Actions. And clearly document
how to do trigger that.




[MonetDB]: https://www.monetdb.org/
[Python-MonetDBe]: https://github.com/MonetDBSolutions/MonetDBe-Python
[DBAPI]: https://peps.python.org/pep-0249/
[monetdbe]: https://pypi.org/project/monetdbe/
[PyPI]: https://pypi.org/