# ATS Resume Analyzer & Scorer

An intelligent Applicant Tracking System (ATS) that evaluates resumes against job descriptions. Built with FastAPI and Streamlit, the system analyzes skill compatibility, keyword density, formatting, and overall relevance using Groq API and fine-tuned models.

## Features

- **Automated Resume Scoring:** Evaluates candidates based on keyword matching, formatting, content quality, and skill validation.
- **AI-Powered Analysis:** Integrates Groq API and sentence transformers for semantic comparison between resume content and job descriptions.
- **Database Storage:** Uses Supabase for storing candidate evaluations and history.
- **Interactive UI:** Features a Streamlit frontend with score visualizers and actionable improvement recommendations.

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Frontend:** Streamlit
- **AI / NLP:** Groq API, Sentence Transformers, PyTorch
- **Database:** Supabase
