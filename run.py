'''
Starts a Bokeh server at a randomly assigned port.
'''

from random import randint
import subprocess

port = randint(1000, 8888)
proc = 'bokeh serve --port {:04d} --show dash'.format(port)


if __name__ == '__main__':
   subprocess.run(proc, shell=True, check=True)
