#!/usr/bin/env python
import sys
import os
import shutil
import argparse
import itertools

def parse_args(*args):

    parser = argparse.ArgumentParser(description="""
Perform destructive operations safely. Specify a list of files
followed by the command. No files are permitted after command.
""")
 
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='display targets, and prompt before executing command')
    parser.add_argument('files', nargs='+',
                        help='one or more file or directory names')
    parser.add_argument('command', choices=['remove','move','copy'],
                        help='command to perform on files')
    args = parser.parse_args(*args)

    command = None

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
    """Classify items in file, directories, etc.
    """
    exist, nonexist = partition(items, os.path.exists)
    files, nonfiles = partition(exist, os.path.isfile)
    dirs, unknown   = partition(nonfiles, os.path.isdir)
    return files, dirs, unknown, nonexist


def print_items(items):
    """Column-formatted output.
    """
    max_cols = 80
    width = max(len(f) for f in items) + 2
    width_fmt = '{:>'+str(width)+'}'
    words_per_line = max_cols / width
    num_lines = (len(items) + words_per_line) / (words_per_line + 1)
    it = iter(items)
    for i in xrange(num_lines):
        for _, word in itertools.izip(xrange(words_per_line), it):
            print width_fmt.format(word),
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
            
    
def main():
    args = parse_args()
    
    fg, dg, ug, ng = classify(args.files)

    nonexist = list(ng)
    unknown  = list(ug)
    dirs     = list(dg)
    files    = list(fg)

    if args.interactive:
        if files:
            print 'files to {}:'.format(args.command)
            print_items(files)
        if dirs:
            print 'dirs to {}:'.format(args.command)
            print_items(dirs)
        if unknown:
            print 'unknown items:'
            print_items(unknown)
        if nonexist:
            print 'not found items:'
            print_items(nonexist)

        response = raw_input('proceed? (y/n)')
        if response != 'y':
            sys.exit(0)

    if not files and not dirs:
        print 'Nothing to do!'
        sys.exit(1)

    if args.command == 'remove':
        remove(files, dirs)
    
    sys.exit(0)

if __name__ == '__main__':
    main()

################################################################
# Tests

import unittest
import contextlib
import tempfile
import subprocess

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
        self.assertEqual(args.files,['foo','bar','baz'])
        self.assertEqual(args.command,'remove')

    def test_args_02(self):
        """Has not implemented copy command yet.
        """
        self.assertRaises(NotImplementedError, parse_args, 'foo bar baz copy'.split())

    def test_args_03(self):
        """Does not recognize this command.
        """
        self.assertRaises(FunkyParserError, parse_args, 'foo bar baz unknown'.split())

    def test_args_04(self):
        """Needs at least one target.
        """
        self.assertRaises(FunkyParserError, parse_args, 'remove'.split())

    def test_classify_01(self):
        """Correctly classifies temporary files and directory.
        """
        with self.mkdtemp() as d1,\
                self.mkstemp(prefix=d1+'/') as f1,\
                self.mkstemp(prefix=d1+'/') as f2,\
                self.mkstemp(prefix=d1+'/') as f3:
            files, dirs, unknown, nonexist = classify([d1,f1,f2,f3])
            self.assertEqual(list(files),    [f1,f2,f3])
            self.assertEqual(list(dirs),     [d1])
            self.assertEqual(list(unknown),  [])
            self.assertEqual(list(nonexist), [])
            

    def test_remove_01(self):
        """Successfully removes temp files.
        """
        files = []
        for _ in xrange(10):
            fd, path = tempfile.mkstemp()
            files.append(path)
        remove(files,[])
        for i in xrange(10):
            self.assertFalse(os.path.exists(files[i]))

    def test_remove_02(self):
        """Successfully removes temp directories.
        """
        dirs = []
        for _ in xrange(10):
            path = tempfile.mkdtemp()
            dirs.append(path)
        remove([],dirs)
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
            proc = subprocess.Popen(['python', __file__, d1, f1, f2, f3, 'remove'],
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            stdout, stderr = proc.communicate('y\n')
            rc = proc.wait()

            if rc:
                print stdout
                print stderr

            self.assertEqual(rc,0)
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

        self.assertEqual(rc,1)
