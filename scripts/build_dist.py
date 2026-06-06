import os
import shutil
import subprocess
import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DIST_NAME = "Ruptura_Temporal_APOLO2.0"
DIST_EXE_NAME = "Ruptura_Temporal.exe"
LIGHT_RUNTIME_HOOK = "scripts/runtime_hooks/player_lite_phase4.py"

LIGHT_BUILD_EXCLUDES = [
    "GAME5",
    "GAME5_PLAYER",
    "apolo_brain",
    "habilidade_boss",
    "oratoria_umbra",
    "Ruptura_Temporal.GAME5",
    "Ruptura_Temporal.oratoria_umbra",
    "torch",
    "torchvision",
    "torchaudio",
    "torchgen",
    "triton",
]


def _exclude_args(modules):
    args = []
    for module in modules:
        args.extend(["--exclude-module", module])
    return args


def _run_pyinstaller(args, dry_run=False):
    command = ["pyinstaller", *args]
    print("Running:", " ".join(command))
    if dry_run:
        return
    subprocess.run(command, check=True)


def build(include_phase5=False, dry_run=False):
    os.chdir(PROJECT_ROOT)
    print("=== STARTING BUILD PROCESS ===")
    if include_phase5:
        print("Build profile: full package, includes GAME5/GAME5_PLAYER and PyTorch dependencies.")
    else:
        print("Build profile: player lite, phases 1-4 only. GAME5/GAME5_PLAYER/PyTorch are excluded.")
        print("Runtime cap: RUPTURA_MAX_PHASE=4 is injected into the executable.")
    
    # 1. Clean old builds
    dist_dir = os.path.abspath(f"dist/{DIST_NAME}")
    temp_dist_dir = os.path.abspath("dist/temp")
    
    for path in [dist_dir, temp_dist_dir, "build"]:
        if os.path.exists(path):
            print(f"Cleaning: {path}...")
            if not dry_run:
                shutil.rmtree(path, ignore_errors=True)
            
    if not dry_run:
        os.makedirs(dist_dir, exist_ok=True)
    
    # 2. Build Ruptura_Temporal.py
    print("\n--- Building Ruptura_Temporal.exe ---")
    main_args = [
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--distpath", "dist",
        "--name", DIST_NAME,
        "Ruptura_Temporal.py"
    ]
    if not include_phase5:
        main_args[-1:-1] = ["--runtime-hook", LIGHT_RUNTIME_HOOK, *_exclude_args(LIGHT_BUILD_EXCLUDES)]
    _run_pyinstaller(main_args, dry_run=dry_run)
    
    # Rename Ruptura_Temporal_APOLO2.0.exe to Ruptura_Temporal.exe.
    old_exe = os.path.join(dist_dir, f"{DIST_NAME}.exe")
    new_exe = os.path.join(dist_dir, DIST_EXE_NAME)
    if os.path.exists(old_exe) and not dry_run:
        import time
        for i in range(10):
            try:
                if os.path.exists(new_exe):
                    os.remove(new_exe)
                os.rename(old_exe, new_exe)
                print("Renamed executable to Ruptura_Temporal.exe")
                break
            except PermissionError:
                print(f"Waiting for file lock to release (attempt {i+1}/10)...")
                time.sleep(2)
        else:
            raise PermissionError(f"Could not rename {old_exe} to {new_exe} due to persistent lock.")
        
    # 3. Optional heavy phase 5 build.
    if include_phase5:
        print("\n--- Building GAME5_PLAYER.exe ---")
        _run_pyinstaller([
            "--noconfirm",
            "--onedir",
            "--windowed",
            "--distpath", "dist/temp",
            "--name", "GAME5_PLAYER",
            "GAME5_PLAYER.py"
        ], dry_run=dry_run)

        # Copy GAME5_PLAYER.exe to dist/Ruptura_Temporal_APOLO2.0/.
        src_player_exe = os.path.join(temp_dist_dir, "GAME5_PLAYER", "GAME5_PLAYER.exe")
        dest_player_exe = os.path.join(dist_dir, "GAME5_PLAYER.exe")
        if not dry_run:
            shutil.copy2(src_player_exe, dest_player_exe)
        print("Copied GAME5_PLAYER.exe to shared folder.")
    else:
        print("\n--- Skipping GAME5_PLAYER.exe (player lite build) ---")
    
    # 4. Copy Assets
    assets = ["Sprites", "Sounds", "Texto", "Video", "saves"]
    for asset in assets:
        if os.path.exists(asset):
            print(f"Copying asset folder: {asset}...")
            dest_asset_path = os.path.join(dist_dir, asset)
            if not dry_run:
                shutil.copytree(asset, dest_asset_path, dirs_exist_ok=True)
            
    # 5. Clean up temporary files
    print("\n--- Cleaning up temporary build files ---")
    if not dry_run:
        shutil.rmtree(temp_dist_dir, ignore_errors=True)
    if os.path.exists("build") and not dry_run:
        shutil.rmtree("build", ignore_errors=True)
        
    print("\n=== BUILD COMPLETED SUCCESSFULLY ===")
    print(f"Distribution folder ready at: {dist_dir}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build Ruptura Temporal distribution. Defaults to the light player package up to phase 4."
    )
    parser.add_argument(
        "--include-phase5",
        action="store_true",
        help="Build the old full package, including GAME5/GAME5_PLAYER and PyTorch."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print build commands without running PyInstaller or copying files."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build(include_phase5=args.include_phase5, dry_run=args.dry_run)
