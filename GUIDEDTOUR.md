# How it works

In this document we explain in detail how Python-MonetDBe works and how it's
built and released, so future maintainers don't have to reinvent all the wheels.

For an overview of what we're trying to achieve, see
[REQUIREMENTS.md](./REQUIREMENTS.md). That document also contains an explanation
of the relationship between the names **MonetDB**, **MonetDB/e**,
**Python-MonetDB** and **monetdbe**.


For a more action-oriented guide of how to release a new version, see
[HOWTORELEASE.md](./HOWTORELEASE.md).


## Preliminaries: embeddeding MonetBD in a C program

You are probably reading this because you want to work on the Python bindings
but it's useful to first consider how MonetDB is embedded in a C program.

We will assume MonetDB has already been installed and that header files can be
found in `$MONETDBE_INCLUDE_PATH` and libraries in `$MONETDBE_LIBRARY_PATH`.
This means that `$MONETDBE_INCLUDE_PATH` must contain the file
`monetdb_config.h` and `$MONETDBE_LIBRARY_PATH` must contain `libmonetdbe.so` on
Linux, `libmonetdbe.dylib` on MacOS and `monetdbe.dll` on Windows.

With that in place, consider the following C program:

```C
#include <stdio.h>
#include "monetdbe.h"
int main(void)
{
    char *dbpath = "/tmp/db_dir";
    monetdbe_database db = NULL;
    if (monetdbe_open(&db, dbpath, NULL) != 0) {
        printf("Failed to open database directory '%s'\n", dbpath);
        return 1;
    }
    printf("Succesfully opened database directory '%s'\n", dbpath);
    monetdbe_close(db);
    return 0;
}
```
On Linux and Mac, this can be compiled with the command
```bash
cc -o minimal minimal.c -I$MONETDBE_INCLUDE_PATH -lmonetdbe -L$MONETDBE_LIBRARY_PATH
```
Note how the program includes `"monetdbe.h"` to get the declarations of the type
`monetdbe_database` and the function `monetdbe_open`, and the `-I` flag tells
 the compiler where to find that file. Similarly, `-lmonetdbe` tells the
compiler to link the library which contains the implementation, and `-L` tells
it where to find that library.

It is not a bad idea to try this out right now if you have never done so before.
Chances are it won't work immediately. The next section may help.


## Library paths

One common complication is that the `-L` flag at the command line above only
says where the library can be found at compile time. It does not help the
resulting executable find it at run time. This means that if the MonetDB
libraries are not installed in one of the systems directories, `minimal` will
give an error message when we try to run it:
```
$ ./minimal
./minimal: error while loading shared libraries: libmonetdbe.so.27: cannot open shared object file: No such file or directory
$ export LD_LIBRARY_PATH=/path/to/monetdb/lib
$ ./minimal
Succesfully opened database directory '/tmp/db_dir'
```
In the example above we fixed the problem temporarily with an environment
variable. On Linux this is `LD_LIBRARY_PATH`. On MacOS it's called
`DYLD_LIBRARY_PATH`. On Windows, who knows?

Fixing the problem with an environment variable is fine for the testing
environment but obviously not when the software is installed on the end users's
system. We will get back to this issue later on.


## Python bindings

The purpose of the *Python-MonetDBe* project is to provide a package *monetdbe*
which allows Python programs to use *MonetDB/e* with an API that conforms to
Python's [DBAPI]. To do so, the package has to bridge to gaps:

1. The gap from Python code to C code
2. The gap from the [DBAPI] API to the MonetDB/e API.

To do so, *monetdbe* consists of an outer module `monetdbe` and an inner module
`monetdbe._lowlevel`. The inner module bridges the gap from Python to C. It
exports Python types and functions that correspond one-to-one with MonetDB/e
types and functions. For example, in the C code above we saw function
`monetdbe_open()` which takes three arguments and returns a handle. The inner
module provides Python function `monetdbe._lowlevel.lib.monetdbe_open` which
also take three arguments and returns a handle object.

The inner module is written in C. Most of the C code is generated automatically
by *cffi*, see below. The outer module is written in Python and maps DBAPI to
the MonetDB/e API.


## CFFI

