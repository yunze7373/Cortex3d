#!/usr/bin/env python3
"""
Cortex3d 风格预设系统 v1.0
工业级风格定义，支持多种艺术风格的精确控制

每个风格预设包含：
- name: 风格名称
- aliases: 别名列表（用于命令行参数匹配）
- description: 风格描述
- prompt: 完整的风格提示词（用于生成）
- style_instruction: 风格指令（用于模板替换）
- enhancements: 增强词（附加到描述后）
- negative_hints: 负面提示（用于 Gemini 的语义负面指令）
- keywords: 风格关键词（用于自动检测）
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class StylePreset:
    """风格预设定义"""
    name: str
    aliases: List[str]
    description: str
    prompt: str
    style_instruction: str
    enhancements: str
    negative_hints: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    def matches(self, query: str) -> bool:
        """检查查询是否匹配此风格"""
        query_lower = query.lower()
        # 检查名称和别名
        if query_lower == self.name.lower():
            return True
        if any(query_lower == alias.lower() for alias in self.aliases):
            return True
        # 检查关键词
        if any(kw.lower() in query_lower for kw in self.keywords):
            return True
        return False


# =============================================================================
# 工业级风格预设定义
# =============================================================================

STYLE_PRESETS: Dict[str, StylePreset] = {}


def register_style(preset: StylePreset):
    """注册风格预设"""
    STYLE_PRESETS[preset.name] = preset
    for alias in preset.aliases:
        STYLE_PRESETS[alias] = preset


# -----------------------------------------------------------------------------
# 1. 写实风格 (Photorealistic)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="photorealistic",
    aliases=["real", "photo", "realistic", "8k", "raw"],
    description="超写实照片风格",
    prompt="Photorealistic, 8k, raw photo, realistic texture, hyperrealistic photography, highly detailed skin texture, cinematic lighting",
    style_instruction="""**PHOTOREALISTIC STYLE - REAL PHOTO QUALITY:**
- Generate as if photographed by a professional camera
- Realistic skin texture, natural lighting, real photography look
- Highly detailed: pores, fabric textures, subtle color variations
- Cinematic lighting with natural shadows
- ❌ DO NOT generate as: cartoon, 3D render, CGI, illustration, anime
- ✅ MUST look like: actual photographs of a real person/subject""",
    enhancements=", detailed face, delicate features, high resolution, 8k, masterpiece, photorealistic, sharp focus, professional photography",
    negative_hints=["cartoon", "anime", "3D render", "CGI", "illustration", "painting", "drawing"],
    keywords=["photorealistic", "photo", "realistic", "raw", "real", "8k", "hyperrealistic"]
))


# -----------------------------------------------------------------------------
# 2. 动漫风格 (Anime)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="anime",
    aliases=["manga", "2d", "cel", "cel-shaded"],
    description="日式动漫风格",
    prompt="Anime style, cel shaded, vibrant colors, 2D art style, clean line art, anime proportions",
    style_instruction="""**ANIME/MANGA STYLE REQUIRED:**
- Classic anime/manga art style with cel shading
- Clean, bold line art with vibrant colors
- Stylized proportions typical of anime (large expressive eyes, etc.)
- Flat color fills with minimal gradients
- Dynamic lighting with anime-style highlights
- ❌ DO NOT generate as: photorealistic, 3D render, Western cartoon
- ✅ MUST look like: Japanese anime production quality""",
    enhancements=", detailed face, delicate features, high resolution, masterpiece, sharp lines, clean art, anime quality",
    negative_hints=["photorealistic", "3D render", "realistic", "Western cartoon", "CGI"],
    keywords=["anime", "manga", "2d", "cel shaded", "cel-shaded", "japanese animation"]
))


# -----------------------------------------------------------------------------
# 3. 吉卜力风格 (Ghibli)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="ghibli",
    aliases=["studio-ghibli", "miyazaki", "ghibli-style"],
    description="宫崎骏/吉卜力工作室风格",
    prompt="Studio Ghibli style, Hayao Miyazaki art direction, soft watercolor aesthetic, hand-painted backgrounds, gentle lighting, nostalgic atmosphere, whimsical character design",
    style_instruction="""**STUDIO GHIBLI / MIYAZAKI STYLE:**
