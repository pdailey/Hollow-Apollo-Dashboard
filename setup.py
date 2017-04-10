'''
Script to be run when first installing the dashboard

installes the packages listed under 'packages'
'''

import pip

packages = ['bokeh', 'tornado']

def install(package):
    pip.main(['install', package])


if __name__ == '__main__':
    for package in packages:
	print("pip install {}".format(package))
        install(package)


