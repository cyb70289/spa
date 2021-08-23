#!usr/bin/env python3
import platform
import os
import shutil
from sh import (
lsb_release,
service,
ErrorReturnCode,
)
import sh
import logging as log
def install_ebpf():
    # Save where we were so we can go back
    prior_dir = os.getcwd()
    # Make sure we are in the charm directory
    # Install prereqs for bcc (API to eBPF)
    apt_install = sh.Command('apt-get')
    apt_install(['install', 'git', 'build-essential', 'flex', 'bison',
                 'libelf-dev', 'zlib1g-dev', 'cmake', 'libtinfo-dev',
                 'libncurses-dev','python3-pip','python3-pandas',
                 'python3-sh','-y'])

    arch = platform.processor()
    print(arch)
    distro = lsb_release('-cs').strip()
    if distro == 'xenial' or arch == 'aarch64':
        # We need to install LLVM 6 when the distro is xenial or
        # when arch is Aarch64.
        # For more information, see:
        # https://github.com/iovisor/bcc/issues/492
        from sh import wget, tar
        from distutils.dir_util import copy_tree
        if arch == 'x86_64':
            dirname = 'clang+llvm-6.0.0-x86_64-linux-gnu-ubuntu-16.04'
        elif arch == 'aarch64':
            dirname = 'clang+llvm-6.0.0-aarch64-linux-gnu'
        wget('https://releases.llvm.org/6.0.0/{}.tar.xz'.format(dirname))
        tar.xf(dirname + '.tar.xz')
        # We use distutils.dir_util.copy_tree instead of
        # shutil.copytree since the latter will fail if the
        # destination directory already exists (/opt usually exists).
        # We just want to add files to it.
        copy_tree(dirname, '/opt/')
    else:  # The packaged versions of LLVM and clang work correctly on x86_64 and artful.
        apt_install(['install', '-y', 'clang-13','clang-tools-13','clang-13-doc','libclang-common-13-dev','libclang-13-dev','libclang1-13','clang-format-13','clangd-13'])
        apt_install(['install', '-y', 'libllvm-13-ocaml-dev','libllvm13','llvm-13','llvm-13-dev','llvm-13-doc','llvm-13-examples','llvm-13-runtime'])
        apt_install(['install', '-y', 'libfuzzer-13-dev', 'lldb-13', 'lld-13', 'libc++-13-dev', 'libc++abi-13-dev', 'libomp-13-dev', 'libclc-13-dev', 'libunwind-13-dev'])


    from sh import git, cmake, make, nproc
    # Build and install bcc
    #bcc_repo = 'git://www.ast.arm.com/github.com/iovisor/bcc'
    bcc_repo = 'git://github.com/iovisor/bcc'
    bcc_tag = 'v0.21.0'
    print('Building bcc from {} tag {}'.format(bcc_repo, bcc_tag))
    shutil.rmtree('bcc', ignore_errors=True)
    git.clone(['--branch', bcc_tag, bcc_repo])
    os.makedirs('bcc/build')
    os.chdir('bcc/build')
    print('CMAKE')
    cmake('..', '-DCMAKE_INSTALL_PREFIX=/usr', '-DPYTHON_CMD=python3', '-DCMAKE_PREFIX_PATH=/opt')
    jobs = nproc().strip()
    make('-j', jobs)
    make.install()
    os.chdir(prior_dir)  # go back to the previous working directory
    shutil.rmtree('libpfm4', ignore_errors=True)
    git.clone("git://perfmon2.git.sourceforge.net/gitroot/perfmon2/libpfm4")
    os.chdir("libpfm4")
    make()
    os.chdir(prior_dir)

def get_ast_cache():
    """ Find the location of the AST cache
    """
    import socket
    ast_cache = ['ast-cache', 'www', 'services']
    for cache in ast_cache:
        try:
            socket.gethostbyname(cache)
        except socket.error:
            pass
        else:
            return 'http://{}/static/'.format(cache)
    return None

if __name__ == "__main__":
    install_ebpf()
