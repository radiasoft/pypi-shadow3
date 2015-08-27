# -*- coding: utf-8 -*-
#
# SHADOW is an open source ray tracing code for modeling optical systems.
#
from __future__ import division, absolute_import, print_function

from distutils.cmd import Command
import datetime
import glob
import os
import os.path
import pip
import platform
import setuptools
import setuptools.command.test
import subprocess
import sys

from numpy.distutils.command.build_clib import build_clib


def main():
    setuptools.setup(
        name='Shadow',
        version='0.1.0',
        packages=['Shadow'],
        package_dir={'Shadow':'Shadow'},
        test_suite='tests',
        tests_require=['pytest'],
        libraries=[
            ('shadow3c', {
                'sources': [
                    'c/shadow_bind_c.c',
                    # The order of these files matters, because fortran
                    # compilers need the "*.mod" files for "use" statements
                    'fortran/shadow_version.f90',
                    'fortran/shadow_globaldefinitions.f90',
                    'fortran/stringio.f90',
                    'fortran/gfile.f90',
                    'fortran/shadow_beamio.f90',
                    'fortran/shadow_math.f90',
                    'fortran/shadow_variables.f90',
                    'fortran/shadow_roughness.f90',
                    'fortran/shadow_kernel.f90',
                    'fortran/shadow_synchrotron.f90',
                    'fortran/shadow_pre_sync.f90',
                    'fortran/shadow_pre_sync_urgent.f90',
                    'fortran/shadow_preprocessors.f90',
                    'fortran/shadow_postprocessors.f90',
                    'fortran/shadow_bind_f.f90',
                    'fortran/shadow_crl.f90',
                ],
                'macros': [('_COMPILE4NIX', 1)],
                'include_dirs': ['def', 'fortran', 'c'],
                # Can't use extra_compiler_args, because applied to all
                # compilers, and some flags are only used
            }),
        ],
        description='SHADOW is an open source ray tracing code for modeling optical systems.',
        long_description=_read('README.txt'),
        install_requires=_install_requires(),
        cmdclass={
            'build_clib': BuildClib, ### BuildFortranLib,
            'build_src': NullCommand,
            'test': PyTest,
        },
        ext_modules=[
            setuptools.Extension(
                name='Shadow.ShadowLib',
                sources=['c/shadow_bind_python.c'],
                include_dirs=['c', 'def'],
                libraries=['gfortran'],
            ),
        ],
    )


class BuildClib(build_clib, object):

    def build_libraries(self, *args, **kwargs):
        self.mkpath(self.build_clib)
        h = _version_h(self.build_clib)
        f90 = self._f_compiler.compiler_f90
        f90 = [x for x in f90 if x not in ['-Wall', '-fno-second-underscore']]
        f90.extend(('-cpp', '-ffree-line-length-none', '-fomit-frame-pointer', '-I' + os.path.dirname(h)))
        self._f_compiler.compiler_f90 = f90
        return super(BuildClib, self).build_libraries(*args, **kwargs)


class NullCommand(Command, object):

    def initialize_options(*args, **kwargs):
        pass

    def finalize_options(*args, **kwargs):
        pass

    def run(*args, **kwargs):
        pass


class PyTest(setuptools.command.test.test, object):
    """Proper initialization of `pytest` for ``python setup.py test``"""

    def finalize_options(self):
        """Initialize test_args and set test_suite to True"""
        super(PyTest, self).finalize_options()
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        """Import `pytest` and calls `main`. Calls `sys.exit` with result"""
        import pytest
        err = pytest.main(['tests'])
        sys.exit(err)


def _install_requires():
    reqs = pip.req.parse_requirements(
        'requirements.txt', session=pip.download.PipSession())
    return [str(i.req) for i in reqs]


def _read(filename):
    with open(filename, 'r') as f:
        return f.read()


def _version_h(tmp_dir):
    t = '''{hline}
{header:^80}
{hline}

{prefix}Date:
{date}

{prefix}Compiler:
{compiler}

{prefix}Platform:
{platform}

{prefix}Build:
{build}

{hline}'''
    out = t.format(
        compiler=subprocess.check_output(
            ['gfortran', '-v'],
            stderr=subprocess.STDOUT,
        ),
        date=datetime.datetime.utcnow().ctime() + ' UTC',
        header='compilation settings',
        hline='+' * 80,
        platform=platform.platform(),
        prefix=' ' + ('+' * 5),
        build='N/A',
    ).rstrip()
    lines = []
    for line in out.split('\n'):
        if not line:
            line = ' '
        line = 'print *,"{}"\n'.format(line)
        lines.append(line)
    out = os.path.join(tmp_dir, 'shadow_version.h')
    with open(out, 'w') as f:
        f.write(''.join(lines))
    return out


if '__main__' == __name__:
    main()