- Soft, dreamy watercolor aesthetic with hand-painted quality
- Gentle, warm color palette with natural earth tones
- Detailed, lush backgrounds with atmospheric perspective
- Character designs: rounded, friendly, expressive faces
- Nostalgic, whimsical atmosphere
- Soft lighting with gentle gradients
- Nature-inspired details and environmental harmony
- ❌ DO NOT generate as: photorealistic, hard-edged anime, dark/gritty
- ✅ MUST look like: Official Ghibli film frame""",
    enhancements=", detailed face, soft features, masterpiece, Ghibli quality, watercolor texture, hand-painted feel",
    negative_hints=["photorealistic", "3D render", "dark", "gritty", "hard edges", "digital art"],
    keywords=["ghibli", "miyazaki", "totoro", "spirited away", "howl", "ponyo", "studio ghibli"]
))


# -----------------------------------------------------------------------------
# 4. 像素风格 (Pixel Art)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="pixel",
    aliases=["pixel-art", "8bit", "16bit", "retro", "mario", "nes", "snes"],
    description="复古像素艺术风格",
    prompt="Pixel art style, 16-bit retro game aesthetic, limited color palette, crisp pixels, no anti-aliasing, nostalgic video game art",
    style_instruction="""**PIXEL ART / RETRO GAME STYLE:**
- Classic 16-bit/32-bit era pixel art aesthetic
- Crisp, defined pixels with NO anti-aliasing or smoothing
- Limited color palette (16-64 colors maximum)
- Each pixel is intentionally placed
- Retro video game character design
- Dithering for gradients instead of smooth blending
- Isometric or orthographic perspective preferred
- ❌ DO NOT generate as: smooth, high-resolution, photorealistic
- ✅ MUST look like: Classic SNES/Genesis era game sprite""",
    enhancements=", pixel perfect, retro game quality, 16-bit aesthetic, crisp pixels, limited palette",
    negative_hints=["smooth", "anti-aliased", "high resolution", "photorealistic", "blurry", "gradient"],
    keywords=["pixel", "8bit", "16bit", "retro", "mario", "nes", "snes", "genesis", "sprite"]
))


# -----------------------------------------------------------------------------
# 5. Minecraft/体素风格 (Voxel)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="minecraft",
    aliases=["voxel", "blocky", "cube", "block-style"],
    description="Minecraft体素方块风格",
    prompt="Minecraft voxel style, blocky 3D aesthetic, cubic geometry, low-poly blocks, game-accurate textures, Minecraft character proportions",
    style_instruction="""**MINECRAFT / VOXEL BLOCK STYLE:**
- Everything made of cubic/block geometry
- Minecraft-accurate proportions (blocky body, rectangular limbs)
- Low-resolution textures on block surfaces (16x16 pixel textures)
- Sharp, geometric edges with no smoothing
- Limited, saturated color palette
- Characteristic Minecraft lighting and shadows
- Square/rectangular silhouettes only
- ❌ DO NOT generate as: smooth, organic curves, high-poly, realistic
- ✅ MUST look like: Official Minecraft game render""",
    enhancements=", voxel art, blocky design, Minecraft quality, cubic geometry, game-accurate",
    negative_hints=["smooth", "curved", "organic", "high-poly", "realistic", "round"],
    keywords=["minecraft", "voxel", "blocky", "cube", "block", "mojang"]
))


# -----------------------------------------------------------------------------
# 6. 橡皮泥/粘土风格 (Claymation)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="clay",
    aliases=["claymation", "plasticine", "play-doh", "stop-motion", "clay-style"],
    description="橡皮泥/粘土动画风格",
    prompt="Claymation style, plasticine texture, stop-motion aesthetic, handmade clay figure, fingerprint details, soft matte surface, warm tactile quality",
    style_instruction="""**CLAYMATION / PLASTICINE STYLE:**
