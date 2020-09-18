#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import sys
import os
from pathlib import Path
import urllib3

if not getattr(sys, 'frozen', False):
    os.chdir(Path(__file__).resolve().parent)

from nut import Config
from nut import Print
from nut import Status
import Server
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
            Print.silent = True

        if args.hostname:
            args.server = True
            Config.server.hostname = args.hostname

        if args.port:
            args.server = True
            Config.server.port = int(args.port)

        Status.start()

        Print.info('                        ,;:;;,')
        Print.info('                       ;;;;;')
        Print.info('               .=\',    ;:;;:,')
        Print.info('              /_\', "=. \';:;:;')
        Print.info('              @=:__,  \\,;:;:\'')
        Print.info('                _(\\.=  ;:;;\'')
        Print.info('               `"_(  _/="`')
        Print.info('                `"\'')

        if args.usb:
            try:
                from nut import Usb
            except BaseException as e:
                Print.error('pip3 install pyusb, required for USB coms: ' +
                            f'{str(e)}')
            nut.scan()
            Usb.daemon()

        if args.server:
            nut.initFiles()
            nut.scan()
            Server.run()

        if len(sys.argv) == 1:
            import nut_gui
            nut_gui.run()

        Status.close()

    except KeyboardInterrupt:
        Config.isRunning = False
        Status.close()

    except BaseException:
        Config.isRunning = False
        Status.close()
        raise

    Print.info('fin')
