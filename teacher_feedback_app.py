import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px


# Function to fetch feedback from the database
def fetch_feedback():
    conn = sqlite3.connect("feedback.db")
    cursor = conn.cursor()

    # Query all rows from the feedback table
    cursor.execute("SELECT * FROM feedback ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()

    # Convert data to a pandas DataFrame
    feedback_df = pd.DataFrame(rows, columns=["ID", "Student Name", "Status", "Question", "Timestamp"])
    return feedback_df


# Function to fetch unanswered questions (Red feedback with questions)
def fetch_unanswered_questions():
    conn = sqlite3.connect("feedback.db")
    cursor = conn.cursor()

    # Query unanswered questions from "Red" feedback
    cursor.execute("""
        SELECT id, student_name, question, timestamp
        FROM feedback
        WHERE status = 'Red' AND question IS NOT NULL
        ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    # Convert to a pandas DataFrame
    questions_df = pd.DataFrame(rows, columns=["ID", "Student Name", "Question", "Timestamp"])
    return questions_df


# Teacher Dashboard Interface
st.title("Teacher Feedback Dashboard")

# "Refresh" Button (Triggers a rerun when clicked)
if st.button("Refresh"):
    # Clear session state to ensure fresh data is fetched.
    for key in st.session_state.keys():
        del st.session_state[key]

# Load all feedback data
if "feedback_data" not in st.session_state:
    st.session_state["feedback_data"] = fetch_feedback()

feedback_data = st.session_state["feedback_data"]

if feedback_data.empty:
    st.write("No feedback data available yet.")
else:
    # Feedback Summary
    st.subheader("Feedback Summary")

    # Aggregate feedback counts
    feedback_counts = feedback_data["Status"].value_counts().reset_index()
    feedback_counts.columns = ["Status", "Count"]

    # Display Pie Chart
    fig = px.pie(feedback_counts, values="Count", names="Status", title="Student Feedback Overview", color="Status",
                 color_discrete_map={"Green": "green", "Yellow": "yellow", "Red": "red"})
    st.plotly_chart(fig)

    # Display Questions (Pop-up Simulation for Unanswered Questions)
    st.subheader("Unanswered Questions")

    if "questions_data" not in st.session_state:
        st.session_state["questions_data"] = fetch_unanswered_questions()

    questions = st.session_state["questions_data"]

    if questions.empty:
        st.write("No unanswered questions.")
    else:
        for i, row in questions.iterrows():
            st.warning(f"New Question from {row['Student Name']} at {row['Timestamp']}:\n{row['Question']}")

    # All Questions Table
    st.subheader("All Questions from Students")
    red_feedback = feedback_data[feedback_data["Status"] == "Red"][["Student Name", "Question", "Timestamp"]]
    if not red_feedback.empty:
        st.table(red_feedback)
    else:
        st.write("No questions have been submitted yet.")
