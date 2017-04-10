'''
Script to be run when first installing the dashboard

- installs the packages listed under 'packages'
'''

import pip


packages = ['bokeh']


def install(package):
    pip.main(['install', package])



if __name__ == '__main__':
    print('Installing required packages. This may take a while...')
    for i, package in enumerate(packages):
        print("Installing package {} of {}:".format(i+1, len(packages)))
        print("pip install {}".format(package))
        install(package)


