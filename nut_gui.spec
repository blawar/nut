# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['nut_gui.py'],
             pathex=['nut', 'C:\\nut'],
             binaries=[('C:\\Windows\\System32\\libusb0.dll', '.')],
             datas=[('public_html', 'public_html'), ('plugins', 'plugins')],
             hiddenimports=['google-api-python-client'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='nut_gui',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True , icon='public_html\\images\\favicon.ico')
