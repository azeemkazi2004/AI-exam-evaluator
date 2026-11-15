# AI Exam Evaluator (AutoGrade AI)

🏆 **1st place – DSCE Generative & Agentic AI Hackathon 2026** (24 January 2026)

An AI-powered web app that grades student answers against a teacher's answer key. It accepts both **typed answers (CSV)** and **handwritten answer sheets (images)**, and returns marks plus short feedback for every answer.

## Problem

Manual correction of exam papers is slow, error-prone (wrong totals, skipped answers), inconsistent between evaluators, and leaves students with little feedback.

## How it works

```
Answer key (CSV) + student files (CSV or images)
        │
        ├── CSV file   → answers grouped per student
        └── Image file → EasyOCR extracts the handwritten text
        │
        ▼
Prompt built from the answer key + student answers
        │
        ▼
Llama 3.3 70B (via Groq) grades by meaning, not exact words
        │
        ▼
Marks + feedback per question → totals, percentage, leaderboard,
chart, CSV downloads (Streamlit)
```

- **Typed mode:** one prompt per student; the model replies `Q1: x/max` + `Feedback: ...`, which is parsed with a regex.
- **Handwritten mode:** EasyOCR reads the image; the OCR text and the full answer key are sent to the model in JSON mode, which returns marks, max and a reason for each question.
- Temperature is set to 0.1 for more consistent grading.

## Tech stack

| Area | Tools |
| --- | --- |
| Web app | Streamlit |
| OCR | EasyOCR, Pillow, NumPy |
| LLM | Llama 3.3 70B (`llama-3.3-70b-versatile`) via the Groq API |
| Data | pandas |
| Parsing | `json`, `re` |

## Input format

**Answer key CSV:** `question_no, model_answer, max_marks`

**Student answers CSV:** `student_name, question_no, student_answer`

**Images:** JPG / JPEG / PNG photos or scans of answer sheets (one sheet per student).

## Run locally

```bash
pip install -r requirements.txt
export GROQ_API_KEY="your_groq_api_key"    # Windows: set GROQ_API_KEY=your_groq_api_key
streamlit run evaluate_bot.py
```

A free API key is available from the Groq console.

## Limitations

- Handwriting OCR can be noisy, which affects grading accuracy.
- Diagrams, equations and graphs are not evaluated.
- No formal accuracy study against teacher marks yet.
- No retry or error handling for failed API calls.

## Future scope

- Per-question rubrics and stricter structured output for both modes
- OCR confidence checks with a teacher review step for unclear sheets
- Diagram and formula evaluation with vision models
- Multiple languages and handwriting styles
- Integration with learning management systems