- Authentic clay/plasticine material appearance
- Visible handmade texture with subtle fingerprint impressions
- Soft, matte surface with no reflections
- Slightly imperfect, organic shapes (not mathematically perfect)
- Rich, saturated colors typical of modeling clay
- Soft shadows and diffused lighting
- Stop-motion animation aesthetic
- Chunky, rounded proportions
- ❌ DO NOT generate as: smooth digital 3D, photorealistic, hard edges
- ✅ MUST look like: Wallace & Gromit or Shaun the Sheep quality""",
    enhancements=", clay texture, handmade quality, plasticine material, stop-motion aesthetic, tactile surface",
    negative_hints=["smooth", "digital", "hard edges", "photorealistic", "glossy", "plastic"],
    keywords=["clay", "claymation", "plasticine", "play-doh", "stop-motion", "wallace", "gromit"]
))


# -----------------------------------------------------------------------------
# 7. 毛绒玩偶风格 (Plush/Felt)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="plush",
    aliases=["felt", "stuffed", "plushie", "kawaii-plush", "soft-toy"],
    description="毛绒玩偶/布艺风格",
    prompt="Plush toy style, soft felt material, stuffed animal aesthetic, visible stitching, button eyes, fabric texture, kawaii plushie design",
    style_instruction="""**PLUSH TOY / FELT FABRIC STYLE:**
- Soft, fuzzy fabric texture (felt, fleece, or velvet)
- Visible stitching and seams as design elements
- Button eyes or embroidered facial features
- Stuffed, puffy 3D form with soft edges
- Warm, cuddly aesthetic
- Simplified, kawaii-inspired proportions
- Pastel or warm color palette
- Subtle fabric grain and texture
- ❌ DO NOT generate as: hard surface, plastic, realistic, detailed face
- ✅ MUST look like: High-quality handmade plush toy or Sanrio merchandise""",
    enhancements=", fabric texture, soft plush, felt material, kawaii design, stuffed toy quality",
    negative_hints=["hard", "plastic", "realistic", "detailed", "shiny", "metallic"],
    keywords=["plush", "felt", "stuffed", "plushie", "soft toy", "kawaii", "sanrio", "fabric"]
))


# -----------------------------------------------------------------------------
# 8. 纸片人/剪纸风格 (Paper/Flat)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="paper",
    aliases=["papercraft", "flat", "cutout", "paper-mario", "origami", "2.5d"],
    description="纸片人/剪纸风格",
    prompt="Paper cutout style, flat 2D character in 3D space, paper craft aesthetic, clean vector-like edges, layered paper depth, Paper Mario inspired",
    style_instruction="""**PAPER CUTOUT / PAPERCRAFT STYLE:**
- Flat, 2D character existing in 3D space
- Clean, vector-like edges as if cut from paper
- Visible paper texture and slight paper thickness
- Layered depth effect (like stacked paper cutouts)
- Bold, flat colors with minimal shading
- Paper Mario / Tearaway game aesthetic
- Characters appear as flat paper figures that can rotate
- Subtle paper grain texture
- ❌ DO NOT generate as: 3D modeled, realistic, rounded, organic
- ✅ MUST look like: Paper Mario or Paper craft art""",
    enhancements=", paper texture, flat design, clean edges, papercraft quality, layered depth",
    negative_hints=["3D", "rounded", "organic", "realistic", "smooth shading", "gradients"],
    keywords=["paper", "papercraft", "flat", "cutout", "paper mario", "origami", "tearaway", "2.5d"]
))


# -----------------------------------------------------------------------------
# 9. 赛博朋克风格 (Cyberpunk)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="cyberpunk",
    aliases=["cyber", "neon", "sci-fi", "futuristic", "synthwave"],
    description="赛博朋克霓虹风格",
    prompt="Cyberpunk style, neon lighting, futuristic sci-fi aesthetic, chrome and holographic materials, dystopian urban atmosphere, high-tech low-life",
    style_instruction="""**CYBERPUNK / NEON SCI-FI STYLE:**
