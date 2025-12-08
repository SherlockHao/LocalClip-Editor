# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
LocalClip Editor Windows 版本
"""

import sys
import os
from pathlib import Path

# 获取项目根目录
block_cipher = None
project_root = Path(SPECPATH).parent
backend_dir = project_root / "backend"
frontend_dir = project_root / "frontend"

# 收集所有需要的数据文件
datas = []

# 1. 前端静态文件
frontend_dist = frontend_dir / "dist"
if frontend_dist.exists():
    datas.append((str(frontend_dist), "frontend/dist"))
    print(f"✅ 添加前端文件: {frontend_dist}")
else:
    print(f"⚠️  前端未构建: {frontend_dist}")

# 2. 后端数据目录（空目录作为占位符）
for dir_name in ["uploads", "exports"]:
    dir_path = backend_dir / dir_name
    if dir_path.exists():
        datas.append((str(dir_path), dir_name))

# 3. package_utils.py 和 platform_utils.py
datas.append((str(backend_dir / "package_utils.py"), "."))
datas.append((str(backend_dir / "platform_utils.py"), "."))

# 收集隐藏导入
hiddenimports = [
    # FastAPI 和 Uvicorn
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",

    # FastAPI 依赖
    "fastapi",
    "fastapi.staticfiles",
    "fastapi.responses",
    "pydantic",
    "starlette",
    "multipart",

    # MoviePy
    "moviepy.video.io.ffmpeg_tools",
    "moviepy.video.io.ffmpeg_reader",
    "moviepy.video.io.ffmpeg_writer",
    "moviepy.audio.fx.all",
    "moviepy.video.fx.all",
    "moviepy.video.compositing.concatenate",

    # PyTorch
    "torch",
    "torch.nn",
    "torch.nn.functional",
    "torchaudio",
    "torchaudio.transforms",

    # Transformers
    "transformers",
    "transformers.models",
    "transformers.models.wav2vec2",
    "transformers.models.auto",

    # Pyannote.audio
    "pyannote.audio",
    "pyannote.audio.core",
    "pyannote.audio.pipelines",

    # 音频处理
    "librosa",
    "librosa.feature",
    "librosa.effects",
    "soundfile",
    "scipy",
    "scipy.signal",
    "scipy.io",
    "scipy.io.wavfile",

    # 机器学习
    "sklearn",
    "sklearn.cluster",
    "numpy",
    "numpy.core",

    # 其他
    "PIL",
    "PIL.Image",
    "speechmos",
    "onnxruntime",

    # Fish-Speech 相关
    "fish_speech",
]

# 分析主程序
a = Analysis(
    [str(backend_dir / "main.py")],
    pathex=[str(backend_dir), str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的包以减小体积
        "matplotlib",
        "pandas",
        "jupyter",
        "notebook",
        "IPython",
        "pytest",
        "setuptools",
        "pip",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 过滤掉不需要的文件
a.datas = [x for x in a.datas if not x[0].startswith("matplotlib")]
a.datas = [x for x in a.datas if not x[0].startswith("pandas")]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LocalClipEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 禁用 UPX 压缩以避免杀毒软件误报
    console=True,  # 显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件路径
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LocalClipEditor',
)

# 打印摘要信息
print("\n" + "=" * 60)
print("📦 PyInstaller 配置摘要")
print("=" * 60)
print(f"项目根目录: {project_root}")
print(f"后端目录: {backend_dir}")
print(f"前端目录: {frontend_dir}")
print(f"数据文件数量: {len(datas)}")
print(f"隐藏导入数量: {len(hiddenimports)}")
print("=" * 60)
