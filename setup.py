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

from numpy.distutils.command.build_clib import build_clib
#from numpy.distutils.command.build_src import build_src
#from distutils.command.build_clib import build_clib
import pip
import setuptools
import setuptools.command.test
import numpy
from distutils.cmd import Command

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
                'sources': [
                    'c/shadow_bind_c.c',
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
                'extra_compiler_args': [
                    #'-ffree-line-length-none',
                    #'-fomit-frame-pointer',
                ],
            }),
        ],
        description='SHADOW is an open source ray tracing code for modeling optical systems.',
        long_description=_read('README.txt'),
        install_requires=_install_requires(),
        cmdclass={
            'build_clib': BuildClib, ### BuildFortranLib,
            'build_src': BuildSrc,
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


class BuildSrc(Command, object):

    def initialize_options(*args, **kwargs):
        pass

    def finalize_options(*args, **kwargs):
        pass

    def run(*args, **kwargs):
        pass


from pykern.pkdebug import pkdp

class BuildClib(build_clib, object):

    def _shadow3_version_h(self, tmp_dir):
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

    def build_libraries(self, *args, **kwargs):
        self.mkpath(self.build_clib)
        h = self._shadow3_version_h(self.build_clib)
        f90 = self._f_compiler.compiler_f90
        f90 = [x for x in f90 if x not in ['-Wall', '-fno-second-underscore']]
        f90.extend(('-cpp', '-ffree-line-length-none', '-fomit-frame-pointer', '-I' + os.path.dirname(h)))
        self._f_compiler.compiler_f90 = f90
        return super(BuildClib, self).build_libraries(*args, **kwargs)


class BuildFortranLib(build_clib, object):

    def build_libraries(self, libraries, *args, **kwargs):
        l = []
        for x in libraries:
            if x[0] == FORTRAN_LIB:
                build_info = x[1]
            else:
                l.append(x)
        libraries = l
        tmp_dir = self.build_clib
        self.mkpath(tmp_dir)
        self._shadow3_version_h(tmp_dir)
        obj = []
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
        obj.extend(self._shadow3_fortran(build_info, tmp_dir))
        self.distribution.announce('linking {}'.format(FORTRAN_LIB))
        self.compiler.create_static_lib(
            obj,
            FORTRAN_LIB,
            output_dir=self.build_clib,
            debug=self.debug,
        )
        # Build the rest of the libraries (for completeness)
        return super(BuildFortranLib, self).build_libraries(libraries, *args, **kwargs)

    def _shadow3_fortran(self, build_info, tmp_dir):
        obj = []
        for src in build_info['sources']:
            if not src.endswith('f90'):
                continue
            self.distribution.announce('compiling {}'.format(src))
            o = os.path.join(tmp_dir, os.path.splitext(src)[0]) + self.compiler.obj_extension
            output_dir = os.path.dirname(o)
            self.mkpath(output_dir)
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
                src,
            ])
        return obj

    def _shadow3_object_filename(self, src, output_dir):
        # disutils.ccompiler has object_filenames, but it
        # asserts against the src_extensions, which are hardwired.
        # Could look into "adding a compiler", but that is
        # much more trouble than it is worth right now. It's
        # too bad numpy.distutils is so complicated
        assert not os.path.isabs(src), \
            '{}: do not use absolute file names for sources'
        obj = os.path.splitext(os.path.splitdrive(src)[1])[0]
        return obj + self.compiler.obj_extension


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
