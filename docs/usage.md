# Usage Guide

Imtihan has two roles: **teacher** and **student**. Here's how each side works.

## Teacher

### 1. Register & log in
- Pick role **teacher** at registration. You'll get a JWT immediately (stored in the browser for the session).

### 2. Create an exam
- Go to **Exams → New Exam**.
- Give it a title, subject, duration (minutes), and negative marking fraction (e.g. `0.25` = −0.25 marks per wrong answer).
- Add questions. Each question needs 2–6 options and **at least one correct option** (the API enforces this).
- Save. The exam now appears in your list.

### 3. Generate a join code
- Open the exam → **Codes** → **Generate code**.
- Set max uses (how many students can join with it) — default 100. Codes expire after 30 days.
- Share the 8-character code with your class (WhatsApp, board, whatever works).

### 4. Watch results & analytics
- Open the exam → **Submissions** → see every student's score, percentage, pass/fail.
- Open **Analytics** → average/highest/lowest score, pass rate, and a per-question breakdown showing how many students got each question right, wrong, or skipped it. **The question with the lowest accuracy is what you should re-teach next class.**

## Student

### 1. Register & log in
- Pick role **student**.

### 2. Join an exam
- Enter the code your teacher gave you (join codes are case-insensitive).
- The exam opens with all questions and options — **correct answers are never shown**.

### 3. Submit
- Pick an option per question (leave blank to skip).
- Submit. You get an instant result: score, max score, percentage, correct/wrong/skipped counts, pass/fail (40% pass mark), and a per-answer breakdown.
- One submission per exam per student — retakes return 409.

## Tips

- **Negative marking**: set it to `0` for practice quizzes, `0.25`–`0.5` for real tests where guessing should cost something.
- **Capacity control**: generate a fresh code per class/section so `used_count` stays meaningful.
- **Duration**: the backend stores `duration_minutes` — the UI shows it; enforce hard timeouts in a future version if needed.
