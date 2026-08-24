Factory Floor Optimizer
Quick Deployment & Execution Guide

1. Overview
Factory Floor Optimizer is a Streamlit-based Python application for industrial facility layout planning, workflow visualization, and preliminary spatial/compliance analysis. The application supports:
- 2D ASME-style blueprint rendering
- Interactive 3D factory viewport
- Machinery, conduit, lighting, and crane placement
- Workflow path configuration
- Layout import/export using JSON-formatted project files
- Basic analytics including bottleneck and clearance checks

2. Requirements
Install the following Python packages:
- streamlit
- matplotlib
- pandas
- numpy
- scipy
- plotly

Recommended install command:
pip install -r requirements.txt

3. Run the application locally
From the project root directory, launch:
streamlit run app.py

The application will typically be available at:
http://localhost:8501

4. Main project files
- app.py: main Streamlit application entry point
- engine.py: analytics and layout validation logic
- state_manager.py: session state initialization and import handling
- library_loader.py: default machinery, lighting, and crane libraries
- visualization.py: 2D and 3D rendering
- __init__compilation.py: compiled UI tab/component logic
- requirements.txt: Python dependencies

5. Current capabilities
- Place and edit machinery from a default library
- Route and edit conduit runs
- Place and edit lighting fixtures
- Place and edit overhead crane coverage areas
- Toggle drawing layers and analysis overlays
- Export current project layout to a JSON-formatted file
- Import previously saved layout files (.json or .txt containing JSON)

6. Current limitations
- No shared database or multi-user synchronization
- No authentication or role-based access control
- No full report package generation (PDF, drawing exports, safety reports)
- No full HVAC, water, drainage, or network utility analysis
- No formal forklift accessibility engine

7. Notes
This application currently functions as a prototype / engineering planning tool and should not be treated as a final regulatory or safety approval system without additional validation.
