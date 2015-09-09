# -*- coding: utf-8 -*-
"""Build and install Shadow3"""
from __future__ import division, absolute_import, print_function

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

import numpy
from numpy.distutils.command.build_clib import build_clib

from pykern import pksetup


class BuildClib(build_clib, object):
    """Set up for shadow3c build"""

    def build_libraries(self, *args, **kwargs):
        """Modify the f90 compiler flags and build shadow_version.h"""
        f90 = self._f_compiler.compiler_f90
        # Is this portable?
        f90.remove('-Wall')
        f90.remove('-fno-second-underscore')
        f90.extend(('-cpp', '-ffree-line-length-none', '-fomit-frame-pointer', '-I' + self.build_clib))
        self.__version_h()
        # This is an unfriendly patch: 
        # Redirect the compiler's create static lib function to create a shared lib. 
        # Save the function reference. 
        create_static_lib_func = self.compiler.create_static_lib 
        # Redirect to decorated create shared library function.
        self.compiler.create_static_lib = self.__redirect_linking_static_to_shared
        # Create library.
        result = super(BuildClib, self).build_libraries(*args, **kwargs)
        # Restore create static library reference.
        self.compiler.create_static_lib = create_static_lib_func

        return result

    def __redirect_linking_static_to_shared(self, objects, lib_name, output_dir, debug):
        return self.compiler.link_shared_lib(objects, lib_name,
                                             output_dir=output_dir,
                                             debug=debug,
                                             libraries=["gfortran"])

    def __version_h(self):
        self.mkpath(self.build_clib)
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
            # We can't show c compiler, because there's no such string
            # in distutils. msvccompiler, for example, creates the string
            # in the spawn() call. This tells us enough
            compiler=self._f_compiler.compiler_f90,
            date=datetime.datetime.utcnow().ctime() + ' UTC',
            header='compilation settings',
            hline='+' * 80,
            platform=platform.platform(),
            prefix=' ' + ('+' * 5),
            build=self.distribution.version,
        ).rstrip()
        lines = []
        for line in out.split('\n'):
            if not line:
                line = ' '
            line = 'print *,"{}"\n'.format(line)
            lines.append(line)
        out = os.path.join(self.build_clib, 'shadow_version.h')
        with open(out, 'w') as f:
            f.write(''.join(lines))
        return out


pksetup.setup(
    name='shadow3',
    packages=['Shadow'],
    url='http://forge.epn-campus.eu/projects/shadow3',
    license='http://www.gnu.org/licenses/gpl-3.0.html',
    author='Franco Cerrina, Chris Welnak, G.J. Chen, and M. Sanchez del Rio',
    author_email='srio@esrf.eu',
    description='SHADOW is an open source ray tracing code for modeling optical systems.',
    pksetup={
        'extra_directories': ['c', 'def', 'fortran', 'examples'],
    },
    libraries=[
        ('shadow3c', {
            'some-random-param': 1,
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
            # compilers, and some flags are only used. See BuildClib
        }),
    ],
    cmdclass={
        'build_clib': BuildClib,
        'build_src': pksetup.NullCommand,
    },
    ext_modules=[
        setuptools.Extension(
            name='Shadow.ShadowLib',
            sources=['c/shadow_bind_python.c'],
            include_dirs=['c', 'def', numpy.get_include()],
        ),
    ],
)
