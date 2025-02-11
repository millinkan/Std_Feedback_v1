import streamlit as st
import sqlite3


# Function to insert feedback into the database
def insert_feedback(student_name, status, question):
    try:
        conn = sqlite3.connect("feedback.db")
        cursor = conn.cursor()

        # Insert the data into the feedback table
        cursor.execute("""
            INSERT INTO feedback (student_name, status, question)
            VALUES (?, ?, ?)
        """, (student_name, status, question))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"An error occurred while saving feedback: {e}")
    finally:
        conn.close()


# Student Feedback Interface
st.title("Student Feedback System")

# Input Name (Optional)
student_name = st.text_input("Enter your name (Optional):", "").strip()

# Initialize session state variables
if "feedback" not in st.session_state:
    st.session_state["feedback"] = None

if "question" not in st.session_state:
    st.session_state["question"] = ""

# Feedback Buttons
st.subheader("Click a button based on your understanding:")
col1, col2, col3 = st.columns(3)

# Capture feedback selection
if col1.button("🟢 Green - Confident"):
    st.session_state["feedback"] = "Green"
if col2.button("🟡 Yellow - Working Through Understanding"):
    st.session_state["feedback"] = "Yellow"
if col3.button("🔴 Red - Stop! I have a question"):
    st.session_state["feedback"] = "Red"

# Optional question field for "Red" feedback
if st.session_state["feedback"] == "Red":
    st.session_state["question"] = st.text_input(
        "Please enter your question:", st.session_state["question"]
    ).strip()

# Store feedback in the database
if st.session_state["feedback"]:
    # Validate question only for "Red" feedback
    if st.session_state["feedback"] == "Red" and not st.session_state["question"]:
        st.warning("Please provide a question if you selected 'Red - Stop! I have a question'")
    else:
        # Insert data into database and show success message
        insert_feedback(
            student_name or "Anonymous",
            st.session_state["feedback"],
            st.session_state["question"] if st.session_state["feedback"] == "Red" else None,
            )
        st.success("Your feedback has been submitted! Thank you for contributing.")

        # Reset session state after submission
        st.session_state["feedback"] = None
        st.session_state["question"] = ""