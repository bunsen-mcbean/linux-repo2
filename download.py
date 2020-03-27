
import argparse
import json
import hashlib
import os
import subprocess
import tempfile
import urllib.request
from collections import OrderedDict
import re
from toposort import toposort_flatten as topo_sort


parser = argparse.ArgumentParser()
parser.add_argument('--packages', nargs='+')
parser.add_argument('--exclude', nargs='+', default=[])
opts = parser.parse_args()


R_INCLUDED = [
    'R',  # base
    'base',
    'compiler',
    'datasets',
    'graphics',
    'grDevices',
    'grid',
    'methods',
    'parallel',
    'splines',
    'stats',
    'stats4',
    'tcltk',
    'utils',
    'tools',
    'KernSmooth',  # recommended
    'MASS',
    'Matrix',
    'boot',
    'class',
    'cluster',
    'codetools',
    'foreign',
    'lattice',
    'mgcv',
    'nlme',
    'nnet',
    'rpart',
    'spatial',
    'survival' ]


global cran_packages
cran_packages = OrderedDict()


def download_cran_dir():
    global cran_packages
    url = 'https://cran.microsoft.com/snapshot/2020-01-01/src/contrib/PACKAGES'
    print('Downloading CRAN directory')
    re_line_fixer = re.compile('(\n +)', re.MULTILINE)
    re_key_value = re.compile('^([A-Za-z0-9]+):\s*(.+)$', re.MULTILINE)
    re_pkg_name = re.compile('[A-Za-z][A-Za-z0-9_\.]+')
    with urllib.request.urlopen(url) as response:
        body = response.read().decode('utf-8')
        print('Downloaded')
        print('Parsing')
        entries = body.split('\n\n')
        for pkg in entries:
            pkg = re_line_fixer.sub(' ', pkg)
            kvs = re_key_value.findall(pkg)
            kvs = dict(kvs)

            name = kvs['Package']
            version = kvs['Version']

            deps = [ ]

            if 'Depends' in kvs:
                deps = re_pkg_name.findall(kvs['Depends'])

            if 'Imports' in kvs:
                imps = re_pkg_name.findall(kvs['Imports'])
                deps.extend(imps)

            if 'LinkingTo' in kvs:
                link = re_pkg_name.findall(kvs['LinkingTo'])
                deps.extend(link)

            cran_packages[name] = { 'name': name, 'version': version, 'deps': set(deps) }

def get_cran_url(name: str) -> str:
    global cran_packages
    if name not in cran_packages:
        raise Exception('Package {} does not exist in CRAN', name)
    version = cran_packages[name]['version']
    return 'https://cran.microsoft.com/snapshot/2020-01-01/src/contrib/{}_{}.tar.gz'.format(name, version)


def get_package_deps(name: str):
    global cran_packages
    package = cran_packages[name]
    deps = set(package['deps'])
    for dep in package['deps']:
        if dep in R_INCLUDED or dep in opts.exclude:
            continue
        dep_deps = get_package_deps(dep)
        deps.update(dep_deps)
    return deps

def main():

    download_cran_dir()

    packages = set(opts.packages)
    for name in opts.packages:
        deps = get_package_deps(name)
        packages.update(deps)

    packages = list(filter(lambda x: x not in opts.exclude, packages))
    packages = list(filter(lambda x: x not in R_INCLUDED, packages))

    pkgs_dict = {}
    for name in packages:
        deps = cran_packages[name]['deps']
        pkgs_dict[name] = deps
    packages = topo_sort(pkgs_dict)
    packages = list(filter(lambda x: x not in opts.exclude, packages))
    packages = list(filter(lambda x: x not in R_INCLUDED, packages))

    sources = [ ]
    pkg_no = 0

    for name in packages:
        url = get_cran_url(name)
        filename = os.path.basename(url)
        local_path = '{n:03}_{filename}'.format(filename=filename, n=pkg_no)

        print('Downloading', name)
        with urllib.request.urlopen(url) as response:
            body = response.read()
            with open(local_path, 'wb') as output:
                output.write(body)

        pkg_no += 1


if __name__ == '__main__':
    main()
