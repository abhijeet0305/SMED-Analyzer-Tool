"""
SMED Studio - Standalone Offline Desktop Packaging Script
Uses PyInstaller to bundle SMED Studio into a 100% self-contained,
offline desktop application distribution in `dist/SMED_Studio/`.

Usage:
    python build_offline_app.py
    python build_offline_app.py --clean
    python build_offline_app.py --include-demo-videos
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path


def print_banner():
    banner = r"""
========================================================================
   ____  __  ________  ____     _____ __            ___      
  / __/ /  |/  / __/ _ \/ __/    / __// /___ _____/ (_)___ 
 _\ \  / /|_/ / _// // / _/     _\ \ / __/ // / _  / / _ \
/___/ /_/  /_/___/____/_/      /___/ \__/\_,_/\_,_/_/\___/ 
      STANDALONE OFFLINE DESKTOP PACKAGING ENGINE (PyInstaller)
========================================================================
"""
    print(banner)


def check_prerequisites(auto_install: bool = False) -> bool:
    """Check if PyInstaller and core dependencies are present."""
    print("[1/5] Checking build dependencies...")
    try:
        import PyInstaller
        print(f"      [OK] PyInstaller {PyInstaller.__version__} detected.")
        return True
    except ImportError:
        print("      [!] PyInstaller is not currently installed.")
        if auto_install:
            print("      --> Installing PyInstaller via pip...")
            res = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0"])
            return res.returncode == 0
        else:
            print("      To install PyInstaller, run:")
            print("          pip install pyinstaller")
            print("      Or re-run this script with: python build_offline_app.py --install")
            return False


def clean_build_artifacts():
    """Remove previous build and dist directories."""
    print("[2/5] Cleaning previous build cache...")
    workspace = Path(__file__).resolve().parent

    for folder_name in ["build", "dist"]:
        folder_path = workspace / folder_name
        if folder_path.exists():
            print(f"      Removing {folder_path}...")
            shutil.rmtree(folder_path, ignore_errors=True)

    spec_file = workspace / "SMED_Studio.spec"
    if spec_file.exists():
        try:
            os.remove(spec_file)
        except Exception:
            pass
    print("      [OK] Clean workspace ready.")


def prepare_demo_videos(include_videos: bool = True):
    """Ensure sample videos are generated so the standalone distribution is ready-to-demo."""
    if not include_videos:
        return
    print("[3/5] Preparing sample video assets for offline bundle...")
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_videos")
    before_vid = os.path.join(sample_dir, "before_trial_01.mp4")
    after_vid = os.path.join(sample_dir, "after_trial_01.mp4")

    if not os.path.exists(before_vid) or not os.path.exists(after_vid):
        print("      Generating synthetic demo videos (this takes ~3 seconds)...")
        try:
            from utils.demo_video_generator import generate_all_demo_videos
            generate_all_demo_videos(output_dir=sample_dir, duration_sec=10.0)
            print("      [OK] Synthetic demo videos generated.")
        except Exception as e:
            print(f"      [WARNING] Could not pre-generate demo videos: {e}")
    else:
        print("      [OK] Existing demo videos verified in sample_videos/.")


def run_pyinstaller(windowed: bool = True):
    """Assemble arguments and execute PyInstaller build."""
    print("[4/5] Running PyInstaller build engine...")
    workspace = os.path.abspath(os.path.dirname(__file__))
    main_script = os.path.join(workspace, "main.py")

    # Data separation character (: on Unix, ; on Windows)
    sep = ";" if sys.platform.startswith("win") else ":"

    # Hidden imports required for dynamic loading in PyQt6, OpenCV, Matplotlib, Pandas, ReportLab
    hidden_imports = [
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "cv2",
        "numpy",
        "matplotlib",
        "matplotlib.backends.backend_qtagg",
        "pandas",
        "openpyxl",
        "reportlab",
        "reportlab.lib",
        "reportlab.lib.colors",
        "reportlab.lib.pagesizes",
        "reportlab.lib.units",
        "reportlab.lib.styles",
        "reportlab.platypus",
        "sqlite3",
        "database",
        "database.db_manager",
        "database.seed_data",
        "ui",
        "ui.styles",
        "ui.project_tab",
        "ui.video_logger_tab",
        "ui.pareto_kaizen_tab",
        "ui.dashboard_tab",
        "utils",
        "utils.demo_video_generator",
        "utils.report_exporter",
    ]

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=SMED_Studio",
        "--onedir",
        "--clean",
        "--noconfirm",
    ]

    if windowed:
        args.append("--noconsole")  # Suppress console window (--noconsole flag)

    # Add hidden imports
    for imp in hidden_imports:
        args.append(f"--hidden-import={imp}")

    # Add sample_videos directory if present
    sample_dir = os.path.join(workspace, "sample_videos")
    if os.path.exists(sample_dir):
        args.append(f"--add-data={sample_dir}{sep}sample_videos")

    # Entry point
    args.append(main_script)

    print("      Executing command:")
    print("      " + " ".join(args[:8]) + " ...")

    result = subprocess.run(args, cwd=workspace)
    return result.returncode == 0


def verify_distribution():
    """Verify that the output executable and runtime dependencies were created."""
    print("[5/5] Verifying distribution package...")
    workspace = Path(__file__).resolve().parent
    dist_dir = workspace / "dist" / "SMED_Studio"

    exe_name = "SMED_Studio.exe" if sys.platform.startswith("win") else "SMED_Studio"
    exe_path = dist_dir / exe_name

    if not exe_path.exists():
        print(f"      [FAILED] Output executable was not found at: {exe_path}")
        return False

    total_bytes = sum(f.stat().st_size for f in dist_dir.glob("**/*") if f.is_file())
    mb = total_bytes / (1024 * 1024)

    print("========================================================================")
    print("   STANDALONE OFFLINE BUILD SUCCESSFUL!")
    print("========================================================================")
    print(f"   Distribution Directory: {dist_dir}")
    print(f"   Application Executable: {exe_path}")
    print(f"   Total Package Size:     {mb:.1f} MB")
    print("\n   To launch the standalone app:")
    if sys.platform.startswith("win"):
        print(f"       .\\dist\\SMED_Studio\\SMED_Studio.exe")
    else:
        print(f"       ./dist/SMED_Studio/SMED_Studio")
    print("========================================================================")
    return True


def main():
    parser = argparse.ArgumentParser(description="Package SMED Studio into standalone offline application.")
    parser.add_argument("--install", action="store_true", help="Auto-install PyInstaller if missing.")
    parser.add_argument("--clean-only", action="store_true", help="Only clean build folders and exit.")
    parser.add_argument("--console", action="store_true", help="Keep console window open (for debugging).")
    parser.add_argument("--no-videos", action="store_true", help="Do not pre-generate demo videos.")

    args = parser.parse_args()
    print_banner()

    if args.clean_only:
        clean_build_artifacts()
        print("Clean complete. Exiting.")
        return 0

    if not check_prerequisites(auto_install=args.install):
        print("\nBuild aborted: missing PyInstaller.")
        return 1

    clean_build_artifacts()
    prepare_demo_videos(include_videos=not args.no_videos)

    success = run_pyinstaller(windowed=not args.console)
    if not success:
        print("\n[ERROR] PyInstaller build failed. Check terminal output above.")
        return 1

    if verify_distribution():
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
