/* Imtihan SPA — auth, exams, take-exam, results, analytics. */
'use strict';

const API = '';
let state = { token: null, user: null, exams: [], currentExam: null, detailExamId: null, taking: null, questionDraft: [] };

// ---------- helpers ----------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers['Authorization'] = 'Bearer ' + state.token;
  const res = await fetch(API + path, { ...opts, headers });
  let body = null;
  try { body = await res.json(); } catch { /* no body */ }
  if (!res.ok) {
    const msg = body && body.detail
      ? (typeof body.detail === 'string' ? body.detail : 'Validation error')
      : 'Something went wrong';
    throw new Error(msg);
  }
  return body;
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s ?? '';
  return d.innerHTML;
}

function show(view) {
  $$('.nav-tab').forEach((t) => t.classList.toggle('active', t.dataset.view === view));
  $('#exams-view').classList.toggle('hidden', view !== 'exams');
  $('#results-view').classList.toggle('hidden', view !== 'results');
  $('#analytics-view').classList.toggle('hidden', view !== 'analytics');
}

// ---------- auth ----------
function applyAuthUI() {
  const isTeacher = state.user?.role === 'teacher';
  $$('.teacher-only').forEach((el) => el.classList.toggle('hidden', !isTeacher));
  $$('.student-only').forEach((el) => el.classList.toggle('hidden', isTeacher));
  if (state.user) {
    $('#user-chip').textContent = state.user.name + ' · ' + (isTeacher ? 'Teacher' : 'Student');
  }
}

async function doAuth(e) {
  e.preventDefault();
  const isRegister = $('#auth-form').dataset.mode === 'register';
  const payload = { email: $('#email').value.trim(), password: $('#password').value };
  if (isRegister) {
    payload.name = $('#name').value.trim();
    payload.role = $('#role').value;
  }
  try {
    const data = await api('/api/auth/' + (isRegister ? 'register' : 'login'), {
      method: 'POST', body: JSON.stringify(payload),
    });
    state.token = data.access_token;
    state.user = data.user;
    $('#auth-error').textContent = '';
    enterApp();
  } catch (err) { $('#auth-error').textContent = err.message; }
}

function enterApp() {
  $('#auth-view').classList.add('hidden');
  $('#main-view').classList.remove('hidden');
  applyAuthUI();
  loadExams();
}

function logout() {
  state = { token: null, user: null, exams: [], currentExam: null, taking: null, questionDraft: [] };
  $('#main-view').classList.add('hidden');
  $('#auth-view').classList.remove('hidden');
  setAuthMode('login');
}

// ---------- exams ----------
async function loadExams() {
  try {
    const exams = await api('/api/exams');
    state.exams = exams;
    renderExamList(exams);
  } catch (err) { $('#join-error').textContent = err.message; }
}

function renderExamList(exams) {
  const box = $('#exam-list');
  if (!exams.length) {
    box.innerHTML = '<div class="card muted" style="text-align:center;padding:30px">No exams yet.</div>';
    return;
  }
  box.innerHTML = exams.map((x) => `
    <div class="exam-card" data-id="${x.id}">
      <div class="title">${esc(x.title)}</div>
      <div class="meta">
        <span class="badge subject">${esc(x.subject)}</span>
        <span>${x.question_count} questions</span>
        <span>${x.duration_minutes} min</span>
        <span>${esc(x.description || '')}</span>
      </div>
    </div>`).join('');
  $$('#exam-list .exam-card').forEach((card) => card.addEventListener('click', () => openExam(Number(card.dataset.id))));
}

async function openExam(id) {
  const isTeacher = state.user.role === 'teacher';
  if (isTeacher) {
    const exam = await api('/api/exams/' + id);
    showExamDetail(exam);
  } else {
    const exam = state.exams.find((x) => x.id === id);
    if (exam) showTakeExam(exam);
  }
}

