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
                extra_compile_args=['-msse','-msse2'],
                extra_link_args=['-msse','-msse2'],
            ),
        ],
    )


class BuildFortranLib(build_clib):

    def build_libraries(self, *args, **kwargs):
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
            o = os.path.join(tmp_dir, os.path.splitext(src)[0]) + '.o'
            obj.append(o)
            print(o)
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
        o = os.path.join(tmp_dir, base + '.o')
        obj.append(o)
        subprocess.check_call([
            'gcc',
            '-fPIC',
            '-Ic',
            '-Idef',
            '-c',
            '-o',
            o,
            os.path.join('c', base + '.c'),
        ])
        #obj.append(o)
            # Now "link" the object files together into a static library.
            # (On Unix at least, this isn't really linking -- it just
            # builds an archive.  Whatever.)
        """
            self.compiler.create_static_lib(objects, lib_name,
                                            output_dir=self.build_clib,
                                            debug=self.debug)

        """
        tgt = os.path.join(tmp_dir, 'libshadow3c.a')
        cmd = [
            'ar',
            'cr',
            tgt,
        ]
        cmd.extend(obj)
        print(obj)
        subprocess.check_call(cmd)
	# $(bFC) $(LIBFLAGS) $(CFLAGS) -o libshadow3$(SO) $(OBJFMODULES)
        #ext.library_dirs.append(tmp_dir)

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