- Intense neon lighting (pink, cyan, purple, orange)
- High contrast between dark shadows and bright neon
- Chrome, holographic, and reflective materials
- Futuristic cybernetic enhancements
- Urban dystopian atmosphere
- Tech-wear and augmented fashion
- Glitch effects and digital artifacts as style elements
- Rain-slicked surfaces with neon reflections
- ❌ DO NOT generate as: natural, bright daylight, fantasy, historical
- ✅ MUST look like: Blade Runner or Cyberpunk 2077 aesthetic""",
    enhancements=", neon lighting, cyberpunk aesthetic, high-tech details, futuristic quality, chrome reflections",
    negative_hints=["natural lighting", "daylight", "fantasy", "historical", "organic", "pastoral"],
    keywords=["cyberpunk", "cyber", "neon", "sci-fi", "futuristic", "synthwave", "blade runner"]
))


# -----------------------------------------------------------------------------
# 10. 奇幻风格 (Fantasy)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="fantasy",
    aliases=["medieval", "dnd", "rpg", "magic", "epic"],
    description="高奇幻/中世纪风格",
    prompt="High fantasy style, epic medieval aesthetic, magical atmosphere, detailed armor and fabric, dramatic lighting, RPG character art quality",
    style_instruction="""**HIGH FANTASY / MEDIEVAL STYLE:**
- Epic, dramatic fantasy atmosphere
- Detailed medieval-inspired clothing and armor
- Rich, jewel-tone color palette
- Magical elements with subtle glow effects
- Dramatic, painterly lighting
- RPG/TCG character art quality
- Intricate details on weapons, accessories
- Atmospheric depth and environmental storytelling
- ❌ DO NOT generate as: modern, sci-fi, cartoon, minimalist
- ✅ MUST look like: MTG card art or AAA fantasy game concept art""",
    enhancements=", fantasy art, epic quality, detailed armor, magical atmosphere, RPG character",
    negative_hints=["modern", "sci-fi", "cartoon", "minimalist", "simple", "contemporary"],
    keywords=["fantasy", "medieval", "dnd", "rpg", "magic", "epic", "sword", "dragon", "knight"]
))


# -----------------------------------------------------------------------------
# 11. 水彩风格 (Watercolor)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="watercolor",
    aliases=["watercolour", "aquarelle", "painted", "traditional"],
    description="传统水彩画风格",
    prompt="Watercolor painting style, soft wet-on-wet technique, visible brush strokes, paper texture, flowing color bleeds, traditional art aesthetic",
    style_instruction="""**WATERCOLOR / TRADITIONAL PAINTING STYLE:**
- Authentic watercolor painting aesthetic
- Soft, flowing color transitions with wet-on-wet technique
- Visible brush strokes and pigment granulation
- Paper texture showing through the paint
- Subtle color bleeds at edges
- Soft, diffused lighting
- Limited but harmonious color palette
- Loose, expressive quality
- ❌ DO NOT generate as: digital, vector, hard edges, photorealistic
- ✅ MUST look like: Traditional watercolor illustration""",
    enhancements=", watercolor texture, painted quality, soft edges, traditional art, paper grain",
    negative_hints=["digital", "vector", "hard edges", "photorealistic", "3D", "CGI"],
    keywords=["watercolor", "watercolour", "aquarelle", "painted", "traditional", "wet-on-wet"]
))


# -----------------------------------------------------------------------------
# 12. 油画风格 (Oil Painting)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="oil",
    aliases=["oil-painting", "classical", "renaissance", "baroque", "impasto"],
    description="古典油画风格",
    prompt="Oil painting style, classical art technique, visible impasto brush strokes, rich color depth, Renaissance/Baroque lighting, museum-quality fine art",
    style_instruction="""**OIL PAINTING / CLASSICAL ART STYLE:**