[CFFI] is a tool that takes as input a number of C type- and function
declarations and outputs C code for a Python module that allows Python to access
them. We use it to generate the inner module described the previous section.

Ideally, we could just point it at `$MONETDBE_INCLUDE_PATH/monetdbe.h` but that
will never work. Instead, we have
[monetdbe/_cffi/embed.h.j2](monetdbe/_cffi/embed.h.j2). This contains simplified
declarations that [CFFI] can understand. It's a [Jinja2] template because the
declarations vary slightly between MonetDB versions. For example, at the time of
writing the template takes parameters like 'have_load_extension' and
'have_option_no_int128'.

CFFI is invoked from a script `monetdbe/_cffi/builder.py`. That script examines
`$MONETDBE_INCLUDE_PATH` and `$MONETDBE_LIBRARY_PATH`, renders the template, and
eventually runs `ffibuilder.compile()` to generate all C code and build the
inner module. Apart from the header file mentioned above, CFFI is also passed

1. some extra helper code read from `native_utilities.c`
2. an instruction to link to libmonetdbe
3. the include- and library path

Normally builder.py is automatically run by the build system (see below) but it
is instructive to run it manually.

To do so, first temporarily delete the directories LICENSES/ and notebooks/.
They confuse the tooling when building manually. Then check the top of
'pyproject.toml' for the dependencies to install, and create and activate a venv
to install them in:

```
$ rm LICENSES notebooks -rf
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv) $ head -2 pyproject.toml
[build-system]
requires = ["setuptools >= 40.6.0", 'cffi', 'jinja2']
(.venv) $ pip install setuptools cffi jinja2 numpy
```
Then we set the environment variables builder.py needs to find MonetDB if we
have not already done so, and run the script:
```
(.venv) $ export MONETDBE_INCLUDE_PATH=/path/to/monetdb/include/monetdb
(.venv) $ export MONETDBE_LIBRARY_PATH=/path/to/monetdb/lib/
(.venv) $ python ./monetdbe/_cffi/builder.py 
generating ./monetdbe/_lowlevel.c
(already up-to-date)
the current directory is '/home/jvr/src/monetdbe-python-dummy'
running build_ext
building 'monetdbe._lowlevel' extension
gcc -Wsign-compare -DNDEBUG -g -fwrapv -O3 -Wall -fPIC -I/path/to/monetdb/include/monetdb -I/home/jvr/src/monetdbe-python-dummy/.venv/include -I/home/jvr/lib/pyenv/versions/3.11.4/include/python3.11 -c monetdbe/_lowlevel.c -o ./monetdbe/_lowlevel.o
gcc -shared -L/home/jvr/lib/pyenv/versions/3.11.4/lib -Wl,-rpath,/home/jvr/lib/pyenv/versions/3.11.4/lib -L/home/jvr/lib/pyenv/versions/3.11.4/lib -Wl,-rpath,/home/jvr/lib/pyenv/versions/3.11.4/lib ./monetdbe/_lowlevel.o -L/path/to/monetdb/lib/ -L/home/jvr/lib/pyenv/versions/3.11.4/lib -lmonetdbe -o ./monetdbe/_lowlevel.cpython-311-x86_64-linux-gnu.so
```
This results in a file `_lowlevel.*.so` in the monetbde directory. You can
inspect its source in `monetdbe/_lowlevel.c`. After installing some runtime
dependencies we can now start Python and try to load it:

```
(.venv) $ pip install numpy pandas
...
(.venv) $ python
Python 3.11.4 (main, Aug 25 2023, 14:04:46) [GCC 12.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import monetdbe._lowlevel
>>> monetdbe._lowlevel.lib.monetdbe_open
<built-in method monetdbe_open of _cffi_backend.Lib object at 0x7fa21fefb740>
```

Do not forget to restore the LICENSES/ and notebooks/ when the experiment is
done.


##



[DBAPI]: https://peps.python.org/pep-0249/
[Jinja2]: https://jinja.palletsprojects.com/en/stable/

<!-- 
## Bla bla bla




## Preliminaries:  cffi

There are many ways to interact with 

## Our cffi


## Building the package


## Making it standalone


## 