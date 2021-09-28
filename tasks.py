#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

from invoke import task

if os.name == 'nt': # Windows
	py = "python"
else:
	py = "python3"

@task
def coverage(c, details=False, gui=False):
	c.run("coverage erase")
	if gui:
		c.run("coverage run -m pytest")
	else:
		c.run("coverage run -m pytest --ignore tests-gui")
	if details:
		c.run("coverage html && coverage annotate")
		c.run("coverage report", pty=True)

@task
def test(c):
	coverage(c)

@task
def lint(c):
	run_arg = "pylint -j 4 nut/Config.py tests/ nut/Nsps.py nut/Hex.py nut_gui.py \
		gui/panes/dirlist.py gui/panes/filters.py gui/panes/format.py Fs/driver/http.py \
		nut/config_impl/download.py gui/table_model.py gui/header.py gui/app.py \
		gui/panes/options.py"
	if os.name == 'nt': # Windows
		c.run(run_arg)
	else:
		c.run(run_arg, pty=True)

@task
def run(c, gui=True):
	run_arg = f"{py} nut_gui.py"
	if os.name == 'nt': # Windows
		c.run(run_arg)
	else:
		c.run(run_arg, pty=True)