// ---------- teacher: builder ----------
let editingQuestions = [];
function showBuilder() {
  $('#exam-builder').classList.remove('hidden');
  $('#exam-title').value = ''; $('#exam-subject').value = 'General';
  $('#exam-duration').value = 30; $('#exam-negative').value = 0.25;
  editingQuestions = [blankQuestion()];
  renderBuilderQuestions();
  $('#builder-error').textContent = '';
  $('#exam-builder').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function hideBuilder() { $('#exam-builder').classList.add('hidden'); }
function blankQuestion() {
  return { text: '', marks: 1, options: [
    { text: '', is_correct: true }, { text: '', is_correct: false },
    { text: '', is_correct: false }, { text: '', is_correct: false },
  ] };
}
function renderBuilderQuestions() {
  const box = $('#question-list');
  box.innerHTML = editingQuestions.map((q, qi) => `
    <div class="q-block" data-qi="${qi}">
      <div class="q-head">
        <span class="q-num">Q${qi + 1}</span>
        <span>marks: <input type="number" value="${q.marks}" min="0.5" max="100" step="0.5" style="width:70px;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:5px;color:var(--text);text-align:center" data-role="marks" /></span>
        <button class="rm-btn" data-role="rmq" title="Remove question">✕</button>
      </div>
      <input type="text" value="${esc(q.text)}" placeholder="Question text…" data-role="qtext" />
      ${q.options.map((o, oi) => `
        <div class="opt-row">
          <input type="text" value="${esc(o.text)}" placeholder="Option ${oi + 1}" data-role="otext" data-oi="${oi}" />
          <label><input type="radio" name="correct-${qi}" data-role="correct" data-oi="${oi}" ${o.is_correct ? 'checked' : ''} /> correct</label>
          <button class="rm-btn" data-role="rmo" data-oi="${oi}" title="Remove option">✕</button>
        </div>`).join('')}
    </div>`).join('');

  box.querySelectorAll('[data-role="qtext"]').forEach((inp) => {
    inp.addEventListener('input', () => editingQuestions[Number(inp.closest('.q-block').dataset.qi)].text = inp.value);
  });
  box.querySelectorAll('[data-role="marks"]').forEach((inp) => {
    inp.addEventListener('input', () => editingQuestions[Number(inp.closest('.q-block').dataset.qi)].marks = Number(inp.value) || 1);
  });
  box.querySelectorAll('[data-role="otext"]').forEach((inp) => {
    const qi = Number(inp.closest('.q-block').dataset.qi);
    editingQuestions[qi].options[Number(inp.dataset.oi)].text = inp.value;
  });
  box.querySelectorAll('[data-role="correct"]').forEach((inp) => {
    const qi = Number(inp.closest('.q-block').dataset.qi);
    inp.addEventListener('change', () => {
      editingQuestions[qi].options.forEach((o, oi) => o.is_correct = oi === Number(inp.dataset.oi));
    });
  });
  box.querySelectorAll('[data-role="rmo"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const qi = Number(btn.closest('.q-block').dataset.qi);
      const q = editingQuestions[qi];
      if (q.options.length <= 2) return;
      const oi = Number(btn.dataset.oi);
      q.options.splice(oi, 1);
      if (q.options.every((o) => !o.is_correct)) q.options[0].is_correct = true;
      renderBuilderQuestions();
    });
  });
  box.querySelectorAll('[data-role="rmq"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (editingQuestions.length <= 1) return;
      editingQuestions.splice(Number(btn.closest('.q-block').dataset.qi), 1);
      renderBuilderQuestions();
    });
  });
}

async function saveExam() {
  const questions = editingQuestions.map((q) => ({
    text: q.text.trim(), marks: q.marks,
    options: q.options.map((o) => ({ text: o.text.trim(), is_correct: o.is_correct })),
  }));
  if (questions.some((q) => !q.text)) { $('#builder-error').textContent = 'Every question needs text.'; return; }
  if (questions.some((q) => q.options.some((o) => !o.text))) { $('#builder-error').textContent = 'Every option needs text.'; return; }
  if (questions.some((q) => !q.options.some((o) => o.is_correct))) { $('#builder-error').textContent = 'Every question needs one correct option.'; return; }
  try {
    await api('/api/exams', {
      method: 'POST',
      body: JSON.stringify({
        title: $('#exam-title').value.trim(),
        subject: $('#exam-subject').value.trim() || 'General',
        description: '',
        duration_minutes: Number($('#exam-duration').value) || 30,
        negative_marking: Number($('#exam-negative').value) || 0,
        questions,
      }),
    });
    hideBuilder();
    loadExams();
  } catch (err) { $('#builder-error').textContent = err.message; }
}

