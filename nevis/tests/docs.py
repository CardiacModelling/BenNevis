#!/usr/bin/env python3
#
# Nevis tests related to documentation
#
import importlib
import inspect
import os
import re
import subprocess
import sys


def printline():
    """ Utility method for printing horizontal lines. """
    print('-' * 60)


def colored(color, text):
    """ Utility method for printing colored text. """
    colors = {
        'normal': '\033[0m',
        'warning': '\033[93m',
        'fail': '\033[91m',
        'bold': '\033[1m',
        'underline': '\033[4m',
    }
    return colors[color] + str(text) + colors['normal']


def test_documentation():
    """
    Checks if the documentation can be built, runs all doc tests, exits if
    anything fails.
    """
    print('Checking documentation coverage.')

    # Scan for classes and functions
    modules, classes, functions = test_doc_coverage_get_objects()

    # Check if they're all shown somewhere
    ok = test_doc_coverage(classes, functions)

    # Terminate if failed
    if not ok:
        sys.exit(1)

    # Build docs and run doc tests
    print('Building docs and running doctests.')
    p = subprocess.Popen([
        'sphinx-build',
        '-b',
        'doctest',
        'docs/source',
        'docs/build/html',
        '-W',
    ])
    try:
        ret = p.wait()
    except KeyboardInterrupt:
        try:
            p.terminate()
        except OSError:
            pass
        p.wait()
        print('')
        sys.exit(1)
    if ret != 0:
        print('FAILED')
        sys.exit(ret)


def test_doc_coverage(classes, functions):
    """
    Check all classes and functions exposed by nevis are included in the docs
    somewhere.
    """

    doc_files = []
    for root, dirs, files in os.walk(os.path.join('docs', 'source')):
        for file in files:
            if file.endswith('.rst'):
                doc_files.append(os.path.join(root, file))

    # Regular expression that would find either 'module' or 'currentmodule':
    # this needs to be prepended to the symbols as x.y.z != x.z
    regex_module = re.compile(r'\.\.\s*\S*module\:\:\s*(\S+)')

    # Regular expressions to find autoclass and autofunction specifiers
    regex_class = re.compile(r'\.\.\s*autoclass\:\:\s*(\S+)')
    regex_funct = re.compile(r'\.\.\s*autofunction\:\:\s*(\S+)')

    # Identify all instances of autoclass and autofunction in all rst files
    doc_classes = []
    doc_functions = []
    for doc_file in doc_files:
        with open(doc_file, 'r') as f:
            # We need to identify which module each class or function is in
            module = ''
            for line in f.readlines():
                m_match = re.search(regex_module, line)
                c_match = re.search(regex_class, line)
                f_match = re.search(regex_funct, line)
                if m_match:
                    module = m_match.group(1) + '.'
                elif c_match:
                    doc_classes.append(module + c_match.group(1))
                elif f_match:
                    doc_functions.append(module + f_match.group(1))

    # Check if documented symbols match known classes and functions
    classes = set(classes)
    functions = set(functions)
    doc_classes = set(doc_classes)
    doc_functions = set(doc_functions)

    undoc_classes = classes - doc_classes
    undoc_functions = functions - doc_functions
    extra_classes = doc_classes - classes
    extra_functions = doc_functions - functions

    # Compare the results
    if undoc_classes:
        n = len(undoc_classes)
        printline()
        print('Found (' + str(n) + ') classes without documentation:')
        print('\n'.join(
            '  ' + colored('warning', y) for y in sorted(undoc_classes)))
    if undoc_functions:
        n = len(undoc_functions)
        printline()
        print('Found (' + str(n) + ') functions without documentation:')
        print('\n'.join(
            '  ' + colored('warning', y) for y in sorted(undoc_functions)))
    if extra_classes:
        n = len(extra_classes)
        printline()
        print('Found (' + str(n) + ') documented but unknown classes:')
        print('\n'.join(
            '  ' + colored('warning', y) for y in sorted(extra_classes)))
    if extra_functions:
        n = len(extra_functions)
        printline()
        print('Found (' + str(n) + ') documented but unknown classes:')
        print('\n'.join(
            '  ' + colored('warning', y) for y in sorted(extra_functions)))
    n = (len(undoc_classes) + len(undoc_functions)
         + len(extra_classes) + len(extra_functions))
    printline()
    print('Found total of (' + str(n) + ') mismatches.')

    return n == 0


def test_doc_coverage_get_objects():
    """
    Scans nevis and returns a list of modules, a list of classes, and a list of
    functions.
    """
    print('Finding nevis modules...')

    def find_modules(root, modules=[], ignore=[]):
        """ Find all modules in the given directory. """

        # Get root as module
        module_root = root.replace('/', '.')

        # Check if this path is on the ignore list
        if root in ignore:
            return modules

        # Check if this is a module
        if os.path.isfile(os.path.join(root, '__init__.py')):
            modules.append(module_root)
        else:
            return modules

        # Look for submodules
        for name in os.listdir(root):
            if name[:1] == '_' or name[:1] == '.':
                continue
            path = os.path.join(root, name)
            if os.path.isdir(path):
                find_modules(path, modules, ignore)
            else:
                base, ext = os.path.splitext(name)
                if ext == '.py':
                    modules.append(module_root + '.' + base)

        # Return found
        return modules

    # Get modules
    import nevis
    modules = find_modules('nevis', ignore=['nevis/tests'])

    # Import all modules
    for module in modules:
        importlib.import_module(module)

    # Find modules, classes, and functions
    def scan(module, root, pref, modules, classes, functions):
        nroot = len(root)
        for name, member in inspect.getmembers(module):
            if name[0] == '_':
                # Don't include private members
                continue

            # Get full name
            full_name = pref + name
            # Module
            if inspect.ismodule(member):
                try:
                    # Don't scan external modules
                    if member.__file__ is None:
                        continue
                    if member.__file__[0:nroot] != root:
                        continue
                except AttributeError:
                    # Built-ins have no __file__ and should not be included
                    continue
                if full_name in modules:
                    continue
                modules.add(full_name)
                mpref = full_name + '.'
                mroot = os.path.join(root, name)
                scan(member, mroot, mpref, modules, classes, functions)

            # Class
            elif inspect.isclass(member):
                mod = member.__module__
                if mod == 'nevis' or mod.startswith('nevis.'):
                    classes.add(full_name)

            # Function
            elif inspect.isfunction(member):
                mod = member.__module__
                if mod == 'nevis' or mod.startswith('nevis.'):
                    functions.add(full_name)

        return

    # Scan and return
    print('Scanning nevis modules...')
    module = nevis
    modules = set()
    classes = set()
    functions = set()
    root = os.path.dirname(module.__file__)
    pre = module.__name__ + '.'
    scan(module, root, pre, modules, classes, functions)

    print(
        'Found (' + str(len(modules)) + ') modules, identified ('
        + str(len(classes)) + ') classes and (' + str(len(functions))
        + ') functions.')

    return modules, classes, functions


if __name__ == '__main__':
    test_documentation()
