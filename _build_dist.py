import os
import shutil
import subprocess

def build():
    print("=== STARTING BUILD PROCESS ===")
    
    # 1. Clean old builds
    dist_dir = os.path.abspath("dist/Ruptura_Temporal_APOLO2.0")
    temp_dist_dir = os.path.abspath("dist/temp")
    
    for path in [dist_dir, temp_dist_dir, "build"]:
        if os.path.exists(path):
            print(f"Cleaning: {path}...")
            shutil.rmtree(path, ignore_errors=True)
            
    os.makedirs(dist_dir, exist_ok=True)
    
    # 2. Build Ruptura_Temporal.py
    print("\n--- Building Ruptura_Temporal.exe ---")
    subprocess.run([
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--distpath", "dist",
        "--name", "Ruptura_Temporal_APOLO2.0",
        "Ruptura_Temporal.py"
    ], check=True)
    
    # Rename Ruptura_Temporal_APOLO2.0.exe to Ruptura_Temporal.exe
    old_exe = os.path.join(dist_dir, "Ruptura_Temporal_APOLO2.0.exe")
    new_exe = os.path.join(dist_dir, "Ruptura_Temporal.exe")
    if os.path.exists(old_exe):
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
        
    # 3. Build GAME5_PLAYER.py in a temp directory to reuse _internal
    print("\n--- Building GAME5_PLAYER.exe ---")
    subprocess.run([
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--distpath", "dist/temp",
        "--name", "GAME5_PLAYER",
        "GAME5_PLAYER.py"
    ], check=True)
    
    # Copy GAME5_PLAYER.exe to dist/Ruptura_Temporal_APOLO2.0/
    src_player_exe = os.path.join(temp_dist_dir, "GAME5_PLAYER", "GAME5_PLAYER.exe")
    dest_player_exe = os.path.join(dist_dir, "GAME5_PLAYER.exe")
    shutil.copy2(src_player_exe, dest_player_exe)
    print("Copied GAME5_PLAYER.exe to shared folder.")
    
    # 4. Copy Assets
    assets = ["Sprites", "Sounds", "Texto", "Video", "saves"]
    for asset in assets:
        if os.path.exists(asset):
            print(f"Copying asset folder: {asset}...")
            dest_asset_path = os.path.join(dist_dir, asset)
            shutil.copytree(asset, dest_asset_path, dirs_exist_ok=True)
            
    # 5. Clean up temporary files
    print("\n--- Cleaning up temporary build files ---")
    shutil.rmtree(temp_dist_dir, ignore_errors=True)
    if os.path.exists("build"):
        shutil.rmtree("build", ignore_errors=True)
        
    print("\n=== BUILD COMPLETED SUCCESSFULLY ===")
    print(f"Distribution folder ready at: {dist_dir}")

if __name__ == "__main__":
    build()
