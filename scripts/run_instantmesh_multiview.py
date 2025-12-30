#!/usr/bin/env python3
"""
Cortex3d Multi-View InstantMesh Runner
Takes 4 real multi-view images (front, back, left, right) and feeds them directly
to InstantMesh's LRM reconstruction model, bypassing the diffusion generation step.

Usage:
    python run_instantmesh_multiview.py <config> <image_folder_or_prefix> [options]
    
Example:
    python run_instantmesh_multiview.py configs/instant-mesh-large.yaml test_images/character_20251226_013442
"""

import os
import argparse
import sys
import numpy as np
import torch
from PIL import Image
from torchvision.transforms import v2
from pytorch_lightning import seed_everything
from omegaconf import OmegaConf
from tqdm import tqdm

# Add InstantMesh submodule to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
instantmesh_root = os.path.join(project_root, "InstantMesh")
sys.path.append(instantmesh_root)

from src.utils.train_util import instantiate_from_config
from src.utils.camera_util import (
    FOV_to_intrinsics, 
    spherical_camera_pose,
)
from src.utils.mesh_util import save_obj, save_obj_with_mtl


def get_4view_input_cameras(batch_size=1, radius=4.0, fov=30.0):
    """
    Get camera parameters for 4-view input (front, right, back, left).
    All cameras at 0 degree elevation, looking at origin.
    
    View order: [front, right, back, left]
    Azimuths:   [0,     90,    180,   270] degrees
    """
    azimuths = np.array([0, 90, 180, 270]).astype(float)
    elevations = np.array([0, 0, 0, 0]).astype(float)
    
    c2ws = spherical_camera_pose(azimuths, elevations, radius)
    c2ws = c2ws.float().flatten(-2)

    Ks = FOV_to_intrinsics(fov).unsqueeze(0).repeat(4, 1, 1).float().flatten(-2)

    extrinsics = c2ws[:, :12]
    intrinsics = torch.stack([Ks[:, 0], Ks[:, 4], Ks[:, 2], Ks[:, 5]], dim=-1)
    cameras = torch.cat([extrinsics, intrinsics], dim=-1)

    return cameras.unsqueeze(0).repeat(batch_size, 1, 1)


def load_and_preprocess_image(path, target_size=320):
    """Load an image and preprocess it for the model."""
    img = Image.open(path).convert('RGBA')
    
    # Create white background
    background = Image.new('RGBA', img.size, (255, 255, 255, 255))
    img = Image.alpha_composite(background, img).convert('RGB')
    
    # Resize to target size
    img = img.resize((target_size, target_size), Image.LANCZOS)
    
    # Convert to tensor
    img_np = np.asarray(img, dtype=np.float32) / 255.0
    img_tensor = torch.from_numpy(img_np).permute(2, 0, 1).contiguous().float()
    
    return img_tensor


def find_multiview_images(input_prefix):
    """
    Find 4 multi-view images based on input prefix.
    Looks for: {prefix}_front.png, {prefix}_back.png, {prefix}_left.png, {prefix}_right.png
    
    Returns dict: {'front': path, 'back': path, 'left': path, 'right': path}
    """
    views = ['front', 'right', 'back', 'left']  # Order matters for camera poses
    result = {}
    
    for view in views:
        for ext in ['.png', '.jpg', '.jpeg']:
            path = f"{input_prefix}_{view}{ext}"
            if os.path.exists(path):
                result[view] = path
                break
        
        if view not in result:
            raise FileNotFoundError(f"Missing view: {view}. Expected file like {input_prefix}_{view}.png")
    
    return result


###############################################################################
# Arguments
###############################################################################

parser = argparse.ArgumentParser(description="Multi-view InstantMesh reconstruction")
parser.add_argument('config', type=str, help='Path to config file.')
parser.add_argument('input_prefix', type=str, help='Prefix for multi-view images (e.g., test_images/character)')
parser.add_argument('--output_path', type=str, default='outputs/', help='Output directory.')
parser.add_argument('--seed', type=int, default=42, help='Random seed.')
parser.add_argument('--scale', type=float, default=1.0, help='Scale of generated object.')
parser.add_argument('--export_texmap', action='store_true', help='Export mesh with texture map.')
parser.add_argument('--texture_resolution', type=int, default=1024, help='Texture resolution.')

