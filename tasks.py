#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from invoke import task

@task
def coverage(c, details=False):
	c.run("coverage erase")
	c.run("coverage run -m pytest")
	if details:
		c.run("coverage html && coverage annotate")
		c.run("coverage report", pty=True)

@task
def test(c):
	coverage(c)

@task
def lint(c):
	c.run("python -m pylint -j 4 nut/Config.py tests/*.py nut/Nsps.py nut/Hex.py", pty=True)

@task
def run(c, gui=True):
	c.run("python nut_gui.py", pty=True)
