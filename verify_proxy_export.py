#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证代理模式 --export-prompt 功能"""

import subprocess
import sys

result = subprocess.run([
    sys.executable,
    'scripts/generate_character.py',
    '测试角色',
    '--views', '4',
    '--mode', 'proxy',
    '--token', 'dummy-token',
    '--export-prompt'
], capture_output=True, text=True, encoding='utf-8', errors='replace')

output = result.stdout + result.stderr

# 检查关键标志
checks = [
    ('包含导出提示词标记', '导出提示词' in output),
    ('包含完整提示词部分', '完整提示词' in output or 'Generate a professional' in output),
    ('未调用 AiProxy API', 'generate_image_via_proxy' not in output and '[AiProxy]' not in output),
    ('成功退出（退出码 0）', result.returncode == 0),
    ('包含配置参数说明', '配置参数' in output or 'Configuration' in output or 'resolution' in output.lower()),
]

print('\n' + '='*60)
print('✅ 代理模式 --export-prompt 功能验证')
print('='*60)

all_pass = all(c[1] for c in checks)

for name, passed in checks:
    status = '✓' if passed else '✗'
    print(f'  {status} {name}')

print(f'\n退出码: {result.returncode}')

if all_pass:
    print('\n✅ 所有检查通过！代理模式 --export-prompt 功能正常工作\n')
else:
    print('\n❌ 部分检查失败\n')
    print('输出摘要（最后 30 行）:')
    print('-' * 60)
    lines = output.split('\n')
    for line in lines[-30:]:
        if line.strip():
            print(line)

sys.exit(0 if all_pass else 1)