- Rich, layered oil paint texture
- Visible impasto brush strokes
- Classical chiaroscuro lighting
- Deep, saturated colors with subtle variations
- Renaissance or Baroque composition principles
- Canvas texture visible in paint
- Dramatic light and shadow interplay
- Museum-quality fine art aesthetic
- ❌ DO NOT generate as: digital, flat, cartoon, modern
- ✅ MUST look like: Classical masterpiece or concept art painting""",
    enhancements=", oil painting texture, classical quality, impasto strokes, rich colors, fine art",
    negative_hints=["digital", "flat", "cartoon", "modern", "minimalist", "simple"],
    keywords=["oil", "oil painting", "classical", "renaissance", "baroque", "impasto", "rembrandt"]
))


# -----------------------------------------------------------------------------
# 13. 3D卡通渲染 (3D Toon)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="3d-toon",
    aliases=["3d-cartoon", "pixar", "disney3d", "dreamworks", "cg-cartoon"],
    description="3D卡通渲染风格（皮克斯/迪士尼）",
    prompt="3D cartoon render, Pixar/Disney style, smooth subsurface scattering skin, stylized proportions, expressive eyes, cinematic lighting, high-quality CGI",
    style_instruction="""**3D CARTOON / PIXAR-DISNEY STYLE:**
- High-quality 3D CGI render with cartoon stylization
- Smooth subsurface scattering for skin
- Large, expressive eyes with detailed reflections
- Stylized but appealing proportions
- Rich, saturated color palette
- Cinematic lighting with rim lights
- Smooth, polished surfaces
- Expressive, animation-ready character design
- ❌ DO NOT generate as: 2D, photorealistic, anime, low-poly
- ✅ MUST look like: Pixar or Disney Animation Studios quality""",
    enhancements=", 3D render, Pixar quality, expressive design, cinematic lighting, CGI cartoon",
    negative_hints=["2D", "flat", "photorealistic", "anime", "low-poly", "realistic"],
    keywords=["3d cartoon", "pixar", "disney", "dreamworks", "cgi", "3d toon", "animated movie"]
))


# -----------------------------------------------------------------------------
# 14. 漫画风格 (Comic/Western)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="comic",
    aliases=["comics", "marvel", "dc", "superhero", "western-cartoon"],
    description="美漫/超级英雄漫画风格",
    prompt="American comic book style, bold ink outlines, Ben-Day dots, dynamic poses, superhero aesthetic, Marvel/DC art quality, dramatic shading",
    style_instruction="""**AMERICAN COMIC BOOK STYLE:**
- Bold, confident ink outlines
- Classic Ben-Day dot shading pattern
- Dramatic, dynamic poses and compositions
- High contrast with bold shadows
- Muscular, heroic proportions
- Vibrant, primary color palette
- Action-oriented visual storytelling
- Cross-hatching for texture and shadow
- ❌ DO NOT generate as: anime, photorealistic, soft, minimal
- ✅ MUST look like: Marvel or DC comic book panel art""",
    enhancements=", comic book art, bold lines, dynamic pose, superhero quality, ink style",
    negative_hints=["anime", "photorealistic", "soft", "minimal", "simple", "cute"],
    keywords=["comic", "comics", "marvel", "dc", "superhero", "american comic", "ink"]
))


# -----------------------------------------------------------------------------
# 15. 极简风格 (Minimalist)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="minimal",
    aliases=["minimalist", "simple", "clean", "flat-design", "vector"],
    description="极简/扁平设计风格",
    prompt="Minimalist design, flat vector style, limited color palette, clean geometric shapes, simple silhouettes, modern graphic design aesthetic",
    style_instruction="""**MINIMALIST / FLAT DESIGN STYLE:**
