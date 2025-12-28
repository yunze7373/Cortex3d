import argparse
import logging
import os
import sys
import time

import numpy as np
import rembg
import torch
import xatlas
import trimesh
from PIL import Image

# Add TripoSR submodule to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
triposr_root = os.path.join(project_root, "TripoSR")
sys.path.append(triposr_root)

# Now import from tsr
from tsr.utils import scale_tensor
import moderngl
# Monkeypatch moderngl to force EGL backend for headless rendering
_original_create_context = moderngl.create_context
def patched_create_context(**kwargs):
    kwargs['backend'] = 'egl'
    return _original_create_context(**kwargs)
moderngl.create_context = patched_create_context

# Import tsr modules to patch
import tsr.bake_texture
from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground, save_video
from tsr.bake_texture import bake_texture

# Monkeypatch positions_to_colors to fix device mismatch (CPU vs CUDA)
def patched_positions_to_colors(model, scene_code, positions_texture, texture_resolution):
    device = scene_code.device
    positions = torch.tensor(positions_texture.reshape(-1, 4)[:, :-1], dtype=torch.float32, device=device)
    with torch.no_grad():
        queried_grid = model.renderer.query_triplane(
            model.decoder,
            positions,
            scene_code,
        )
    rgb_f = queried_grid["color"].cpu().numpy().reshape(-1, 3)
    rgba_f = np.insert(rgb_f, 3, positions_texture.reshape(-1, 4)[:, -1], axis=1)
    rgba_f[rgba_f[:, -1] == 0.0] = [0, 0, 0, 0]
    return rgba_f.reshape(texture_resolution, texture_resolution, 4)

tsr.bake_texture.positions_to_colors = patched_positions_to_colors

class PatchedTSR(TSR):
    def extract_mesh(self, scene_codes, has_vertex_color, resolution: int = 256, threshold: float = 25.0):
        self.set_marching_cubes_resolution(resolution)
        meshes = []
        for scene_code in scene_codes:
            # Chunk strategy for density query to avoid OOM
            grid_vertices = self.isosurface_helper.grid_vertices
            chunk_size = 65536 * 4  # ~260k points per chunk
            densities = []
            num_points = grid_vertices.shape[0]
            
            logging.info(f"Querying density field in chunks (Total points: {num_points}, Chunk size: {chunk_size})...")
            
            for i in range(0, num_points, chunk_size):
                chunk = grid_vertices[i:i+chunk_size].to(scene_code.device)
                scaled_chunk = scale_tensor(
                    chunk,
                    self.isosurface_helper.points_range,
                    (-self.renderer.cfg.radius, self.renderer.cfg.radius),
                )
                with torch.no_grad():
                    density_chunk = self.renderer.query_triplane(
                        self.decoder,
                        scaled_chunk,
                        scene_code,
                    )["density_act"]
                densities.append(density_chunk.cpu())
                
            density = torch.cat(densities, dim=0)
    
            v_pos, t_pos_idx = self.isosurface_helper(-(density - threshold))
            
            v_pos = scale_tensor(
                v_pos,
                self.isosurface_helper.points_range,
                (-self.renderer.cfg.radius, self.renderer.cfg.radius),
            )
    
            color = None
            if has_vertex_color:
                num_v_points = v_pos.shape[0]
                logging.info(f"Querying color field in chunks (Total vertices: {num_v_points})...")
                colors = []
                for i in range(0, num_v_points, chunk_size):
                    chunk_v = v_pos[i:i+chunk_size].to(scene_code.device)
                    with torch.no_grad():
                        color_chunk = self.renderer.query_triplane(
                            self.decoder,
                            chunk_v,
                            scene_code,
                        )["color"]
                    colors.append(color_chunk.cpu())
                color = torch.cat(colors, dim=0)
    
            mesh = trimesh.Trimesh(
                vertices=v_pos.cpu().numpy(),
                faces=t_pos_idx.cpu().numpy(),
                vertex_colors=color.cpu().numpy() if has_vertex_color else None,
            )
            meshes.append(mesh)
        return meshes


