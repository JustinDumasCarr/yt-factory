# GUI later

We keep the pipeline backend stable so GUI is a thin wrapper.

## Recommended GUI approach
FastAPI server later:
- list projects
- show project.json status
- show logs
- buttons to run steps
- audio preview list

Alternative quick GUI:
Streamlit app that reads project folders and triggers steps.

Key rule:
GUI must call the same pipeline functions.
Do not re-implement logic in the GUI layer.
