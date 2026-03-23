# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules

datas = [('llm_config.yaml', '.'), ('core/prompts', 'core/prompts'), ('runtime/agents', 'runtime/agents'), ('preprocessing', 'preprocessing')]
hiddenimports = ['litellm', 'json_repair', 'tiktoken_ext.openai_public', 'tiktoken_ext']
datas += collect_data_files('litellm')
datas += collect_data_files('litellm.litellm_core_utils')
hiddenimports += collect_submodules('api')
hiddenimports += collect_submodules('litellm.litellm_core_utils')


a = Analysis(
    ['server.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='whatif-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='whatif-server',
)
