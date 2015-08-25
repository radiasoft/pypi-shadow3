# -*- coding: utf-8 -*-
#
# SHADOW is an open source ray tracing code for modeling optical systems.
#
from __future__ import division, absolute_import, print_function

import os.path

import pip
from distutils.command.build_ext import build_ext
import setuptools
import subprocess

import numpy

def _read(filename):
    with open(filename, 'r') as f:
        return f.read()

def _install_requires():
    reqs = pip.req.parse_requirements(
        'requirements.txt', session=pip.download.PipSession())
    return [str(i.req) for i in reqs]

#FC = gfortran
#FFLAGS = -cpp -fPIC -ffree-line-length-none $(32BITS) $(STATIC) -O2 -fomit-frame-pointer $(COMPILEOPT)
#LINKFLAGS = $(32BITS) $(STATIC)

class BuildExt(build_ext):
    def build_extension(self, ext, *args, **kwargs):
        subprocess.check_call(['touch', 'fortran/shadow_version.h'])
        import os
        tmp_dir = os.path.join(self.build_temp, 'c')
        try:
            os.makedirs(tmp_dir)
        except OSError:
            pass
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
        return build_ext.build_extension(self, ext, *args, **kwargs)

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
