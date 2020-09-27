#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
import os
from pathlib import Path
import urllib3

if not getattr(sys, 'frozen', False):
    os.chdir(Path(__file__).resolve().parent)

from nut import config
from nut import printer
from nut import status
import server
import nut

if __name__ == '__main__':
    try:
        urllib3.disable_warnings()

        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--usb',
            action="store_true",
            help='Run usb daemon',
        )
        parser.add_argument(
            '-S',
            '--server',
            action="store_true",
            help='Run server daemon',
        )
        parser.add_argument('-m', '--hostname', help='Set server hostname')
        parser.add_argument('-p', '--port', type=int, help='Set server port')
        parser.add_argument(
            '--silent',
            action="store_true",
            help='Suppresses stdout',
        )

        args = parser.parse_args()

        if args.silent:
            printer.silent = True

        if args.hostname:
            args.server = True
            config.server.hostname = args.hostname

        if args.port:
            args.server = True
            config.server.port = int(args.port)

        status.start()

        printer.info('                        ,;:;;,')
        printer.info('                       ;;;;;')
        printer.info('               .=\',    ;:;;:,')
        printer.info('              /_\', "=. \';:;:;')
        printer.info('              @=:__,  \\,;:;:\'')
        printer.info('                _(\\.=  ;:;;\'')
        printer.info('               `"_(  _/="`')
        printer.info('                `"\'')

        if args.usb:
            try:
                from nut import usb
                nut.scan()
                usb.daemon()
            except BaseException as e:
                printer.error('pip3 install pyusb, required for USB coms: ' +
                              f'{str(e)}')

        if args.server:
            nut.scan()
            server.run()

        if len(sys.argv) == 1:
            import nut_gui
            nut_gui.run()

        status.close()

    except KeyboardInterrupt:
        config.isRunning = False
        status.close()

    except BaseException:
        config.isRunning = False
        status.close()
        raise

    printer.info('fin')