- Clean, geometric shapes with no unnecessary details
- Flat colors with no gradients or textures
- Limited color palette (3-5 colors maximum)
- Bold silhouettes and simple forms
- Modern graphic design aesthetic
- Negative space as design element
- No shadows or minimal shadow
- Vector-art quality with crisp edges
- ❌ DO NOT generate as: detailed, textured, realistic, complex
- ✅ MUST look like: Modern app icon or flat illustration""",
    enhancements=", minimalist design, flat colors, clean shapes, vector quality, simple",
    negative_hints=["detailed", "textured", "realistic", "complex", "gradient", "3D"],
    keywords=["minimal", "minimalist", "simple", "clean", "flat", "vector", "geometric"]
))


# -----------------------------------------------------------------------------
# 16. 低多边形风格 (Low Poly)
# -----------------------------------------------------------------------------
register_style(StylePreset(
    name="lowpoly",
    aliases=["low-poly", "polygon", "geometric-3d", "faceted"],
    description="低多边形3D风格",
    prompt="Low poly 3D style, faceted geometric surfaces, visible polygon edges, stylized lighting, modern game art aesthetic, clean geometric forms",
    style_instruction="""**LOW POLY / GEOMETRIC 3D STYLE:**
- Visible polygonal facets and geometric surfaces
- Sharp edges between polygon faces
- Flat shading on each polygon face
- Limited but harmonious color palette
- Modern indie game aesthetic
- Clean, geometric silhouettes
- Stylized lighting with hard shadows
- No texture maps, only vertex colors
- ❌ DO NOT generate as: smooth, high-poly, realistic, organic
- ✅ MUST look like: Monument Valley or modern indie game art""",
    enhancements=", low poly, geometric design, faceted surfaces, indie game quality, polygon art",
    negative_hints=["smooth", "high-poly", "realistic", "organic", "detailed", "textured"],
    keywords=["low poly", "lowpoly", "polygon", "geometric", "faceted", "indie game"]
))


# =============================================================================
# 风格查询和管理函数
# =============================================================================

def get_style_preset(name: str) -> Optional[StylePreset]:
    """
    根据名称获取风格预设
    
    Args:
        name: 风格名称或别名
    
    Returns:
        StylePreset 或 None
    """
    if not name:
        return None
    return STYLE_PRESETS.get(name.lower())


def find_matching_style(query: str) -> Optional[StylePreset]:
    """
    根据查询字符串查找匹配的风格
    
    Args:
        query: 查询字符串（可能包含风格关键词）
    
    Returns:
        匹配的 StylePreset 或 None
    """
    if not query:
        return None
    
    # 先尝试精确匹配
    preset = get_style_preset(query)
    if preset:
        return preset
    
    # 再尝试关键词匹配
    query_lower = query.lower()
    for name, preset in STYLE_PRESETS.items():
        if preset.matches(query_lower):
            return preset
    
    return None


def list_all_styles() -> List[str]:
    """获取所有唯一风格名称列表"""
    unique_styles = set()
    for preset in STYLE_PRESETS.values():
        unique_styles.add(preset.name)
    return sorted(unique_styles)


def get_style_help() -> str:
    """生成风格帮助文本"""
    lines = ["可用风格预设:"]
    seen = set()
    for preset in STYLE_PRESETS.values():
        if preset.name not in seen:
            aliases = ", ".join(preset.aliases[:3])  # 只显示前3个别名
            lines.append(f"  --{preset.name:<15} {preset.description} (别名: {aliases})")
            seen.add(preset.name)
    return "\n".join(lines)


# 导出
__all__ = [
    'StylePreset',
    'STYLE_PRESETS',
    'get_style_preset',
    'find_matching_style',
    'list_all_styles',
    'get_style_help',
]
