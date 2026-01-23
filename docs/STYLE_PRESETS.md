# Cortex3d 风格预设系统 v1.0

## 快速使用

```bash
# 查看所有可用风格
python scripts/generate_character.py --list-styles

# 使用风格预设
python scripts/generate_character.py --from-image img.png --pixel
python scripts/generate_character.py --from-image img.png --ghibli
python scripts/generate_character.py --from-image img.png --clay

# 也可以通过 --style 参数指定风格名称
python scripts/generate_character.py --from-image img.png --style minecraft
```

## 可用风格预设

| 参数 | 风格 | 描述 | 关键词 |
|------|------|------|--------|
| `--photorealistic` | 超写实 | 8K照片级真实感 | photo, real, raw, 8k |
| `--anime` | 动漫 | 日式赛璐璐着色 | manga, 2d, cel-shaded |
| `--ghibli` | 吉卜力 | 宫崎骏水彩画风 | miyazaki, totoro, spirited away |
| `--pixel` | 像素 | 16-bit复古游戏风格 | 8bit, retro, mario, nes |
| `--minecraft` | Minecraft | 体素方块风格 | voxel, blocky, cube |
| `--clay` | 粘土 | 橡皮泥/定格动画风格 | claymation, plasticine, stop-motion |
| `--plush` | 毛绒 | 布艺玩偶风格 | felt, stuffed, kawaii |
| `--paper` | 纸片人 | Paper Mario风格 | papercraft, flat, 2.5d |
| `--cyberpunk` | 赛博朋克 | 霓虹灯科幻风格 | neon, sci-fi, futuristic |
| `--fantasy` | 奇幻 | 中世纪RPG风格 | medieval, dnd, magic |
| `--watercolor` | 水彩 | 传统水彩画风格 | painted, traditional |
| `--oil` | 油画 | 古典油画风格 | classical, renaissance, impasto |
| `--3d-toon` | 3D卡通 | 皮克斯/迪士尼风格 | pixar, disney, dreamworks |
| `--comic` | 美漫 | 超级英雄漫画风格 | marvel, dc, superhero |
| `--minimal` | 极简 | 扁平设计风格 | flat, vector, simple |
| `--lowpoly` | 低多边形 | 几何3D风格 | polygon, geometric, faceted |

## 风格效果示例

### 🎮 像素风格 (--pixel)
适合复古游戏风格角色，生成16-bit时代的像素画质感：
- 清晰的像素边缘，无抗锯齿
- 有限的调色板 (16-64色)
- 抖动渐变效果

### 🏔️ 吉卜力风格 (--ghibli)
宫崎骏/吉卜力工作室的手绘水彩美学：
- 柔和的水彩质感
- 温暖的自然配色
- 梦幻怀旧氛围

### 🧱 Minecraft风格 (--minecraft)
经典的体素方块造型：
- 立方体几何体
- 16x16像素纹理
- 锐利的几何边缘

### 🎨 粘土风格 (--clay)
Wallace & Gromit式的定格动画质感：
- 橡皮泥材质
- 可见的手工痕迹
- 柔软的哑光表面

### 🧸 毛绒风格 (--plush)
可爱的布艺玩偶外观：
- 绒布/毛毡材质
- 可见的缝线
- 扣子眼睛

### 📄 纸片人风格 (--paper)
Paper Mario式的2.5D效果：
- 扁平的纸张角色
- 矢量化边缘
- 层叠的纸张深度

## 组合使用

```bash
# 像素风格 + 单视角
python scripts/generate_character.py --from-image img.png --pixel --custom-views front

# 吉卜力风格 + 主体隔离
python scripts/generate_character.py --from-image img.png --ghibli --subject-only

# 粘土风格 + 严格复制模式
python scripts/generate_character.py --from-image img.png --clay --strict

# 赛博朋克风格 + 6视角
python scripts/generate_character.py --from-image img.png --cyberpunk --views 6
```

## 自定义风格

如果预设不满足需求，可以使用 `--style` 参数自定义：

```bash
python scripts/generate_character.py --from-image img.png --style "steampunk victorian, brass and copper, mechanical gears, sepia tones"
```

## 添加新风格

编辑 `scripts/prompts/styles.py` 文件，使用 `register_style()` 函数注册新风格：

```python
register_style(StylePreset(
    name="your-style",
    aliases=["alias1", "alias2"],
    description="风格描述",
    prompt="完整的风格提示词",
    style_instruction="详细的风格指令",
    enhancements=", 增强词1, 增强词2",
    negative_hints=["不要的元素1", "不要的元素2"],
    keywords=["关键词1", "关键词2"]
))
```
