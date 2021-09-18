#!/usr/bin/env python3
from __future__ import print_function

import argparse
import sys

# Package information
version = __version__ = "1.1.0"
__title__ = "pylint_exit"
__summary__ = "Exit code handler for pylint command line utility."
__uri__ = "https://github.com/jongracecox/pylint-exit"


#: List of bit encoded exit codes, their meaning and whether to treat as a fatal message.
exit_code_list = [
    (1, 'fatal message issued', 1),
    (2, 'error message issued', 0),
    (4, 'warning message issued', 0),
    (8, 'refactor message issued', 0),
    (16, 'convention message issued', 0),
    (32, 'usage error', 1)
    ]


def decode(value):
    """
    Decode the return code value into a bit array.

    Args:
        value(int): Return code from pylint command line.

    Returns:
        list of raised exit codes.

    Example:
        >>> decode(1)
        [(1, 'fatal message issued', 1)]
        >>> decode(2)
        [(2, 'error message issued', 0)]
        >>> decode(3)
        [(1, 'fatal message issued', 1), (2, 'error message issued', 0)]
    """
    return [x[1] for x in zip(format(value, "b")[::-1], exit_code_list) if int(x[0])]


def get_messages(value):
    """
    Return a list of raised messages for a given pylint return code.

    Args:
        value(int): Return code from pylint command line.

    Returns:
        list of str: Raised messages.

    Example:
        >>> get_messages(1)
        ['fatal message issued']
        >>> get_messages(2)
        ['error message issued']
        >>> get_messages(3)
        ['fatal message issued', 'error message issued']
    """
    return [x[1] for x in decode(value)]


def get_exit_code(value):
    """
    Return the exist code that should be returned.

    Args:
        value(int): Return code from pylint command line.

    Returns:
        int: Return code that should be returned when run as a command.

    Example:
        >>> get_exit_code(1)
        1
        >>> get_exit_code(2)
        0
        >>> get_exit_code(3)
        1
        >>> get_exit_code(12)
        0
    """
    exit_codes = [x[2] for x in decode(value)]
    if not exit_codes:
        return 0
    else:
        return max(exit_codes)


def show_workings(value):
    """
    Display workings

    Args:
        value(int): Return code from pylint command line.

    Example:
        >>> show_workings(1)
        1 (1) = ['fatal message issued']
        >>> show_workings(12)
        12 (1100) = ['warning message issued', 'refactor message issued']
    """
    print("{0} ({0:b}) = {1}".format(value, [y[1] for y in decode(value)]))


def handle_exit_code(value):
    """
    Exit code handler.

    Takes a pylint exist code as the input parameter, and
    displays all the relevant console messages.

    Args:
        value(int): Return code from pylint command line.

    Returns:
        int: Return code that should be returned when run as a command.

    Example:
        >>> handle_exit_code(1)
        The following messages were raised:
        <BLANKLINE>
          - fatal message issued
        <BLANKLINE>
        Fatal messages detected.  Failing...
        1
        >>> handle_exit_code(12)
        The following messages were raised:
        <BLANKLINE>
          - warning message issued
          - refactor message issued
        <BLANKLINE>
        No fatal messages detected.  Exiting gracefully...
        0
    """
    messages = get_messages(value)
    exit_code = get_exit_code(value)

    if messages:
        print("The following messages were raised:")
        print('')

    for m in messages:
        print("  - %s" % m)

    if messages:
        print('')

    if exit_code:
        print("Fatal messages detected.  Failing...")
    else:
        print("No fatal messages detected.  Exiting gracefully...")

    return exit_code


def test():
    # Test function
    import doctest
    doctest.testmod()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()

    parser.add_argument('pylint_exit_code', metavar='PYLINTRC', type=int,
                        help='pylint return code')

    parser.add_argument('-efail', '--error-fail', action='store_true',
                        help='Fail on issued error messages')

    parser.add_argument('-wfail', '--warn-fail', action='store_true',
                        help='fail on issued warnings messages')

    parser.add_argument('-rfail', '--refactor-fail', action='store_true',
                        help='fail on issued refactor messages')

    parser.add_argument('-cfail', '--convention-fail', action='store_true',
                        help='fail on issued convention messages')

    return parser.parse_args()


def apply_enforcement_setting(key, value):
    """
    Apply an enforcement setting

    Args:
        key (str): specific message level to set
        value (int): new value for level

    Examples:

        >>> import pylint_exit
        >>> pylint_exit.exit_code_list[1]
        (2, 'error message issued', 0)

        >>> apply_enforcement_setting('error', 1)
        >>> pylint_exit.exit_code_list[1]
        (2, 'error message issued', 1)

        >>> apply_enforcement_setting('error', 0)  # Set back to normal again

    """
    positions = {
        "fatal": 0,
        "error": 1,
        "warning": 2,
        "refactor": 3,
        "convention": 4
    }
    # fetch the position from the dict
    position = positions[key]

    # unpack the tuple so it can be modified
    encoded, description, enforce = exit_code_list[position]
    enforce = value  # set the element to True (error)

    # repack it back into a tuple to match existing data type
    exit_code_list[position] = encoded, description, enforce


def handle_cli_flags(namespace):
    """
    Applies the CLI flags

    Args:
        namespace (argparse.Namespace): namespace from CLI arguments

    Examples:

        Take a look at the current settings:

            >>> import pylint_exit
            >>> pylint_exit.exit_code_list[1]
            (2, 'error message issued', 0)

        Create a namespace with some settings:

            >>> ns = argparse.Namespace()
            >>> ns.error_fail = True
            >>> ns.warn_fail = False
            >>> ns.refactor_fail = False
            >>> ns.convention_fail = False

        Use handle_cli_flags to update the exit code list:

            >>> handle_cli_flags(ns)
            >>> pylint_exit.exit_code_list[1]
            (2, 'error message issued', 1)

        Set everything back to normal again:

            >>> ns.error_fail = False
            >>> handle_cli_flags(ns)

    """
    # [
    #   (1, 'fatal message issued', 1),
    #   (2, 'error message issued', 0),
    #   (4, 'warning message issued', 0),
    #   (8, 'refactor message issued', 0),
    #   (16, 'convention message issued', 0),
    #   (32, 'usage error', 1)
    # ]
    if namespace.error_fail:  # fail on errors
        apply_enforcement_setting("error", 1)

    if namespace.warn_fail:
        apply_enforcement_setting("warning", 1)

    if namespace.refactor_fail:
        apply_enforcement_setting("refactor", 1)

    if namespace.convention_fail:
        # error on conventions
        apply_enforcement_setting("convention", 1)


def main():
    args = parse_args()
    handle_cli_flags(args)
    exit_code = handle_exit_code(args.pylint_exit_code)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
