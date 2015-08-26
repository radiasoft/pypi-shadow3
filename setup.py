# -*- coding: utf-8 -*-
#
# SHADOW is an open source ray tracing code for modeling optical systems.
#
from __future__ import division, absolute_import, print_function

import datetime
import os
import os.path
import platform
import subprocess
import sys

from distutils.command.build_clib import build_clib
import pip
import setuptools
import setuptools.command.test
import numpy

FORTRAN_LIB = 'shadow3c'

def main():
    setuptools.setup(
        name='Shadow',
        version='0.1.0',
        packages=['Shadow'],
        package_dir={'Shadow':'Shadow'},
        test_suite='tests',
        tests_require=['pytest'],
        libraries=[
            (FORTRAN_LIB, {
                'sources': ['c/shadow_bind_c.c'],
            }),
        ],
        description='SHADOW is an open source ray tracing code for modeling optical systems.',
        long_description=_read('README.txt'),
        install_requires=_install_requires(),
        cmdclass={
            'build_clib': BuildFortranLib,
            'test': PyTest,
        },
        ext_modules=[
            setuptools.Extension(
                name='Shadow.ShadowLib',
                sources=['c/shadow_bind_python.c'],
                include_dirs=['c', 'def', numpy.get_include()],
                libraries=['gfortran'],
            ),
        ],
    )


class BuildFortranLib(build_clib, object):

    def build_libraries(self, libraries, *args, **kwargs):
        libraries = [x for x in libraries if x[0] != FORTRAN_LIB]
        tmp_dir = self._libshadow3c_tmp_dir()
        self._libshadow3c_version_h(tmp_dir)
        obj = []
        for src in (
            'shadow_version.F90',
            'shadow_globaldefinitions.F90',
            'stringio.F90',
            'gfile.F90',
            'shadow_beamio.F90',
            'shadow_math.F90',
            'shadow_variables.F90',
            'shadow_roughness.F90',
            'shadow_kernel.F90',
            'shadow_synchrotron.F90',
            'shadow_pre_sync.F90',
            'shadow_pre_sync_urgent.F90',
            'shadow_preprocessors.F90',
            'shadow_postprocessors.F90',
            'shadow_bind_f.F90',
            'shadow_crl.F90',
            ):
            self.distribution.announce('compiling {}'.format(src))
            o = os.path.join(tmp_dir, os.path.splitext(src)[0]) + '.o'
            obj.append(o)
            subprocess.check_call([
                'gfortran',
                '-cpp',
                '-fPIC',
                '-ffree-line-length-none',
                '-O2',
                '-Ifortran',
                '-Idef',
                '-c',
                '-fomit-frame-pointer',
                '-J' + tmp_dir,
                '-D_COMPILE4NIX',
                '-o',
                # Don't hardwire extension
                o,
                os.path.join('fortran', src),
            ])
        base = 'shadow_bind_c'
        c = os.path.join('c', base + '.c')
        self.distribution.announce('compiling {}'.format(c))
        objects = self.compiler.compile(
            [c],
            output_dir=self.build_temp,
            macros=[('_COMPILE4NIX',)],
            include_dirs=['c', 'def'],
            debug=self.debug)
        obj.extend(objects)
        self.distribution.announce('linking {}'.format(FORTRAN_LIB))
        self.compiler.create_static_lib(
            obj,
            FORTRAN_LIB,
            output_dir=self.build_clib,
            debug=self.debug,
        )
        # Build the rest of the libraries (for completeness)
        return super(BuildFortranLib, self).build_libraries(libraries, *args, **kwargs)

    def _libshadow3c_version_h(self, tmp_dir):
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
        with open(os.path.join(tmp_dir, 'shadow_version.h'), 'w') as f:
            f.write(''.join(lines))

    def _libshadow3c_tmp_dir(self):
        res = self.build_clib
        try:
            os.makedirs(res)
        except OSError:
            pass
        return res


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


def _read(filename):
    with open(filename, 'r') as f:
        return f.read()


def _install_requires():
    reqs = pip.req.parse_requirements(
        'requirements.txt', session=pip.download.PipSession())
    return [str(i.req) for i in reqs]


if '__main__' == __name__:
    main()
