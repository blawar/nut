#!/bin/bash
################################################################################
# Alex Hogen (code.ahogen@outlook.com)
# https://github.com/ahogen
#
# A basic script to inspect the return code from pylint, filter it based on our
# needs, and return with a non-zero exit code when appropriate.
#
# PyLint returns non-zero exit codes for things that aren't errors. For example,
# if a warning message was issued, 0x4 is OR'd into the exit code.
#
# This script simply masks out error bits we don't care about in our continuous
# integration script(s). I started by using "pylint-exit" but I can't change the 
# exit code easily when it is envoked from the command line.
#
# If the exit code was 63 (decimal), all error bits were set.
#
# USAGE:
#       $ pylint test_file.py || pylint_exit_handler.sh $?
#
#     To overwrite the default mask, simply set the PYLINT_EXIT_MASK variable.
#       $ export PYLINT_EXIT_MASK=1
#       $ pylint test_file.py || pylint_exit_handler.sh $?
#
# MIT License
# 
# Copyright (c) 2018 Alexander Hogen
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

function decode_pylint_exit_code() {
    error_code=$1

    # Decode the bit-encoded return code into the seperate return meanings.
    msg_fatal=$(((error_code & 1) >> 0))
    msg_error=$(((error_code & 2) >> 1))
    msg_warning=$(((error_code & 4) >> 2))
    msg_refactor=$(((error_code & 8) >> 3))
    msg_convention=$(((error_code & 16) >> 4))
    msg_usage_err=$(((error_code & 32) >> 5))

    # Print out what was just decoded above. Similar to what pylint-exit does.
    if [ $msg_fatal -ne 0 ]; then
        echo "  - FATAL error message issued"
    fi

    if [ $msg_error -ne 0 ]; then
        echo "  - ERROR message issued"
    fi

    if [ $msg_warning -ne 0 ]; then
        echo "  - WARNING message issued"
    fi

    if [ $msg_refactor -ne 0 ]; then
        echo "  - Refactor message issued"
    fi

    if [ $msg_convention -ne 0 ]; then
        echo "  - Convention message issued"
    fi

    if [ $msg_usage_err -ne 0 ]; then
        echo "  - USAGE ERROR message issued"
    fi
}

# Capture the first parameter, expected to be the pylint exit code
PYLINT_EC=${1}

echo "Receieved exit code ${PYLINT_EC} which means:"
decode_pylint_exit_code ${PYLINT_EC}

# Now, apply the pylint exit code mask to the error code and return with the
# masked error value.
if [ -z ${PYLINT_EXIT_MASK+x} ]; then
    echo "PYLINT_EXIT_MASK is unset"

    PYLINT_EXIT_MASK=3
    echo "Using default mask of ${PYLINT_EXIT_MASK}"
fi

MASKED_PYLINT_EC=$((PYLINT_EC & PYLINT_EXIT_MASK))
echo "Exiting with code (${PYLINT_EC} & ${PYLINT_EXIT_MASK} =) ${MASKED_PYLINT_EC}"
echo "Exit code ${MASKED_PYLINT_EC} means:"
decode_pylint_exit_code ${MASKED_PYLINT_EC}

exit ${MASKED_PYLINT_EC}
