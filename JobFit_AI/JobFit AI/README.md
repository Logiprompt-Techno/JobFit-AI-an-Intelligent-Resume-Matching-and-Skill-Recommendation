# JobFit AI – Intelligent Resume-Based Job Matching & Skill Recommendation Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0%2B-green.svg)](https://www.djangoproject.com/)
[![NLP](https://img.shields.io/badge/NLP-spaCy%20%7C%20Sentence--Transformers-cyan.svg)](https://spacy.io/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**JobFit AI** is an intelligent, open-source web application built with **Django** and modern **NLP (Natural Language Processing)** techniques to parse resumes, extract skills and candidate information, compute semantic job-fit scores, and recommend targeted certifications for skill gaps.

---

## 🌟 Key Features

- 📄 **Resume Parsing (PDF/DOCX):** Automatically extracts raw text, candidate contact information (name, email, phone), work experience, and educational background.
- 🏷️ **Rule-Based Skill Extraction:** Uses spaCy's `PhraseMatcher` combined with a curated skills taxonomy dataset to detect technical and soft skills.
- 💼 **Job Description Management:** Full job management (Create, Read, Update, Delete) allowing hiring managers to post job requirement criteria.
- 📊 **Semantic Similarity & Match Scoring:** Combines Sentence-BERT (`all-MiniLM-L6-v2`) vector embeddings and skill overlap ratios to calculate transparent match percentages (0–100%).
- 💡 **Skill Gap & Recommendation Engine:** Identifies missing required skills for specific roles and provides a mapped roadmap to recognized industry certifications.
- 🎨 **Modern Dark Navy & Tech Cyan Theme:** Responsive, modern user interface built with HTML5, CSS3 design tokens, Bootstrap 5, and client-side JavaScript.
- 🧪 **Automated Testing:** 100% automated test suite with 16 unit and integration test cases using Django's test framework.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Django 5.0+ |
| **Frontend** | HTML5, Vanilla CSS3, Bootstrap 5.3, JavaScript |
| **Database** | SQLite3 |
| **Resume Parsing** | `pdfplumber`, `PyMuPDF (fitz)`, `python-docx` |
| **NLP – NER & Extraction** | `spaCy` (`en_core_web_sm` / `spacy.blank("en")`) |
| **NLP – Semantic Embedding** | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| **Similarity & Metrics** | `scikit-learn` (Cosine Similarity & TF-IDF backup) |
| **Testing** | Django `TestCase` & `Client` |

---

## 📁 Project Architecture & Folder Structure

```
JobFit AI/
│
├── manage.py                          # Django CLI management script
├── requirements.txt                   # Project dependencies
├── README.md                          # Documentation
├── db.sqlite3                         # SQLite database file
│
├── config/                            # Project configuration package
│   ├── settings.py                    # Django configuration settings
│   ├── urls.py                        # Root URL routing
│   ├── wsgi.py                        # WSGI entry point
│   └── asgi.py                        # ASGI entry point
│
├── matching_app/                      # Main Django application
│   ├── models.py                      # Resume, Job, MatchResult models
│   ├── views.py                       # HTTP views for uploads, jobs, matching, recommendations
│   ├── forms.py                       # ResumeUploadForm & JobForm
│   ├── urls.py                        # App URL routes
│   ├── admin.py                       # Django admin model registration
│   ├── tests.py                       # 16 Unit & Integration test cases
│   │
│   ├── services/                      # NLP processing layer
│   │   ├── resume_parser.py           # Text extraction from PDF & DOCX
│   │   ├── info_extractor.py          # Candidate NER extraction (name, email, phone, etc.)
│   │   ├── skill_extractor.py         # spaCy PhraseMatcher skill extraction
│   │   ├── embedding_engine.py        # Sentence-BERT embeddings & similarity scoring
│   │   ├── matcher.py                 # Hybrid match percentage calculation
│   │   └── skill_recommender.py       # Missing skill gap certification mapping
│   │
│   ├── data/                          # Reference datasets
│   │   ├── skills_taxonomy.csv        # Skill names & categories reference
│   │   └── certifications_map.csv     # Skill-to-certification mappings
│   │
│   ├── management/commands/           # Management commands
│   │   └── seed_demo_data.py          # Seed command for sample job postings
│   │
│   ├── templates/matching_app/        # HTML templates
│   │   ├── base.html                  # Master layout
│   │   ├── home.html                  # Landing page
│   │   ├── upload_resume.html         # Resume upload page
│   │   ├── resume_list.html           # Resumes directory
│   │   ├── resume_detail.html         # Candidate detail page
│   │   ├── job_list.html              # Job postings directory
│   │   ├── job_form.html              # Post / Edit job form
│   │   ├── job_detail.html            # Job description view
│   │   ├── match_results.html         # Ranked job fit results
│   │   └── recommendations.html       # Skill gap certification recommendations
│   │
│   └── static/matching_app/           # Static assets
│       ├── css/
│       │   └── style.css              # Custom Dark Navy & Tech Cyan stylesheet
│       └── js/
│           └── script.js              # Client-side validation & UI scripts
│
└── media/
    └── resumes/                       # User-uploaded resume files
```

---

## ⚡ Quick Start & Setup Instructions

### 1. Prerequisites
- Python 3.10 or higher installed.
- Git (optional).

### 2. Clone / Open Project Directory
Navigate to the project root directory in your shell:
```powershell
cd "c:\JobFit AI"
```

### 3. Activate Virtual Environment
Activate the pre-configured virtual environment:
```powershell
venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
If installing into a fresh environment:
```powershell
pip install -r requirements.txt
```

### 5. Run Database Migrations
Create SQLite tables for `Resume`, `Job`, and `MatchResult`:
```powershell
python manage.py migrate
```

### 6. Seed Sample Job Data
Populate the database with realistic sample job postings for immediate testing:
```powershell
python manage.py seed_demo_data
```

### 7. Start the Development Server
Run Django's development server:
```powershell
python manage.py runserver
```
Open your browser and visit: **`http://127.0.0.1:8000/`**

---

## 🧪 Running Automated Tests

To execute the full Django test suite (16 automated tests covering Models, Forms, Services, and Views):

```powershell
python manage.py test
```

Expected Output:
```
Found 16 test(s).
System check identified no issues (0 silenced).
................
----------------------------------------------------------------------
Ran 16 tests in ~13s

OK
```

---

## 📖 Usage Guide

1. **Upload Resume:** Navigate to **Upload Resume**, select a sample `.pdf` or `.docx` resume, and click **Upload and Process Resume**.
2. **View Candidate Details:** Inspect extracted candidate details, contact information, detected skill badges, and parsed work history.
3. **Run Job Matching:** Click **Run Job Match** on any candidate profile to view all active job postings ranked by match percentage (0–100%).
4. **Analyze Skill Gaps:** Click **View Skill Recommendations** to see missing skill badges alongside suggested industry certifications.
5. **Manage Jobs:** Navigate to **Jobs** → **Post Job** to add new job postings with custom required skills.

---

## 📄 License

This project is licensed under the MIT License - free for academic, personal, and commercial use.