args = parser.parse_args()
seed_everything(args.seed)

###############################################################################
# Setup
###############################################################################

print("="*60)
print("Cortex3d Multi-View InstantMesh Reconstruction")
print("="*60)

config = OmegaConf.load(args.config)
config_name = os.path.basename(args.config).replace('.yaml', '')
model_config = config.model_config
infer_config = config.infer_config

if args.texture_resolution:
    infer_config.texture_resolution = args.texture_resolution

IS_FLEXICUBES = True if config_name.startswith('instant-mesh') else False
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[INFO] Using device: {device}")

# Find multi-view images
print(f"\n[INFO] Looking for multi-view images with prefix: {args.input_prefix}")
view_paths = find_multiview_images(args.input_prefix)
for view, path in view_paths.items():
    print(f"  - {view}: {path}")

# Load reconstruction model (skip diffusion pipeline entirely!)
print('\n[INFO] Loading reconstruction model (LRM)...')
model = instantiate_from_config(model_config)
if os.path.exists(infer_config.model_path):
    model_ckpt_path = infer_config.model_path
else:
    from huggingface_hub import hf_hub_download
    ckpt_filename = os.path.basename(infer_config.model_path)
    model_ckpt_path = hf_hub_download(repo_id="TencentARC/InstantMesh", filename=ckpt_filename, repo_type="model")

state_dict = torch.load(model_ckpt_path, map_location='cpu')['state_dict']
state_dict = {k[14:]: v for k, v in state_dict.items() if k.startswith('lrm_generator.')}
model.load_state_dict(state_dict, strict=True)
model = model.to(device)
if IS_FLEXICUBES:
    model.init_flexicubes_geometry(device, fovy=30.0)
model = model.eval()
print("[INFO] Model loaded successfully!")

# Create output directories
name = os.path.basename(args.input_prefix)
mesh_path = os.path.join(args.output_path, config_name + '-multiview', 'meshes')
os.makedirs(mesh_path, exist_ok=True)

###############################################################################
# Load and Process Images
###############################################################################

print("\n[INFO] Loading and preprocessing images...")
view_order = ['front', 'right', 'back', 'left']
images_list = []
for view in view_order:
    img_tensor = load_and_preprocess_image(view_paths[view])
    images_list.append(img_tensor)
    print(f"  - Loaded {view}: {img_tensor.shape}")

# Stack to (4, 3, 320, 320) then add batch dim -> (1, 4, 3, 320, 320)
images = torch.stack(images_list, dim=0).unsqueeze(0).to(device)
print(f"[INFO] Combined image tensor: {images.shape}")

# Get camera matrices for 4 views
input_cameras = get_4view_input_cameras(batch_size=1, radius=4.0 * args.scale).to(device)
print(f"[INFO] Camera matrices: {input_cameras.shape}")

###############################################################################
# Reconstruction
###############################################################################

print(f"\n[INFO] Running reconstruction for '{name}'...")

with torch.no_grad():
    # Get triplane features from images
    planes = model.forward_planes(images, input_cameras)
    
    # Extract mesh
    mesh_path_idx = os.path.join(mesh_path, f'{name}.obj')
    
    mesh_out = model.extract_mesh(
        planes,
        use_texture_map=args.export_texmap,
        **infer_config,
    )
    
    if args.export_texmap:
        vertices, faces, uvs, mesh_tex_idx, tex_map = mesh_out
        save_obj_with_mtl(
            vertices.data.cpu().numpy(),
            uvs.data.cpu().numpy(),
            faces.data.cpu().numpy(),
            mesh_tex_idx.data.cpu().numpy(),
            tex_map.permute(1, 2, 0).data.cpu().numpy(),
            mesh_path_idx,
        )
    else:
        vertices, faces, vertex_colors = mesh_out
        save_obj(vertices, faces, vertex_colors, mesh_path_idx)

print(f"\n{'='*60}")
print(f"[SUCCESS] Mesh saved to: {mesh_path_idx}")
print(f"{'='*60}")
