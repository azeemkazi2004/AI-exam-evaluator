import streamlit as st
import pandas as pd
from PIL import Image
import numpy as np
import easyocr
import json
import os
import re
from groq import Groq

# ================= CONFIG =================
st.set_page_config(page_title="Unified AI Exam Evaluator", layout="wide")

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY not set.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# ================= TITLE =================
st.title("📝 Automated AI Exam Evaluator - AutoGrade AI")
st.markdown("---")

# ================= OCR =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

def extract_text(image_file):
    reader = load_reader()
    image = Image.open(image_file)
    image_np = np.array(image)
    results = reader.readtext(image_np, detail=0, paragraph=True)
    return " ".join(results)

# ================= PARSER =================
def parse_scores_and_feedback(text):
    results = []
    current_q = None
    for line in text.splitlines():
        score_match = re.search(r"Q(\d+)\s*:\s*([\d\.]+)\s*/\s*([\d\.]+)", line)
        if score_match:
            current_q = int(score_match.group(1))
            results.append({
                "Question": current_q,
                "Scored": float(score_match.group(2)),
                "Max": float(score_match.group(3)),
                "Feedback": ""
            })
        if current_q and line.lower().startswith("feedback"):
            results[-1]["Feedback"] = line.split(":", 1)[1].strip()
    return results

# ================= CSV GRADER =================
def grade_csv_answers(student_answers, answer_key_df):
    qa_block = ""
    for _, r in student_answers.iterrows():
        key = answer_key_df[answer_key_df["question_no"] == r["question_no"]].iloc[0]
        qa_block += f"""
Question {r['question_no']}:
Model Answer: {key['model_answer']}
Student Answer: {r['student_answer']}
Max Marks: {key['max_marks']}
"""

    prompt = f"""
You are a fair university examiner.
Give partial marks generously.

Return ONLY in this format:
Q1: x/marks
Feedback: short feedback

{qa_block}
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return completion.choices[0].message.content

# ================= IMAGE GRADER =================
def grade_image(answer_key_text, student_text, student_filename):
    prompt = f"""
You are an expert academic evaluator. Grade with partial marks.

ANSWER KEY:
{answer_key_text}

STUDENT ANSWER:
{student_text}

JSON FORMAT:
{{
 "answers":[
   {{"question":1,"marks":3,"max":5,"reason":"partial explanation"}}
 ]
}}
"""
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)

# ================= UI =================
left, right = st.columns(2)
with left:
    answer_key_file = st.file_uploader("📘 Upload Answer Key CSV", type="csv")
    student_files = st.file_uploader("🧑‍🎓 Upload Student Files", type=["csv", "jpg", "jpeg", "png"], accept_multiple_files=True)

# ================= PROCESS =================
if answer_key_file and student_files and st.button("⚡ Evaluate"):
    answer_key_df = pd.read_csv(answer_key_file)
    answer_key_df = answer_key_df[["question_no", "model_answer", "max_marks"]]
    answer_key_text = answer_key_df.to_csv(index=False)

    totals = []
    detailed_rows = []

    for file in student_files:
        filename = file.name

        # ===== CSV MODE =====
        if filename.endswith(".csv"):
            student_df = pd.read_csv(file)
            student_df.columns = ["student_name", "question_no", "student_answer"]
            students = student_df["student_name"].unique()

            for student in students:
                sa = student_df[student_df["student_name"] == student]
                output = grade_csv_answers(sa, answer_key_df)
                parsed = parse_scores_and_feedback(output)

                total_scored = sum(q["Scored"] for q in parsed)
                total_possible = sum(q["Max"] for q in parsed)

                for row in parsed:
                    detailed_rows.append({
                        "Student": student,
                        **row
                    })

                totals.append({
                    "Student": student,
                    "Total": round(total_scored, 2),
                    "Out Of": round(total_possible, 2),
                    "Percentage": round((total_scored / total_possible) * 100, 2)
                })

        # ===== IMAGE MODE =====
        else:
            extracted_text = extract_text(file)
            result_json = grade_image(answer_key_text, extracted_text, filename)
            answers = result_json.get("answers", [])

            total_marks = sum(a["marks"] for a in answers)
            max_possible = sum(a["max"] for a in answers)

            for a in answers:
                detailed_rows.append({
                    "Student": filename,
                    "Question": a["question"],
                    "Scored": a["marks"],
                    "Max": a["max"],
                    "Feedback": a["reason"]
                })

            totals.append({
                "Student": filename,
                "Total": round(total_marks, 2),
                "Out Of": round(max_possible, 2),
                "Percentage": round((total_marks / max_possible) * 100, 2)
            })

    totals_df = pd.DataFrame(totals)
    details_df = pd.DataFrame(detailed_rows)

    # ================= RESULTS =================
    st.subheader("🏆 Leaderboard")
    leaderboard = totals_df.sort_values("Percentage", ascending=False).reset_index(drop=True)
    leaderboard.index += 1
    st.dataframe(leaderboard, use_container_width=True)

    st.subheader("📝 Marks & Feedback Table")
    st.dataframe(details_df, use_container_width=True)

    st.subheader("📊 Analytics")
    st.bar_chart(totals_df.set_index("Student")["Percentage"])

    st.download_button("📥 Download Summary", totals_df.to_csv(index=False), "summary.csv")
    st.download_button("📥 Download Detailed Marks", details_df.to_csv(index=False), "detailed_marks.csv")

st.caption("Unified AI Evaluator | EasyOCR + Groq")
