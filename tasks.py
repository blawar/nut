#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from invoke import task

@task
def coverage(c, details=False, clean=False):
	if clean:
		c.run("rm -rf ./htmlcov")
	else:
		c.run("coverage run -m pytest")
		if details:
			c.run("coverage html && coverage annotate")

@task
def test(c):
	coverage(c)

@task
def lint(c):
	c.run("python -m pylint -j 4 nut/Config.py tests/*.py nut/Nsps.py")

@task
def run(c, gui=True):
	result = c.run("python nut_gui.py", pty=True)
	print(result.stdout)
