🛠️ 3. Quick Deployment & Execution Guide
Follow the layout sequence table below to set up and compile the optimization dashboard locally on your system:

Phase	Description	Command / Action
Phase 1	Install system dependencies	pip install streamlit pandas matplotlib
Phase 2	Save source code files	Save Robert's C-code as optimizer.c and Samantha's GUI script as app.py in the same directory.
Phase 3	Manual Compilation (Optional)	gcc optimizer.c -o optimizer -lm (On Windows, output is optimizer.exe)
Phase 4	Launch the local web server	streamlit run app.py
Phase 5	Interact and Export	Adjust sliders in your browser at http://localhost:8501, click optimization run, and download the finalized layout coordinates as a CSV spreadsheet.