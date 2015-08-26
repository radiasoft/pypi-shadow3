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

from distutils.command.build_ext import build_ext
import pip
import setuptools
import numpy

def main():
    setuptools.setup(
        name='Shadow',
        version='0.1.0',
        packages=['Shadow'],
        package_dir={'Shadow':'Shadow'},
        description='SHADOW is an open source ray tracing code for modeling optical systems.',
        long_description=_read('README.txt'),
        install_requires=_install_requires(),
        cmdclass={
            'build_ext': BuildExt,
        },
        ext_modules=[
            setuptools.Extension(
                name='Shadow.ShadowLib',
                sources=['c/shadow_bind_python.c'],
                include_dirs=['c', 'def', numpy.get_include()],
                libraries=['gfortran', 'shadow3c'],
                extra_compile_args=['-msse','-msse2'],
                extra_link_args=['-msse','-msse2'],
            ),
        ],
    )


def _read(filename):
    with open(filename, 'r') as f:
        return f.read()



def _install_requires():
    reqs = pip.req.parse_requirements(
        'requirements.txt', session=pip.download.PipSession())
    return [str(i.req) for i in reqs]


class BuildExt(build_ext):
    def build_extension(self, ext, *args, **kwargs):
        self._libshadow3c(ext)
        return build_ext.build_extension(self, ext, *args, **kwargs)

    def _libshadow3c(self, ext):
        if hasattr(self, '_libshadow3c_sentinel'):
            return
        self._libshadow3c_sentinel = True
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
                '-fomit-frame-pointer',
                # Don't hardwire
                '-D_COMPILE4NIX',
                '-Ifortran',
                '-J' + tmp_dir,
                '-Idef',
                '-c',
                # Don't hardwire extension
                '-o',
                o,
                os.path.join('fortran', src),
            ])
        base = 'shadow_bind_c'
        o = os.path.join(tmp_dir, base + '.o')
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
        obj.append(o)
        tgt = os.path.join(tmp_dir, 'libshadow3c.a')
        cmd = [
            'ar',
            'cr',
            tgt,
        ]
        cmd.extend(obj)
        print(tgt)
        subprocess.check_call(cmd)
	# $(bFC) $(LIBFLAGS) $(CFLAGS) -o libshadow3$(SO) $(OBJFMODULES)
        ext.library_dirs.append(tmp_dir)

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
        res = os.path.join(self.build_temp, 'c')
        try:
            os.makedirs(res)
        except OSError:
            pass
        return res


if '__main__' == __name__:
    main()
