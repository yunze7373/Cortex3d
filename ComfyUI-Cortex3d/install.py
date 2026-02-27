"""ComfyUI 自动安装钩子 — 安装 Cortex3d 节点包所需依赖。"""
import subprocess
import sys
from pathlib import Path


def install():
    req = Path(__file__).parent / "requirements.txt"
    if not req.exists():
        print("[Cortex3d] requirements.txt 不存在，跳过依赖安装")
        return
    print("[Cortex3d] 正在安装依赖...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        stdout=subprocess.DEVNULL,
    )
    print("[Cortex3d] 依赖安装完成 ✓")


if __name__ == "__main__":
    install()
else:
    # ComfyUI Manager 在 import 时自动执行
    install()
