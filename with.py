#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
with -- Perform destructive file operations safely.

Copyright © 2013 Robert Hunter

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.import sys
"""

import sys
import os
import shutil
import argparse
import itertools


def parse_args(*args, **kwargs):

    parser = argparse.ArgumentParser(description="""
Perform destructive file operations safely. Specify a list of files
followed by the command. No files are permitted after command.
""")

    parser.add_argument('--interactive', '-i', action='store_true',
                        help='prompt before executing command. '
                        'implies verbose.')

    parser.add_argument('--verbose', '-v', action='store_true',
                        help='display targets')

    parser.add_argument('files', nargs='+',
                       help='one or more file or directory names.  '
                        'a single dash "-" forces filenames '
                        'to be read from standard input, and disables '
                        'interactive mode.')

    parser.add_argument('command', choices=['remove', 'move', 'copy'],
                        help='command to perform on files')

    args = parser.parse_args(*args)

    if args.interactive:
        args.verbose = True

    if args.files == ['-']:
        input_stream = kwargs['stream']
        args.files = [line.strip() for line in input_stream]
        args.interactive = False
        args.verbose = True

    if args.command != 'remove':
        raise NotImplementedError

    return args


def partition(items, predicate=bool):
    """Partition a list based on predicate.  Courtesy of Ned Batchelder.
    http://nedbatchelder.com/blog/201306/filter_a_list_into_two_parts.html
    """
    a, b = itertools.tee((predicate(item), item) for item in items)
    return ((item for pred, item in a if pred),
            (item for pred, item in b if not pred))


def classify(items):
    """Classify items into file, directories, etc.
    """
    exist, nonexist = partition(items, os.path.exists)
    files, nonfiles = partition(exist, os.path.isfile)
    dirs, unknown = partition(nonfiles, os.path.isdir)
    return tuple(list(g) for g in (files, dirs, unknown, nonexist))


def numbins(n, binsize):
    return 1 + ((n - 1) / binsize)


def print_items(hdr, items):
    """Column-formatted output.
    """
    print hdr

    max_cols = 120
    width = max(len(f) for f in items) + 2

    if width > max_cols:
        max_cols = width

    items_per_line = max_cols / width
    num_lines = numbins(len(items), items_per_line)

    itemfmt = '{:<'+str(width)+'}'

    it = iter(items)
    for _ in xrange(num_lines):
        for _, item in itertools.izip(xrange(items_per_line), it):
            print itemfmt.format(item),
        print


def remove(files, dirs):
    """Here goes.
    """
    for f in files:
        try:
            os.remove(f)
        except Exception as e:
            print str(e)
            sys.exit(1)
    for f in dirs:
        try:
            shutil.rmtree(f)
        except Exception as e:
            print str(e)
            sys.exit(1)


def prompt_to_proceed():
    response = raw_input('proceed? (y/n)')
    if response != 'y':
        sys.exit(0)


def main():

    args = parse_args(stream=sys.stdin)

    files, dirs, unknown, nonexist = classify(args.files)

    if args.verbose:
        if files:
            hdr = 'files to {}:'.format(args.command)
            print_items(hdr, files)
        if dirs:
            hdr = 'dirs to {}:'.format(args.command)
            print_items(hdr, dirs)

    if nonexist or unknown:
        if unknown:
            hdr = 'unknown items:'
            print_items(hdr, unknown)
        if nonexist:
            hdr = 'not found items:'
            print_items(hdr, nonexist)

    if not files and not dirs:
        print 'Nothing to do.'
        sys.exit(1)

    if args.interactive:
        prompt_to_proceed()

    if args.command == 'remove':
        remove(files, dirs)
    else:
        raise RuntimeError

if __name__ == '__main__':
    main()

################################################################
# Tests

import unittest
import contextlib
import tempfile
import subprocess
import StringIO

class FunkyParserError(RuntimeError):
    pass


class TestWith(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestWith, self).__init__(*args, **kwargs)

        def error(*args):
            raise FunkyParserError()
        argparse.ArgumentParser.error = error

    @staticmethod
    @contextlib.contextmanager
    def mkdtemp(*args, **kwargs):
        path = tempfile.mkdtemp(*args, **kwargs)
        try:
            yield path
        finally:
            try:
                shutil.rmtree(path)
            except:
                pass

    @staticmethod
    @contextlib.contextmanager
    def mkstemp(*args, **kwargs):
        fd, path = tempfile.mkstemp(*args, **kwargs)
        try:
            yield path
        finally:
            try:
                os.close(fd)
                os.remove(path)
            except:
                pass

    def test_args_01(self):
        """Returns list of three files.
        """
        args = parse_args('foo bar baz remove'.split())
        self.assertEqual(args.files, ['foo', 'bar', 'baz'])
        self.assertEqual(args.command, 'remove')

    def test_args_02(self):
        """Has not implemented copy command yet.
        """
        self.assertRaises(NotImplementedError, parse_args,
                          'foo bar baz copy'.split())

    def test_args_03(self):
        """Does not recognize this command.
        """
        self.assertRaises(FunkyParserError, parse_args,
                          'foo bar baz unknown'.split())

    def test_args_04(self):
        """Needs at least one target.
        """
        self.assertRaises(FunkyParserError, parse_args, 'remove'.split())

    def test_args_05(self):
        """Reads list of filenames from input stream.
        """
        files = 'foo bar baz bang qux quxx'.split()
        stream = StringIO.StringIO('\n'.join(files))
        args = parse_args('- remove'.split(), stream=stream)
        self.assertEqual(args.files, files)

    def test_args_06(self):
        """Reads list of filenames with embedded spaces from input stream.
        """
        files = ['foo bar', 'baz bang', 'qux quxx']
        stream = StringIO.StringIO('\n'.join(files))
        args = parse_args('- remove'.split(), stream=stream)
        self.assertEqual(args.files, files)

    def test_classify_01(self):
        """Correctly classifies temporary files and directory.
        """
        with self.mkdtemp() as d1,\
                self.mkstemp(prefix=d1+'/') as f1,\
                self.mkstemp(prefix=d1+'/') as f2,\
                self.mkstemp(prefix=d1+'/') as f3:
            files, dirs, unknown, nonexist = classify([d1, f1, f2, f3])
            self.assertEqual(files, [f1, f2, f3])
            self.assertEqual(dirs, [d1])
            self.assertEqual(unknown, [])
            self.assertEqual(nonexist, [])

    def test_remove_01(self):
        """Successfully removes temp files.
        """
        files = []
        for _ in xrange(10):
            fd, path = tempfile.mkstemp()
            files.append(path)
        remove(files, [])
        for i in xrange(10):
            self.assertFalse(os.path.exists(files[i]))

    def test_remove_02(self):
        """Successfully removes temp directories.
        """
        dirs = []
        for _ in xrange(10):
            path = tempfile.mkdtemp()
            dirs.append(path)
        remove([], dirs)
        for i in xrange(10):
            self.assertFalse(os.path.exists(dirs[i]))

    def test_main_01(self):
        """Completes functional test by removing specified files, and
        directory, and then exits with zero code.
        """
        with self.mkdtemp() as d1,\
                self.mkstemp(prefix=d1) as f1,\
                self.mkstemp(prefix=d1+'/') as f2,\
                self.mkstemp(prefix=d1+'/') as f3:
            proc = subprocess.Popen(['python', __file__, d1, f1, f2, f3,
                                     'remove'],
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            stdout, stderr = proc.communicate('y\n')
            rc = proc.wait()

            if rc:
                print stdout
                print stderr

            self.assertEqual(rc, 0)
            self.assertFalse(os.path.exists(f1))
            self.assertFalse(os.path.exists(f2))
            self.assertFalse(os.path.exists(f3))
            self.assertFalse(os.path.exists(d1))

    def test_main_02(self):
        """Fails functional test because files do not exist, and so it
        exits with non-zero code.
        """
        with self.mkstemp() as f1,\
                self.mkstemp() as f2,\
                self.mkstemp() as f3:
            pass

        proc = subprocess.Popen(['python', __file__, f1, f2, f3, 'remove'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        stdout, stderr = proc.communicate('y\n')
        rc = proc.wait()

        self.assertEqual(rc, 1)

    def test_main_03(self):
        """Completes functional test by removing files and directory
        specified on standard input, and then exits with zero code.
        """
        with self.mkdtemp() as d1,\
                self.mkstemp(prefix=d1) as f1,\
                self.mkstemp(prefix=d1+'/') as f2,\
                self.mkstemp(prefix=d1+'/') as f3:
            proc = subprocess.Popen(['python', __file__, '-',
                                     'remove'],
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            files = '\n'.join([d1, f1, f2, f3])
            stdout, stderr = proc.communicate(files)
            rc = proc.wait()

            if rc:
                print stdout
                print stderr

            self.assertEqual(rc, 0)
            self.assertFalse(os.path.exists(f1))
            self.assertFalse(os.path.exists(f2))
            self.assertFalse(os.path.exists(f3))
            self.assertFalse(os.path.exists(d1))

    def test_main_04(self):
        """Fails functional test because files do not exist, and so it
        exits with non-zero code.
        """
        with self.mkstemp() as f1,\
                self.mkstemp() as f2,\
                self.mkstemp() as f3:
            pass

        proc = subprocess.Popen(['python', __file__, '-', 'remove'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        files = '\n'.join([f1, f2, f3])
        stdout, stderr = proc.communicate(files)
        rc = proc.wait()

        self.assertEqual(rc, 1)


class TestBins(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        self.longMessage = True
        super(TestBins, self).__init__(*args, **kwargs)

    def msg(self, i, j, k):
        return 'multiplier = {}, binsize = {}, items = {}'.format(i, j, k)

    def test_numbins_1(self):
        """Should return correct bin size for a range of bin sizes
        and number of items.
        """
        for i in xrange(0, 20):  # multiple of bin size
            for j in xrange(1, 100):  # bin size
                for k in xrange(i*j+1, (i+1)*j):  # number of items
                    self.assertEqual(numbins(k, j), i+1, self.msg(i, j, k))
