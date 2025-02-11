Install the streamlit and pandas

- Install all dependencies
  - - streamlit>=1.24.0
  - - pandas>=1.3.0  # Only if you need data analysis; otherwise, can omit

- Run dbcreate


Jaadi :
  -- I want to add an extra colum for a  course description
  -- Then :  Create a tables for all class / session with live feedbacks.
  -- Data Analyses on feedback can be done anytime.


After set up:

Run : streamlit run student_feedback_app.py --server.port 8501 for student app : https:localhost:8501
Run : streamlit run teacher_feedback_app.py --server.port 8502 for student app : https:localhost:8502