// ---------- teacher: exam detail + codes + submissions ----------
function showExamDetail(exam) {
  state.detailExamId = exam.id;
  $('#exam-list').classList.add('hidden');
  $('#exam-detail').classList.remove('hidden');
  $('#detail-title').textContent = exam.title;
  $('#detail-meta').textContent = `${exam.subject} · ${exam.question_count} questions · ${exam.duration_minutes} min · negative ${exam.negative_marking}`;
  $('#codes-list').innerHTML = '<div class="muted" style="font-size:.82rem">Loading…</div>';
  $('#subs-list').innerHTML = '<div class="muted" style="font-size:.82rem">Loading…</div>';
  loadCodes(exam.id);
  loadSubs(exam.id);
}
async function loadCodes(examId) {
  try {
    const codes = await api(`/api/exams/${examId}/codes`);
    $('#codes-list').innerHTML = codes.length
      ? codes.map((c) => `<div class="code-chip">${esc(c.code)}<small>${c.used_count}/${c.max_uses} used</small></div>`).join('')
      : '<div class="muted" style="font-size:.82rem">No codes yet — generate one below.</div>';
  } catch (err) { $('#codes-list').innerHTML = `<div class="error">${esc(err.message)}</div>`; }
}
async function loadSubs(examId) {
  try {
    const subs = await api(`/api/submissions/exam/${examId}`);
    $('#subs-list').innerHTML = subs.length ? `
      <table><thead><tr><th>Student</th><th>Score</th><th>%</th><th>Status</th></tr></thead>
      <tbody>${subs.map((s) => `
        <tr>
          <td>${esc(s.student_name)}</td>
          <td>${s.score}/${s.max_score}</td>
          <td>${s.percentage}%</td>
          <td><span class="pill ${s.percentage >= 40 ? 'pass' : 'fail'}">${s.percentage >= 40 ? 'Pass' : 'Fail'}</span></td>
        </tr>`).join('')}</tbody></table>`
      : '<div class="muted" style="font-size:.82rem">No submissions yet.</div>';
  } catch (err) { $('#subs-list').innerHTML = `<div class="error">${esc(err.message)}</div>`; }
}
async function genCode() {
  if (!state.detailExamId) return;
  try {
    await api(`/api/exams/${state.detailExamId}/codes`, { method: 'POST', body: JSON.stringify({ max_uses: 100 }) });
    loadCodes(state.detailExamId);
  } catch (err) { alert(err.message); }
}

// ---------- student: take exam ----------
function showTakeExam(exam) {
  state.taking = exam;
  $('#exam-list').classList.add('hidden');
  $('#take-exam').classList.remove('hidden');
  $('#take-title').textContent = exam.title;
  $('#take-meta').textContent = `${exam.subject} · ${exam.question_count} questions · ${exam.duration_minutes} min · negative ${exam.negative_marking} per wrong answer`;
  $('#take-questions').innerHTML = exam.questions.map((q, qi) => `
    <div class="tq" data-qid="${q.id}">
      <div class="q-text">${qi + 1}. ${esc(q.text)} <span class="q-marks">(${q.marks} marks)</span></div>
      ${q.options.map((o) => `
        <label class="option">
          <input type="radio" name="q${q.id}" value="${o.id}" />
          <span>${esc(o.text)}</span>
        </label>`).join('')}
    </div>`).join('');
  $('#take-error').textContent = '';
}
async function submitExam() {
  const exam = state.taking;
  const answers = exam.questions.map((q) => {
    const sel = document.querySelector(`input[name="q${q.id}"]:checked`);
    return { question_id: q.id, option_id: sel ? Number(sel.value) : null };
  });
  try {
    const res = await api('/api/submissions', {
      method: 'POST',
      body: JSON.stringify({ code: state.joinCode, answers }),
    });
    $('#take-exam').classList.add('hidden');
    showResult(res);
    loadExams();
  } catch (err) { $('#take-error').textContent = err.message; }
}

