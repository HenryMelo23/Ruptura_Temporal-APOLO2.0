import os
import shutil
import subprocess
import argparse
import struct
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DIST_NAME = "Ruptura_Temporal_APOLO2.0"
DIST_EXE_NAME = "Ruptura_Temporal.exe"
LIGHT_RUNTIME_HOOK = "scripts/runtime_hooks/player_lite_phase4.py"
VLC_RUNTIME_HOOK = "scripts/runtime_hooks/vlc_path.py"
SOURCE_MODULE_DIRS = ["Fases", "Manifestacoes", "Aureas", "Rede", "Boss", "Menus", "Engine"]

REQUIRED_RUNTIME_MODULES = [
    "ancorada_manifestacao",
    "condutora_manifestacao",
    "gravitante_manifestacao",
    "insana_aurea",
    "lacerante_manifestacao",
    "parasitica_manifestacao",
    "prismatica_manifestacao",
    "retornante_manifestacao",
    "teleporte_manifestacao",
    "voraz_aurea",
]

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


def _hidden_import_args(modules):
    args = []
    for module in modules:
        args.extend(["--hidden-import", module])
    return args


def _source_path_args():
    args = []
    for directory in SOURCE_MODULE_DIRS:
        source_path = PROJECT_ROOT / directory
        if source_path.is_dir():
            args.extend(["--paths", str(source_path)])
    return args


def _verify_required_runtime_modules(modules):
    missing = []
    search_roots = [PROJECT_ROOT] + [PROJECT_ROOT / directory for directory in SOURCE_MODULE_DIRS]
    for module in modules:
        relative_module = module.replace(".", os.sep)
        found = any(
            (root / f"{relative_module}.py").is_file()
            or (root / relative_module / "__init__.py").is_file()
            for root in search_roots
        )
        if not found:
            missing.append(module)
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(
            f"Required runtime module(s) missing before build: {joined}. "
            "The executable would crash on another PC if this build continued."
        )


def _pe_machine(path):
    try:
        with open(path, "rb") as f:
            if f.read(2) != b"MZ":
                return None
            f.seek(0x3C)
            pe_offset = struct.unpack("<I", f.read(4))[0]
            f.seek(pe_offset)
            if f.read(4) != b"PE\0\0":
                return None
            return struct.unpack("<H", f.read(2))[0]
    except OSError:
        return None


def _python_machine():
    return 0x8664 if sys.maxsize > 2 ** 32 else 0x014C


def _same_arch_vlc(vlc_dir):
    dll_path = vlc_dir / "libvlc.dll"
    machine = _pe_machine(dll_path)
    return machine is not None and machine == _python_machine()


def _vlc_candidates(vlc_dir_override=None):
    seen = set()
    if vlc_dir_override:
        path = Path(vlc_dir_override)
        seen.add(str(path).lower())
        yield path
    env_dir = os.environ.get("RUPTURA_VLC_DIR")
    if env_dir and env_dir != vlc_dir_override:
        path = Path(env_dir)
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            yield path
    for value in (
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
    ):
        path = Path(value)
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            yield path


def _find_vlc_runtime(vlc_dir_override=None):
    for vlc_dir in _vlc_candidates(vlc_dir_override):
        if not vlc_dir.exists():
            continue
        if not (vlc_dir / "libvlc.dll").exists() or not (vlc_dir / "libvlccore.dll").exists():
            continue
        if not _same_arch_vlc(vlc_dir):
            print(f"WARNING: VLC found but skipped due to architecture mismatch: {vlc_dir}")
            continue
        plugins_dir = vlc_dir / "plugins"
        if not plugins_dir.exists():
            print(f"WARNING: VLC found without plugins folder, skipped: {vlc_dir}")
            continue
        return vlc_dir
    return None


def _add_binary_arg(src, dest="."):
    return ["--add-binary", f"{src}{os.pathsep}{dest}"]


def _add_data_arg(src, dest):
    return ["--add-data", f"{src}{os.pathsep}{dest}"]


def _vlc_pyinstaller_args(vlc_dir):
    if not vlc_dir:
        return []
    args = []
    args.extend(_add_binary_arg(vlc_dir / "libvlc.dll"))
    args.extend(_add_binary_arg(vlc_dir / "libvlccore.dll"))
    args.extend(_add_data_arg(vlc_dir / "plugins", "plugins"))
    return args


def _run_pyinstaller(args, dry_run=False):
    command = ["pyinstaller", *args]
    print("Running:", " ".join(command))
    if dry_run:
        return
    subprocess.run(command, check=True)


def build(include_phase5=False, dry_run=False, vlc_dir=None):
    os.chdir(PROJECT_ROOT)
    print("=== STARTING BUILD PROCESS ===")
    if include_phase5:
        print("Build profile: full package, includes GAME5/GAME5_PLAYER and PyTorch dependencies.")
    else:
        print("Build profile: player lite, phases 1-4 only. GAME5/GAME5_PLAYER/PyTorch are excluded.")
        print("Runtime cap: RUPTURA_MAX_PHASE=4 is injected into the executable.")

    vlc_dir = _find_vlc_runtime(vlc_dir)
    if vlc_dir:
        print(f"VLC runtime bundled from: {vlc_dir}")
    else:
        print("WARNING: Compatible VLC runtime not found. Trailer playback will be skipped on PCs without VLC.")

    _verify_required_runtime_modules(REQUIRED_RUNTIME_MODULES)
    
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
        "--runtime-hook", VLC_RUNTIME_HOOK,
        "--distpath", "dist",
        "--name", DIST_NAME,
        *_source_path_args(),
        *_hidden_import_args(REQUIRED_RUNTIME_MODULES),
        *_vlc_pyinstaller_args(vlc_dir),
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
            "--runtime-hook", VLC_RUNTIME_HOOK,
            "--distpath", "dist/temp",
            "--name", "GAME5_PLAYER",
            *_source_path_args(),
            *_hidden_import_args(REQUIRED_RUNTIME_MODULES),
            *_vlc_pyinstaller_args(vlc_dir),
            os.path.join("Fases", "GAME5_PLAYER.py")
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
    parser.add_argument(
        "--vlc-dir",
        default=None,
        help="Optional path to a VLC folder containing libvlc.dll, libvlccore.dll and plugins."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build(include_phase5=args.include_phase5, dry_run=args.dry_run, vlc_dir=args.vlc_dir)
