import os
import subprocess
import sys

def main():
    print("==================================================")
    print("       FACTORY FLOOR OPTIMIZER SYSTEM STARTUP     ")
    print("==================================================")
    
    print("\n[1/3] Attempting C Optimizer Backend Compilation...")
    backend_dir = os.path.join("factory_floor_optimizer", "backend")
    if os.path.exists(backend_dir):
        try:
            res = subprocess.run(["gcc", "--version"], capture_output=True, text=True)
            if res.returncode == 0:
                print(" -> GCC toolchain located. Compiling native libraries...")
                make_res = subprocess.run(["make", "-C", backend_dir], capture_output=True, text=True)
                if make_res.returncode == 0:
                    print(" -> SUCCESS: compiled liboptimizer.so!")
                else:
                    print(f" -> Compilation error: {make_res.stderr}")
                    print(" -> Fallback: C backend not compiled. Pure Python will be used.")
            else:
                print(" -> GCC not active. Fallback: Python simulation logic will run.")
        except Exception as e:
            print(" -> Fallback: Python simulation logic will run.")
    else:
        print(" -> ERROR: Backend directory not found!")
        sys.exit(1)
        
    print("\n[2/3] Checking dependencies...")
    try:
        import reportlab
        print(" -> ReportLab available. PDF Layout Exporter is active.")
    except ImportError:
        print(" -> WARNING: 'reportlab' is missing. Please run: pip install reportlab")

    print("\n[3/3] Launching Factory Floor Optimizer Web Service...")
    app_path = os.path.join("factory_floor_optimizer", "app.py")
    if os.path.exists(app_path):
        print(" -> Starting local HTTP server on http://localhost:8000")
        print("-" * 50)
        try:
            subprocess.run(["python", app_path])
        except KeyboardInterrupt:
            print("\nServer shutdown requested by user.")
    else:
        print(f" -> ERROR: app.py not found at {app_path}!")
        sys.exit(1)

if __name__ == "__main__":
    main()