// ---------- student: join ----------
async function joinExam() {
  const code = $(''join-code').value.trim().toUpperCase();
  if (!code) return;
  try {
    const exam = await api('/api/exams/join', { method: 'POST', body: JSON.stringify({ code }) });
    state.joinCode = code;
    $('#join-error').textContent = '';
    $('#exam-list').classList.add('hidden');
    showTakeExam(exam);
  } catch (err) { $('#join-error').textContent = err.message; }
}

// ---------- results ----------
function showResult(r) {
  $('#results-view').classList.remove('hidden');
  show('results');
  const pct = r.percentage;
  $('#result-card').classList.remove('hidden');
  $('#result-card').innerHTML = `
    <div class="result-hero">
      <div class="result-score">${pct}%</div>
      <div class="result-pct ${r.passed ? 'pass' : 'fail'}">${r.passed ? 'Passed 🎉' : 'Failed'}</div>
      <div class="muted" style="margin-top:4px">${esc(r.exam_title)}</div>
    </div>
    <div class="stat-grid">
      <div class="stat-box"><div class="num">${r.score}</div><div class="lbl">Score</div></div>
      <div class="stat-box"><div class="num">${r.max_score}</div><div class="lbl">Max</div></div>
      <div class="stat-box"><div class="num" style="color:var(--green)">${r.correct_count}</div><div class="lbl">Correct</div></div>
      <div class="stat-box"><div class="num" style="color:var(--red)">${r.wrong_count}</div><div class="lbl">Wrong</div></div>
      <div class="stat-box"><div class="num" style="color:var(--muted)">${r.skipped_count}</div><div class="lbl">Skipped</div></div>
      <div class="stat-box"><div class="num">${r.submitted_at ? new Date(r.submitted_at).toLocaleString() : '—'}</div><div class="lbl">Submitted</div></div>
    </div>`;
  loadMyResults();
}
async function loadMyResults() {
  try {
    const subs = await api('/api/submissions/my');
    $('#results-list').innerHTML = subs.length ? subs.map((s) => `
      <div class="exam-card">
        <div class="title">${esc(s.exam_title)}</div>
        <div class="meta">
          <span>${s.score}/${s.max_score}</span>
          <span>${s.percentage}%</span>
          <span class="pill ${s.percentage >= 40 ? 'pass' : 'fail'}">${s.percentage >= 40 ? 'Pass' : 'Fail'}</span>
          <span>${s.submitted_at ? new Date(s.submitted_at).toLocaleDateString() : ''}</span>
        </div>
      </div>`).join('') : '<div class="card muted" style="text-align:center;padding:24px">No results yet — take an exam!</div>';
  } catch { /* ignore */ }
}

// ---------- analytics ----------
async function loadAnalytics() {
  try {
    const exams = await api('/api/exams');
    const overview = await api('/api/analytics/overview');
    $('#analytics-overview').innerHTML = `
      <div class="stat-card"><div class="num">${overview.exam_count}</div><div class="lbl">Exams</div></div>
      <div class="stat-card"><div class="num">${overview.submission_count}</div><div class="lbl">Submissions</div></div>
      <div class="stat-card"><div class="num">${overview.average_percentage}%</div><div class="lbl">Avg score</div></div>`;

    const detail = $('#analytics-detail');
    if (!exams.length) { detail.innerHTML = '<div class="card muted" style="text-align:center;padding:24px">Create an exam to see analytics.</div>'; return; }

    let html = '';
    for (const ex of exams) {
      const a = await api(`/api/analytics/exam/${ex.id}`);
      html += `<div class="card">
        <h3>${esc(a.exam_title)} <span class="muted" style="font-weight:400;font-size:.85rem">· ${a.total_submissions} submissions · avg ${a.average_score} · pass rate ${a.pass_rate}%</span></h3>
        ${a.question_stats.map((q) => {
          const color = q.accuracy >= 70 ? 'good' : q.accuracy >= 40 ? 'mid' : 'low';
          return `<div class="q-stat">
            <div class="q-text">${esc(q.text)} <span class="muted" style="font-weight:400;font-size:.78rem">· ${q.attempts} attempts · ${q.correct}✓ ${q.wrong}✗ ${q.skipped}—</span></div>
            <div style="display:flex;justify-content:space-between;font-size:.75rem"><span class="muted">accuracy</span><strong>${q.accuracy}%</strong></div>
            <div class="bar"><div class="bar-fill ${color}" style="width:${q.accuracy}%"></div></div>
          </div>`;
        }).join('') || '<div class="muted" style="font-size:.85rem">No submissions yet.</div>'}
      </div>`;
    }
    detail.innerHTML = html;
  } catch (err) { $('#analytics-detail').innerHTML = `<div class="error">${esc(err.message)}</div>`; }
}

// ---------- nav wiring ----------
function setAuthMode(mode) {
  $('#auth-form').dataset.mode = mode;
  $('#auth-submit').textContent = mode === 'register' ? 'Create account' : 'Login';
  $('#name-field').classList.toggle('hidden', mode !== 'register');
  $('#role-field').classList.toggle('hidden', mode !== 'register');
  $('#auth-error').textContent = '';
}

function init() {
  // Show the auth view on first load
  $('#auth-view').classList.remove('hidden');
  setAuthMode('login');

  $$('.tab-btn').forEach((btn) => btn.addEventListener('click', () => {
    $$('.tab-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    setAuthMode(btn.dataset.tab);
  }));

  $('#auth-form').addEventListener('submit', doAuth);
  $('#logout-btn').addEventListener('click', logout);

  $$('.nav-tab').forEach((t) => t.addEventListener('click', () => {
    show(t.dataset.view);
    if (t.dataset.view === 'analytics') loadAnalytics();
    if (t.dataset.view === 'results') loadMyResults();
  }));

  $('#new-exam-btn').addEventListener('click', showBuilder);
  $('#add-question-btn').addEventListener('click', () => { editingQuestions.push(blankQuestion()); renderBuilderQuestions(); });
  $('#save-exam-btn').addEventListener('click', saveExam);
  $('#cancel-exam-btn').addEventListener('click', hideBuilder);
  $('#back-btn').addEvntNistener('click', () => {
    $('#exam-detail').classList.add('hidden');
    $('#take-exam').classList.add('hidden');
    $('#exam-list').classList.remove('hidden');
    loadExams();
  });
  $('#gen-code-btn').addEventListener('click', genCode);
  $('#join-btn').addEventListener('click', joinExam);
  $('#submit-exam-btn').addEventListener('click', submitExam);

  // Enter key on join code
  $('#join-code').addEventListener('keydown', (e) => { if (e.key === 'Enter') joinExam(); });
}

init();