class Timer:
    def __init__(self):
        self.items = {}
        self.time_scale = 1000.0  # ms
        self.time_unit = "ms"

    def start(self, name: str) -> None:
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        self.items[name] = time.time()
        logging.info(f"{name} ...")

    def end(self, name: str) -> float:
        if name not in self.items:
            return
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        start_time = self.items.pop(name)
        delta = time.time() - start_time
        t = delta * self.time_scale
        logging.info(f"{name} finished in {t:.2f}{self.time_unit}.")


timer = Timer()
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=str, nargs="+", help="Path to input image(s).")
    parser.add_argument(
        "--device",
        default="cuda:0",
        type=str,
        help="Device to use. Default: 'cuda:0'",
    )
    parser.add_argument(
        "--pretrained-model-name-or-path",
        default="stabilityai/TripoSR",
        type=str,
        help="Path to pretrained model. Default: 'stabilityai/TripoSR'",
    )
    parser.add_argument(
        "--chunk-size",
        default=8192,
        type=int,
        help="Evaluation chunk size. Default: 8192",
    )
    parser.add_argument(
        "--mc-resolution",
        default=256,
        type=int,
        help="Marching cubes grid resolution. Default: 256"
    )
    parser.add_argument(
        "--no-remove-bg",
        action="store_true",
        help="Skip background removal. Default: false",
    )
    parser.add_argument(
        "--foreground-ratio",
        default=0.95,
        type=float,
        help="Ratio of foreground size. Default: 0.95",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/triposr",
        type=str,
        help="Output directory. Default: 'outputs/triposr'",
    )
    parser.add_argument(
        "--model-save-format",
        default="obj",
        type=str,
        choices=["obj", "glb"],
        help="Format to save the mesh. Default: 'obj'",
    )
    parser.add_argument(
        "--bake-texture",
        action="store_true",
        help="Bake texture atlas instead of vertex colors",
    )
    parser.add_argument(
        "--texture-resolution",
        default=2048,
        type=int,
        help="Texture atlas resolution. Default: 2048"
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Save NeRF-rendered video. Default: false",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    device = args.device
    if not torch.cuda.is_available():
        device = "cpu"

    timer.start("Initializing model")
    model = PatchedTSR.from_pretrained(
        args.pretrained_model_name_or_path,
        config_name="config.yaml",
        weight_name="model.ckpt",
    )
    model.renderer.set_chunk_size(args.chunk_size)
    model.to(device)
    timer.end("Initializing model")

    timer.start("Processing images")
    
    if args.no_remove_bg:
        rembg_session = None
    else:
        rembg_session = rembg.new_session()

    for i, image_path in enumerate(args.image):
        name = os.path.basename(image_path).split('.')[0]
        logging.info(f"Processing {name} ({image_path})...")
        
        save_dir = os.path.join(output_dir, name)
        os.makedirs(save_dir, exist_ok=True)

        # Smart background processing logic (similar to InstantMesh)
        # But here we stick to TripoSR's flow but assume files might be transparent already
        
        input_pil = Image.open(image_path)
        
        # Check alpha
        has_alpha = False
        if input_pil.mode == 'RGBA':
             if input_pil.getextrema()[-1][0] < 255:
                 has_alpha = True
        
        should_rembg = (not args.no_remove_bg) and (not has_alpha)
        
        if should_rembg:
             logging.info("Removing background...")
             image = remove_background(input_pil, rembg_session)
             image = resize_foreground(image, args.foreground_ratio)
        else:
             if has_alpha:
                 logging.info("Alpha channel detected, resizing foreground only...")
                 image = resize_foreground(input_pil, args.foreground_ratio)
             else:
                 logging.info("Using image as-is (no-remove-bg or opaque)...")
                 image = input_pil.convert("RGB")
        
        # Preprocess for model (white bg + float)
        image = np.array(image).astype(np.float32) / 255.0
        if image.shape[2] == 4:
            # Alpha blend with white
            image = image[:, :, :3] * image[:, :, 3:4] + (1 - image[:, :, 3:4]) * 0.5
        image = Image.fromarray((image * 255.0).astype(np.uint8))
        
        # Save input reference
        image.save(os.path.join(save_dir, "input.png"))

        timer.start(f"Running inference for {name}")
        scene_codes = model(image, device=device)
        timer.end(f"Running inference for {name}")

        if args.render:
            timer.start(f"Rendering video for {name}")
            render_images = model.render(scene_codes, n_views=30, return_type="pil")
            save_video(
                render_images, os.path.join(save_dir, f"render.mp4"), fps=30
            )
            timer.end(f"Rendering video for {name}")

        timer.start(f"Extracting mesh for {name}")
        # Note: TripoSR run.py passes `not args.bake_texture` as `has_vertex_color` arg?
        # Let's check: meshes = model.extract_mesh(scene_codes, not args.bake_texture, resolution=args.mc_resolution)
        # So if baking texture, we set has_vertex_color=False to save time? Or is it required?
        # Actually, bake_texture takes `mesh` which needs UVs? No, bake_texture does UV unwrapping?
        # Let's follow reference: `meshes = model.extract_mesh(scene_codes, not args.bake_texture, resolution=args.mc_resolution)`
        meshes = model.extract_mesh(scene_codes, has_vertex_color=not args.bake_texture, resolution=args.mc_resolution)
        timer.end(f"Extracting mesh for {name}")

        # Smooth the mesh using Taubin smoothing (preserves volume/details better than Laplacian)
        logging.info("Applying Taubin smoothing (Volume Preserving)...")
        try:
            trimesh.smoothing.filter_taubin(meshes[0], iterations=10)
        except AttributeError:
            # Fallback if filter_taubin is missing in old trimesh versions
            logging.warning("Taubin smoothing not found, falling back to Laplacian...")
            trimesh.smoothing.filter_laplacian(meshes[0], iterations=3)

        out_mesh_path = os.path.join(save_dir, f"{name}.{args.model_save_format}")

        if args.bake_texture:
            out_texture_path = os.path.join(save_dir, f"{name}_texture.png")
            timer.start(f"Baking texture for {name}")
            bake_output = bake_texture(meshes[0], model, scene_codes[0], args.texture_resolution)
            timer.end(f"Baking texture for {name}")

            timer.end(f"Baking texture for {name}")

            # Scale model to real-world size (e.g. 100mm height)
            # TripoSR outputs normalized coordinates approx [-0.5, 0.5]
            # Slicers usually treat 1 unit = 1mm. So 1 unit height = 1mm (too small).
            # We scale it to 100mm (10cm) standard figure height.
            target_height = 100.0
            
            # Calculate current height
            vs = meshes[0].vertices
            ymin, ymax = vs[:, 1].min(), vs[:, 1].max()
            current_height = ymax - ymin
            if current_height > 0:
                scale_factor = target_height / current_height
                logging.info(f"Scaling model by {scale_factor:.2f} to reach {target_height}mm height")
                # Scale vertices
                meshes[0].vertices *= scale_factor
            
            timer.start("Exporting mesh and texture")
            # Note: We use the SCALED vertices for export
            xatlas.export(
                out_mesh_path, 
                meshes[0].vertices[bake_output["vmapping"]], 
                bake_output["indices"], 
                bake_output["uvs"], 
                meshes[0].vertex_normals[bake_output["vmapping"]]
            )
            Image.fromarray((bake_output["colors"] * 255.0).astype(np.uint8)).transpose(Image.FLIP_TOP_BOTTOM).save(out_texture_path)
            timer.end("Exporting mesh and texture")
            logging.info(f"Mesh and texture saved to {out_mesh_path}")
        else:
            # Scale for non-textured export too
            target_height = 100.0
            vs = meshes[0].vertices
            ymin, ymax = vs[:, 1].min(), vs[:, 1].max()
            current_height = ymax - ymin
            if current_height > 0:
                scale_factor = target_height / current_height
                meshes[0].vertices *= scale_factor

            timer.start(f"Exporting mesh for {name}")
            meshes[0].export(out_mesh_path)
            timer.end(f"Exporting mesh for {name}")
            logging.info(f"Mesh saved to {out_mesh_path}")

if __name__ == "__main__":
    main()
