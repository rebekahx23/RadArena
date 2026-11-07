/* Trace inspection is read-only. Live launches are explicit in live.js. */
const $ = id => document.getElementById(id);
const state = {runs: [], tools: [], run: null, episode: null, step: -1, image: 0,
  page: 'history', liveFollow: true, workspace: 'arena', judgeId: null, tab: 'output', playing: false, timer: null, watch: false, zoom: 1, inverted: false, loading: false};
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = value => '$' + Number(value || 0).toFixed(6);
const number = value => Number(value || 0).toLocaleString('en-US');
const pretty = value => typeof value === 'string' ? value : JSON.stringify(value, null, 2);
const label = value => String(value || '').replaceAll('_', ' ');
const sum = calls => calls.reduce((total, c) => total + c.cost, 0);
const visibleCalls = () => state.episode?.calls.slice(0, state.step + 1) || [];
const currentCall = () => state.episode?.calls[state.step];
const actionTitle = call => call.role === 'judge' && call.review_disposition ? ({accepted:'Judge · accepted', superseded:'Judge · earlier response', rejected:'Judge · rejected', raw:'Judge review'}[call.review_disposition]) : ({attack:'Create challenge', plan:'Plan image checks', inspect:'Inspect image', assess:'Blue verdict', direct:'Direct image verdict', text:'Text-only verdict', handbook:'Read handbook', judge:'Judge review', open_attack:'Rewrite report', open_assess:'Blue verdict', open_review:'Judge open report', reflect_red:'Update Red memory', reflect_blue:'Update Blue memory', update_lessons:`Update ${call.role} lessons`}[call.action] || call.name);
const crewLabel = result => result?.review_policy === 'majority_distinct_families_v1' ? 'JUDGE CREW · 2 OF 3 · DISTINCT FAMILIES' : 'TWO-JUDGE CONSENSUS';
const badge = call => call.cost_known ? money(call.cost) : `${money(call.cost)} reserve`;
let loadGeneration = 0;

async function getJSON(url) {
  const response = await fetch(url, {cache: 'no-store'});
  if (!response.ok) throw new Error('The local trace is unavailable. Refresh or select another run.');
  return response.json();
}
function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }
function runTitle(run) { return run.id.replace(/^midpoint-/, '').replace(/-/g, ' '); }
function renderRuns() {
  const query = $('search').value.toLowerCase();
  $('run-count').textContent = state.runs.length.toString().padStart(2, '0');
  const filtered = state.runs.filter(r => `${r.id} ${r.kind}`.toLowerCase().includes(query));
  $('run-list').innerHTML = filtered.map(run => `<button class="run-item ${state.run?.id === run.id ? 'active' : ''}" data-run="${esc(run.id)}" aria-pressed="${state.run?.id === run.id}"><span class="run-kind">${esc(run.kind)}<span>${run.kind === 'Red × Blue' ? '↗' : '≡'}</span></span><span class="run-title">${esc(runTitle(run))}</span><span class="run-summary">${run.format === 'open_online' ? `${run.completed_studies}/${run.expected_studies} studies` : `${run.episode_count} ${run.format === 'learning' ? 'views' : run.episode_count === 1 ? 'case' : 'cases'}`} <span aria-hidden="true">·</span> ${money(run.cost)}${run.unknown_calls ? ' *' : ''}</span></button>`).join('') || '<p class="empty">No matching runs.</p>';
  $('run-list').querySelectorAll('[data-run]').forEach(button => button.onclick = () => loadRun(button.dataset.run));
}
function updateHash() {
  if (!state.run || !state.episode) return;
  history.replaceState(null, '', '#' + new URLSearchParams({...(state.page === 'live' ? {page:'live'} : {}), run: state.run.id, episode: state.episode.id, view: state.workspace, step: String(state.step + 1), ...(state.judgeId ? {judge: state.judgeId} : {})}));
}
async function loadRun(id, episodeId, refresh = false) {
  const generation = ++loadGeneration;
  const run = await getJSON('/api/run?' + new URLSearchParams({id})).catch(error => { notice(error.message); return null; });
  if (!run || generation !== loadGeneration) return;
  const oldStep = state.step;
  const oldCount = state.episode?.calls.length || 0;
  const follow = refresh && oldStep === oldCount - 1;
  state.run = run;
  $('run-cost').textContent = money(run.cost);
  $('cost-note').textContent = run.unknown_calls ? `${run.unknown_calls} request reserves included *` : 'Provider-reported · USD';
  $('agent-total-cost').textContent = money(run.agent_cost);
  $('judge-total-cost').textContent = money(run.judge_cost);
  $('run-calls').textContent = String(run.calls_count).padStart(2, '0');
  $('episode-count').textContent = run.format ? `${run.episodes.length} views · ${run.study_count} studies` : `${run.episodes.length} ${run.episodes.length === 1 ? 'episode' : 'episodes'} in this run`;
  $('run-name').textContent = run.id;
  $('run-subtitle').textContent = run.format === 'open_online' ? 'Open-ended report attacks, evolving private memories, and two reviewers.' : run.format === 'learning' ? 'Role-private strategy updates, training rounds, and before/after probes.' : run.kind === 'Red × Blue' ? 'One source report. A constrained attack. An image-grounded response.' : 'The same study, across verification conditions. Inspect each recorded action.';
  $('episode').innerHTML = run.episodes.map(episode => `<option value="${esc(episode.id)}">${episode.activity_type === 'memory_update' ? `Memory / ${esc(episode.memory_role)} / ${esc(episode.checkpoint)}` : `Study ${esc(episode.study_id)}${episode.round ? ` / ${episode.phase === 'frozen paired probe' ? 'probe set' : 'round '+episode.round}` : ''} / ${esc(label(episode.variant))}${episode.experiment_format ? '' : ' / '+(episode.attack?.has_error === false ? 'control' : 'attack')}`}</option>`).join('');
  const selected = run.episodes.find(e => e.id === episodeId) || run.episodes[0];
  $('observer-content').hidden = state.page === 'live' && !selected;
  renderRuns();
  if (!selected) {
    state.episode = null;
    if (state.page !== 'live') notice('This run has no recorded requests yet. Watch new calls to follow it.');
    return;
  }
  selectEpisode(selected.id, state.page === 'live' && state.liveFollow ? selected.calls.length - 1 : refresh ? (follow ? selected.calls.length - 1 : oldStep) : undefined, refresh);
  if (state.page === 'live') renderLiveDiff();
  notice('');
}
function selectEpisode(id, step, preserveImage = false) {
  stopReplay();
  state.episode = state.run.episodes.find(e => e.id === id);
  const lastAgent = state.episode.calls.findLastIndex(call => call.role !== 'judge');
  state.step = Math.min(step ?? (state.workspace === 'judge' ? state.episode.calls.length - 1 : lastAgent), state.episode.calls.length - 1);
  if (!state.episode.judges?.some(r => r.id === state.judgeId)) state.judgeId = state.episode.judges?.[0]?.id || null;
  if (step == null && state.workspace === 'judge' && state.judgeId) {
    const judgeStep = state.episode.calls.findLastIndex(call => call.judge_id === state.judgeId);
    if (judgeStep >= 0) state.step = judgeStep;
  }
  if (state.episode.activity_type === 'memory_update') state.workspace = 'arena';
  setWorkspace(state.workspace, false);
  $('episode').value = id;
  if (!preserveImage) { state.image = 0; resetImage(); }
  $('case-kind').textContent = state.episode.attack?.requested_error_type || state.episode.attack?.error_type || (state.episode.attack?.has_error === false ? 'Unchanged report' : 'Fresh attack pending');
  $('record-status').textContent = state.episode.status === 'recording' ? 'RECORDING' : ['error', 'failed'].includes(state.episode.status) ? 'FAILED' : state.episode.status === 'invalid_output' ? 'INVALID OUTPUT' : 'RECORDED';
  renderImages(); renderStep(); renderExperimentContext(); updateHash();
  if (state.page === 'live') renderLiveDiff();
}
function imageURL(index) {
  return '/api/image?' + new URLSearchParams({run: state.run.id, episode: state.episode.id, index});
}
function renderImages() {
  const images = state.episode.images;
  state.image = Math.min(state.image, Math.max(images.length - 1, 0));
  $('study-label').textContent = `STUDY ${state.episode.study_id}`;
  $('image-meta').textContent = `IU / OPENI · ${images.length} VIEWS`;
  $('image-count').textContent = `${images.length ? state.image + 1 : 0} / ${images.length}`;
  $('view-label').textContent = (images[state.image]?.view || 'VIEW NOT RECORDED').toUpperCase();
  const img = $('study-image');
  img.hidden = !images.length;
  $('image-empty').hidden = !!images.length;
  $('image-empty').textContent = state.episode.activity_type === 'memory_update' ? 'Strategy update · no study images in this action' : 'Study image unavailable';
  if (images.length) {
    img.alt = `Study ${state.episode.study_id}, ${images[state.image].view}, image ${state.image + 1}`;
    const nextURL = imageURL(state.image);
    if (img.getAttribute('src') !== nextURL) img.src = nextURL;
  } else img.removeAttribute('src');
  $('thumbnails').innerHTML = images.map((image, index) => `<button class="thumb ${state.image === index ? 'active' : ''}" data-image="${index}" aria-label="Show ${esc(image.view)} image ${index+1}" aria-pressed="${state.image === index}"><img src="${esc(imageURL(index))}" alt=""><span>${esc(image.view)}<small>IMAGE ${String(index+1).padStart(2, '0')}</small></span></button>`).join('');
  $('thumbnails').querySelectorAll('[data-image]').forEach(button => button.onclick = () => { state.image = +button.dataset.image; renderImages(); });
}
function applyImage() {
  $('study-image').style.transform = `scale(${state.zoom})`;
  $('study-image').style.filter = `brightness(${$('brightness').value}%) contrast(${$('contrast').value}%) invert(${state.inverted ? 1 : 0})`;
  $('zoom-label').textContent = state.zoom === 1 ? 'FIT TO VIEW' : `ZOOM ${Math.round(state.zoom * 100)}%`;
  $('window-label').textContent = `BRIGHTNESS ${$('brightness').value} · CONTRAST ${$('contrast').value}`;
  $('invert').setAttribute('aria-pressed', String(state.inverted));
}
function resetImage() { state.zoom = 1; state.inverted = false; $('brightness').value = 100; $('contrast').value = 100; applyImage(); }
function reportHTML(sentences, changed = new Set()) {
  return sentences.map(s => `<div class="report-row ${changed.has(s.id) ? 'changed' : ''}"><span class="sentence-id">${esc(s.id)}</span><span>${esc(s.text.replace(/^(FINDINGS|IMPRESSION):\s*/, ''))}</span></div>`).join('');
}
function verdictFor(calls) {
  const actions = ['assess', 'open_assess', 'direct', 'text'];
  const finalIndex = state.episode.calls.findLastIndex(call => call.role === 'blue' && actions.includes(call.action));
  if (state.episode.verdict && (finalIndex < 0 || state.step >= finalIndex)) return state.episode.verdict;
  return calls.filter(call => call.role === 'blue' && actions.includes(call.action) && call.status === 'complete').at(-1)?.outputs[0]?.verdict;
}
function memoryRoleHTML(role) {
  const episode = state.episode;
  if (role !== episode.memory_role) return `<div class="context-label">Role-private update</div><p class="context-description">This stage updates ${esc(episode.memory_role)}'s strategy. Select another checkpoint to inspect this role's updates.</p>`;
  const previous = episode.memories?.[role]?.rules || [];
  const rules = episode.memory_rules || [];
  const explanation = episode.memory_update?.explanation;
  return `<div class="context-label">${esc(episode.checkpoint)} · ${rules.length} saved rules</div><div class="agent-action">${esc(explanation || 'Waiting for a saved memory checkpoint.')}</div><div class="agent-section"><div class="context-label">Updated rules</div>${rules.map((rule, index) => `<div class="finding"><span class="accent">${index+1} / </span>${esc(rule)}</div>`).join('') || '<p class="agent-note">No rules in the saved checkpoint.</p>'}</div><details class="report-details"><summary>Previous private rules · ${previous.length}</summary>${previous.map(rule => `<div class="finding">${esc(rule)}</div>`).join('') || '<p class="agent-note">Empty initial strategy input.</p>'}</details>`;
}
function renderExperimentContext() {
  const root = $('experiment-context');
  const run = state.run, episode = state.episode;
  root.hidden = !run.format;
  if (!run.format) { root.innerHTML = ''; return; }
  const progress = run.format === 'open_online' ? `${run.completed_studies}/${run.expected_studies} studies recorded` : `${run.study_count} studies · training + before/after probes`;
  const phase = episode.activity_type === 'memory_update' ? `Private ${episode.memory_role} update · ${episode.checkpoint}` : run.live_demo ? `Live study ${episode.study_index} · ${label(episode.variant)}` : episode.phase === 'frozen paired probe' ? 'Final paired probe · memories frozen' : episode.round ? `Training round ${episode.round}` : episode.checkpoint ? `${label(episode.checkpoint)} checkpoint` : label(episode.variant);
  const memories = Object.entries(episode.memories || {});
  root.innerHTML = `<div class="experiment-line"><span>${run.format === 'open_online' ? 'OPEN-ENDED ONLINE' : 'STRATEGY LEARNING'}</span><b>${esc(phase)}</b><small>${esc(progress)} · ${run.complete ? 'complete' : 'incomplete'}</small></div><details class="experiment-details"><summary>Context & private memories ${memories.map(([role, memory]) => `· ${role} ${memory.version}`).join(' ')}</summary>${episode.indication ? `<div class="field-label">SUPPLIED INDICATION</div><p>${esc(episode.indication)}</p>` : ''}<div class="memory-context-grid">${memories.map(([role, memory]) => `<section class="memory-context-card"><div class="field-label ${role === 'blue' ? 'blue-ink' : 'red-ink'}">${esc(role.toUpperCase())} · ${esc(memory.version)} · ${memory.rules.length} RULES</div>${memory.sha256 ? `<small class="memory-hash" title="${esc(memory.sha256)}">${esc(memory.sha256.slice(0,16))}…</small>` : ''}<ol>${memory.rules.map(rule => `<li>${esc(rule)}</li>`).join('')}</ol>${!memory.rules.length ? '<p>Empty strategy input.</p>' : ''}</section>`).join('')}</div><p class="protocol-note">${esc(run.protocol || '')}</p>${run.format === 'open_online' ? '<p class="protocol-note">Open rewrites, additions, and omissions use report-level outcomes. Sentence-localization F1 is not applicable.</p>' : ''}</details>`;
}

function fieldsHTML(value) {
  if (!value || (Array.isArray(value) && !value.length)) return '<p class="context-description">No output recorded yet.</p>';
  if (Array.isArray(value) && value.length === 1) return fieldsHTML(value[0]);
  if (value.verdict) return fieldsHTML(value.verdict);
  if (value.review) return fieldsHTML(value.review);
  if (typeof value !== 'object' || Array.isArray(value)) return `<pre>${esc(pretty(value))}</pre>`;
  return `<div class="output-grid">${Object.entries(value).map(([key, val]) => `<div class="output-field"><div class="field-label">${esc(label(key))}</div><div class="field-text">${esc(pretty(val))}</div></div>`).join('')}</div>`;
}
function questionFor(call) {
  const messages = (call?.inputs.messages || []).filter(m => m.role !== 'system');
  const text = messages.map(m => typeof m.content === 'string' ? m.content : (m.content || []).map(p => p.text || '').join('')).join('\n');
  const match = text.match(/\[\[ ## question ## \]\]\s*([\s\S]*?)(?=\[\[ ##|$)/);
  return match?.[1].replace(/\s*Respond with a JSON object[\s\S]*$/, '').trim() || '';
}
function contextForRole(role, calls) {
  const latest = calls.filter(c => c.role === role).at(-1);
  const episode = state.episode;
  if (episode.activity_type === 'memory_update') return memoryRoleHTML(role);
  const modelReport = ['model', 'reused'].includes(episode.attacker_kind) || (!episode.attacker_kind && episode.variant === 'red_blue');
  const sourceById = new Map(episode.source.map(s => [s.id, s.text]));
  const changed = new Set([...(episode.attack?.edits?.map(e => e.sentence_id) || episode.attack?.changed_sentence_ids || []), ...episode.candidate.filter(s => sourceById.has(s.id) && sourceById.get(s.id) !== s.text).map(s => s.id)]);
  const report = (sentences, title) => `<details class="report-details"><summary>${esc(title)} · ${sentences.length} sentences</summary>${reportHTML(sentences, changed)}</details>`;
  const excerpt = sentences => `<div class="context-excerpt">${reportHTML(sentences.filter(s => changed.has(s.id)).slice(0, 2), changed) || reportHTML(sentences.slice(0, 2))}</div>`;
  const model = latest?.model.replace(/^openrouter\//, '') || (role === 'red' && episode.attacker_kind === 'reused' ? 'Reused model-generated candidate' : role === 'red' && !modelReport ? 'Deterministic lexical seed' : 'Waiting for recorded action');
  const modelHTML = `<div class="agent-model">${esc(model)}</div>`;
  if (role === 'red') {
    if (episode.attack?.has_error === false && !calls.some(c => ['attack', 'open_attack'].includes(c.action))) return `<div class="agent-model">No attacker call</div><div class="context-label">Unchanged control</div><p class="context-description">The source report was passed to Blue without an injected edit.</p>${excerpt(episode.source)}${report(episode.source, 'Full source report')}`;
    if (!modelReport) return modelHTML + `<div class="context-label">Frozen benchmark attack</div><p class="context-description">${episode.attack?.has_error ? `A deterministic ${esc(label(episode.attack.error_type))} edit was applied before this run.` : 'Unchanged control. No attack was applied.'}</p><div class="agent-section"><div class="context-label">Source report · researcher context</div>${excerpt(episode.source)}${report(episode.source, 'Full source report')}</div><p class="agent-note">No Red model call in this condition. Source text and edit labels are not sent to Blue.</p>`;
    const attackCall = calls.filter(c => ['attack', 'open_attack'].includes(c.action) && c.status === 'complete').at(-1);
    const result = attackCall?.outputs[0];
    return modelHTML + `<div class="context-label">Source report</div>${excerpt(episode.source)}<div class="agent-section"><div class="context-label">${attackCall ? 'Recorded attack' : 'Assigned objective'}</div><p class="agent-action">${esc(result?.private_rationale || result?.rationale || episode.attack?.rationale || `Change one ${label(episode.attack?.requested_error_type || 'report')} attribute while preserving unrelated claims.`)}</p>${(episode.attack?.changes || []).map(change => `<div class="finding"><span class="accent">${esc(change.category)} · ${esc((change.source_ids || []).join(', '))} → ${esc((change.candidate_ids || []).join(', ') || 'removed')}</span><p>${esc(change.description)}</p></div>`).join('')}${result?.edits?.map(e => `<div class="finding"><span class="accent">${esc(e.sentence_id)} → </span>${esc(e.replacement)}</div>`).join('') || ''}</div>${report(episode.source, 'Full source report')}<p class="agent-note">Visible to Red: source report + study images. Private edits and rationale stay outside Blue’s context.</p>`;
  }
  const attackFinished = !modelReport || episode.attacker_kind === 'reused' || episode.attack?.has_error === false || calls.some(c => ['attack', 'open_attack'].includes(c.action) && c.status === 'complete');
  let html = modelHTML + `<div class="context-label">Candidate report ${attackFinished ? '· received' : '· pending handoff'}</div>`;
  html += attackFinished ? excerpt(episode.candidate) : '<p class="context-description">Waiting for Red’s candidate report.</p>';
  if (latest) {
    const output = latest.outputs[0];
    html += '<div class="agent-section">';
    if (latest.action === 'plan') {
      html += '<div class="context-label">Verification plan</div>';
      html += output?.questions?.map((q, i) => `<div class="finding"><span class="accent">0${i+1} / </span>${esc(q)}</div>`).join('') || '<p class="agent-note">Waiting for the planning response.</p>';
    } else if (latest.action === 'inspect') {
      html += `<div class="context-label">Image inspection</div><p class="agent-action accent">${esc(questionFor(latest))}</p><p class="agent-action" style="margin-top:9px">${esc(output?.observation || 'Waiting for image-tool response.')}</p><p class="agent-note">${esc(output?.limitations || '')}</p>`;
    } else if (['assess', 'open_assess', 'direct', 'text'].includes(latest.action) && verdictFor(calls)) {
      const v = verdictFor(calls);
      html += `<div class="context-label">Recorded verdict</div><b class="verdict-label">${esc(label(v.decision))}</b>`;
      html += v.findings.map(f => `<div class="finding"><span class="accent">${esc(f.sentence_id)} · ${esc(label(f.error_type))}</span><p>${esc(f.evidence)}</p>${(f.tool_call_ids || []).map(id => `<button class="evidence-link" data-evidence="${esc(id)}">${esc(id)} ↗</button>`).join('')}${f.report_sentence_ids?.length ? `<small class="agent-note">Report evidence: ${esc(f.report_sentence_ids.join(', '))}</small>` : ''}</div>`).join('');
      html += `<p class="agent-note">${esc(v.limitations)}</p>`;
    } else html += `<div class="context-label">${esc(latest.name)}</div><p class="agent-note">${latest.status === 'failed' ? esc(latest.error) : latest.status === 'pending' ? 'Request started. No response recorded yet.' : 'Select full request context below to inspect this action.'}</p>`;
    html += '</div>';
  }
  return html + (attackFinished ? report(episode.candidate, 'Full candidate report') : '') + `<p class="agent-note">${episode.variant === 'text_only' ? 'Text-only condition: Blue has no image access.' : 'Blue sees candidate text; image checks receive only the images and the question.'} Colored report rows mark researcher-visible edits.</p>`;
}
function activeJudge() {
  return state.episode?.judges?.find(review => review.id === state.judgeId) || state.episode?.judges?.[0];
}
function reviewIsVisible(review) {
  if (!review) return false;
  if (!review.has_trace) return true;
  const indexes = state.episode.calls.map((call, index) => call.judge_id === review.id ? index : -1).filter(index => index >= 0);
  return indexes.length > 0 && indexes.at(-1) <= state.step;
}
function setWorkspace(view, jump = true) {
  state.workspace = view;
  if (jump && view === 'judge') {
    const indexes = state.episode?.calls.map((call, index) => call.judge_id === activeJudge()?.id ? index : -1).filter(index => index >= 0) || [];
    if (indexes.length) state.step = indexes.at(-1);
  } else if (jump && currentCall()?.role === 'judge') {
    state.step = state.episode.calls.findLastIndex(call => call.role !== 'judge');
  }
  $('arena').classList.toggle('judge-view', view === 'judge');
  $('arena').classList.toggle('memory-view', state.episode?.activity_type === 'memory_update' && view === 'arena');
  document.querySelector('.image-panel').hidden = state.episode?.activity_type === 'memory_update' && view === 'arena';
  document.querySelectorAll('.arena > .agent').forEach(panel => panel.hidden = view === 'judge');
  $('judge-panel').hidden = view !== 'judge';
  $('view-arena').setAttribute('aria-pressed', String(view === 'arena'));
  $('view-judge').setAttribute('aria-pressed', String(view === 'judge'));
  $('workspace-caption').textContent = view === 'judge' ? 'An independent review of the completed episode.' : 'Red creates the challenge. Blue checks the evidence.';
  if (jump) { stopReplay(); renderStep(); updateHash(); if (view === 'judge' && window.innerWidth <= 800) document.querySelector('.workspace-toolbar').scrollIntoView({behavior:'smooth', block:'start'}); }
}
function evidenceIndex(id) {
  if (id.startsWith('vision_')) {
    const observation = state.episode.observations.find(o => o.tool_call_id === id);
    if (observation) {
      const match = state.episode.calls.findIndex(call => call.action === 'inspect' && call.status === 'complete' && questionFor(call) === observation.question);
      if (match >= 0) return match;
    }
    return state.episode.calls.map((call, index) => ({call, index})).filter(({call}) => call.action === 'inspect')[+id.split('_')[1]-1]?.index ?? -1;
  }
  return state.episode.calls.findIndex(call => call.action === (id === 'direct_image' ? 'direct' : 'text'));
}
function bindEvidenceLinks(root) {
  root.querySelectorAll('[data-evidence]').forEach(button => {
    const index = evidenceIndex(button.dataset.evidence);
    button.disabled = index < 0;
    button.onclick = () => chooseStep(index);
  });
}
function renderEpisodeSummary(calls) {
  const verdict = verdictFor(calls);
  if (state.episode.activity_type === 'memory_update') {
    $('episode-summary').innerHTML = `<div><span class="summary-label">ROLE-PRIVATE STRATEGY UPDATE</span><b>${esc(state.episode.memory_role)} · ${esc(state.episode.checkpoint)}</b><small>${state.episode.memory_rules?.length || 0} saved rules</small></div><div><span class="summary-label">MODEL REQUESTS</span><b>${state.episode.calls.length}</b><small>Feedback and update output are on the tape</small></div><div><span class="summary-label">STAGE SPEND</span><b>${money(sum(state.episode.calls))}</b><small>No report-verification score for this action</small></div>`;
    return;
  }
  const score = state.episode.score;
  const review = activeJudge();
  const judged = reviewIsVisible(review) && review?.record?.status === 'ok';
  $('episode-summary').innerHTML = `<div><span class="summary-label blue-ink">BLUE'S VERDICT</span><b>${verdict ? esc(label(verdict.decision)) : 'Awaiting verdict'}</b><small>${verdict ? `${verdict.findings?.length || 0} flagged sentences` : 'Follow the action tape'}</small></div><div><span class="summary-label">${state.episode.score_scope === 'open_report' ? 'OPEN-ENDED REPORT · OUTCOME' : 'CODE SCORE · EDIT MATCHING'}</span><b>${state.episode.score_scope === 'open_report' ? `${state.episode.attack?.changes?.length || 0} change groups / ${verdict?.findings?.length || 0} flags` : verdict && score ? `${score.localization_tp} matched / ${score.localization_fp} additional / ${score.localization_fn} missed` : 'Not scored yet'}</b><small>${state.episode.score_scope === 'open_report' ? 'Sentence-localization F1 is not applicable' : 'Against injected sentence IDs'}</small></div><button id="summary-judge" class="summary-judge"><span class="summary-label judge-ink">JUDGE'S ASSESSMENT ↗</span><b>${judged ? esc(label(review.record.analysis?.blue_assessment || 'unknown')) : review ? 'Review available' : 'Not reviewed'}</b><small>${judged ? `${esc(label(review.record.analysis?.confidence || 'unknown'))} confidence · model opinion` : 'Independent post-hoc review'}</small></button>`;
  $('summary-judge').onclick = () => setWorkspace('judge');
  if (state.episode.outcome) {
    const result = state.episode.outcome;
    $('episode-summary').insertAdjacentHTML('afterbegin', `<div class="study-result-bar ${esc(result.state)}"><span class="summary-label">FINAL STUDY RESULT · ${esc(crewLabel(result))}</span><b>${esc(result.title)}</b><small>${esc(result.reason)}</small></div>`);
  }
}
function renderJudge(calls) {
  const reviews = state.episode?.judges || [];
  const review = activeJudge();
  const record = review?.record;
  state.judgeId = review?.id || null;
  $('review-count').textContent = reviews.length;
  $('judge-select').innerHTML = reviews.length ? reviews.map((r, index) => `<option value="${esc(r.id)}">${esc(r.model.replace(/^openrouter\//, ''))}${r.record?.fallback_used ? ' · backup for Gemma' : ''} · ${esc(r.record?.rubric_version || 'review '+(index+1))}</option>`).join('') : '<option>No judge recorded</option>';
  $('judge-select').disabled = reviews.length < 2;
  if (review) $('judge-select').value = review.id;
  $('judge-scope').textContent = record?.image_review === true ? 'Images + evidence' : record?.image_review === false ? 'Evidence only' : '';
  $('judge-cost').textContent = review ? money(review.cost) + (review.cost_known ? '' : ' *') : '—';
  $('judge-cost').title = review && !review.cost_known ? 'Accounted amount; provider cost is not confirmed for every request.' : 'Provider-reported amount for this review';
  const visible = reviewIsVisible(review);
  $('judge-state').textContent = !review ? 'NOT RUN' : !visible ? 'AVAILABLE' : review.status === 'ok' && record?.analysis ? 'REVIEWED' : review.status === 'ok' ? 'INCOMPLETE' : ['failed', 'rejected'].includes(review.status) ? review.status.toUpperCase() : 'RECORDING';
  $('jump-judge').disabled = !review?.has_trace;
  $('jump-judge').onclick = () => {
    const index = state.episode.calls.findLastIndex(c => c.judge_id === review.id);
    state.tab = 'input'; chooseStep(index);
    document.querySelector('.inspector').scrollIntoView({behavior:'smooth', block:'start'});
  };
  if (!review) {
    $('judge-content').innerHTML = '<div class="judge-empty"><span class="judge-empty-mark">J</span><h3>No independent review yet.</h3><p>This episode has Blue’s verdict and code-based edit matching. A recorded judge review will appear here when available.</p><small>Viewing and replaying traces makes no model calls.</small></div>';
    return;
  }
  if (!visible) {
    $('judge-content').innerHTML = '<div class="judge-empty"><h3>The review comes after the agents.</h3><p>Continue the tape to the judge action, or open Judge review to jump to the recorded assessment.</p></div>';
    return;
  }
  if (record?.status !== 'ok' || !record.analysis) {
    const failed = ['failed', 'rejected'].includes(review.status) || review.calls.at(-1)?.status === 'failed';
    $('judge-content').innerHTML = `<div class="judge-empty"><h3>${failed ? 'Review did not complete.' : 'Waiting for a recorded review.'}</h3><p>${failed ? esc(record?.exception_type || review.calls.at(-1)?.error || 'No accepted judge analysis was saved.') : 'The judge request is visible in the tape. Its accepted assessment has not been saved yet.'}</p><small>Accounted spend remains visible even when a request fails.</small></div>`;
    return;
  }
  const a = record.analysis;
  const warnings = review.warnings || [];
  const detailedReview = Array.isArray(a.flag_reviews);
  const reviewedFlags = detailedReview ? a.flag_reviews : (a.reviewed_flag_ids || []).map(sentence_id => ({sentence_id}));
  const flagRows = reviewedFlags.map(flag => {
    const blueFlag = state.episode.verdict?.findings?.find(f => f.sentence_id === flag.sentence_id);
    const sentence = state.episode.candidate.find(s => s.id === flag.sentence_id);
    const tension = warnings.some(w => w.sentence_id === flag.sentence_id);
    return `<details class="review-flag"><summary><span class="flag-id">${esc(flag.sentence_id)}</span><span>${detailedReview ? esc(label(flag.evidence_relation)) : 'Reviewed · overall explanation'}</span>${tension ? '<span class="tension-tag">Review tension</span>' : ''}<span class="expand-hint">Compare ↗</span></summary><p class="review-claim">“${esc(sentence?.text || 'Sentence text unavailable')}”</p><div class="flag-comparison"><div><div class="field-label blue-ink">BLUE FLAGGED THIS CLAIM</div><p>${esc(blueFlag?.evidence || 'No evidence text recorded.')}</p><small>Category: ${esc(label(blueFlag?.error_type || 'not recorded'))}</small></div><div><div class="field-label judge-ink">JUDGE'S EXPLANATION</div><p>${esc(flag.explanation || 'No separate per-sentence explanation was recorded. See the overall assessment above.')}</p>${detailedReview ? `<small>Image: ${esc(label(flag.image_relation))} · Citation: ${esc(label(flag.citation_fidelity))}</small>` : ''}</div></div><div class="review-sources">${detailedReview ? 'Cited evidence' : 'Blue’s cited evidence'} ${(flag.cited_tool_call_ids || blueFlag?.tool_call_ids || []).map(id => `<button class="evidence-link" data-evidence="${esc(id)}">${esc(id)} ↗</button>`).join('') || '<span>None recorded</span>'}</div></details>`;
  }).join('');
  $('judge-content').innerHTML = `<div class="judgment-metrics"><div><span>ATTACK VALIDITY</span><b>${esc(label(a.attack_validity))}</b></div><div><span>BLUE PERFORMANCE</span><b>${esc(label(a.blue_assessment))}</b></div><div><span>${detailedReview ? 'RED OUTCOME' : 'FLAGS REVIEWED'}</span><b>${detailedReview ? esc(label(record.red_outcome || 'not recorded')) : reviewedFlags.length}</b></div><div><span>CONFIDENCE</span><b>${esc(label(a.confidence))}</b></div></div><section class="judge-explanation"><div class="field-label">WHY THE JUDGE SAYS THIS</div><p>${esc(a.explanation || a.blue_explanation || 'No overall explanation recorded.')}</p></section>${warnings.length ? `<div class="review-warning"><b>${warnings.length} review ${warnings.length === 1 ? 'tension' : 'tensions'}</b><p>The judge describes evidence as supporting ${warnings.map(w => esc(w.sentence_id)).join(', ')}, although Blue flagged those claims as errors. Compare the recorded statements below; the judge’s wording is preserved.</p></div>` : ''}<div class="review-section-label">SENTENCE-BY-SENTENCE REVIEW <span>${reviewedFlags.length} flags</span></div>${flagRows || '<p class="agent-note">Blue flagged no sentences for this judge to review.</p>'}<details class="review-notes"><summary>Attack review, failure modes & limitations</summary><div class="field-label">ATTACK REVIEW</div><p>${esc(a.attack_explanation)}</p>${a.attack_image_support ? `<div class="field-label">JUDGE'S IMAGE-SUPPORT ASSESSMENT</div><p>${esc(label(a.attack_image_support))}</p>` : ''}<div class="field-label">FAILURE MODES</div><p>${esc((a.failure_modes || []).map(label).join(', ') || 'None reported by the judge')}</p><div class="field-label">LIMITATIONS</div><p>${esc(a.limitations)}</p></details><p class="judge-disclosure">${esc(record.rubric_version || 'Recorded review')} · Independent model opinion, not clinical ground truth. ${record.fallback_used ? 'Backup reviewer replaced '+esc(record.requested_model)+'. Failed primary requests remain on the tape and in accounted cost. ' : ''}${record.agent_feedback && !record.agent_feedback.startsWith('none') ? esc(record.agent_feedback) : 'This review was not sent to Red or Blue.'}${!review.has_trace ? ' Per-request trace is unavailable for this saved review.' : ''}</p>`;
  bindEvidenceLinks($('judge-content'));
}
function renderStep() {
  const calls = visibleCalls();
  const requestImages = (currentCall()?.inputs.messages || []).flatMap(m => Array.isArray(m.content) ? m.content : []).filter(p => p.type === 'image_url').length;
  $('image-context').textContent = requestImages ? `${requestImages} IMAGES IN REQUEST` : 'NO IMAGE IN THIS REQUEST';
  $('step-label').textContent = `${Math.max(state.step + 1, 0)} / ${state.episode.calls.length}`;
  $('prev').disabled = state.step <= 0;
  $('next').disabled = state.step >= state.episode.calls.length - 1;
  $('play').disabled = !state.episode.calls.length;
  for (const role of ['red', 'blue']) {
    const teamCalls = calls.filter(c => c.role === role);
    $(`${role}-cost`).textContent = money(sum(teamCalls)) + (teamCalls.some(c => !c.cost_known) ? ' *' : '');
    const absent = role === 'red' ? state.episode.attacker_kind === 'none' ? 'NO ATTACK' : state.episode.attacker_kind === 'reused' ? 'REUSED' : state.episode.attacker_kind === 'seed' || (!state.episode.attacker_kind && state.episode.variant !== 'red_blue') ? 'SEED' : 'WAITING' : 'WAITING';
    $(`${role}-state`).textContent = teamCalls.at(-1)?.status.toUpperCase() || absent;
    $(`${role}-context`).innerHTML = contextForRole(role, calls);
  }
  bindEvidenceLinks($('blue-context'));
  $('current-action').textContent = currentCall() ? `${currentCall().role === 'judge' ? 'Independent judge' : currentCall().role === 'red' ? 'Red team' : 'Blue team'} / ${actionTitle(currentCall())} · ${currentCall().status}` : 'Choose an action to see its inputs and response.';
  $('timeline').innerHTML = state.episode.calls.map((call, index) => `<button class="tape-action ${call.role} ${index === state.step ? 'selected' : ''} ${index > state.step ? 'future' : ''}" data-step="${index}" aria-pressed="${index === state.step}" aria-label="Request ${index+1}, ${esc(call.name)}, ${esc(badge(call))}"><span class="tape-top"><b>${call.role.toUpperCase()}</b><span>${String(index+1).padStart(2,'0')} ${call.status === 'failed' ? '×' : call.status === 'pending' ? '◌' : '↗'}</span></span><span class="tape-name">${esc(actionTitle(call))}</span><span class="tape-bottom"><span>${call.elapsed == null ? 'pending' : call.elapsed.toFixed(2)+'s'}</span><span>${money(call.cost)}${call.cost_known ? '' : '*'}</span></span></button>`).join('') || '<p class="empty">No model requests recorded for this case yet.</p>';
  $('timeline').querySelectorAll('[data-step]').forEach(button => button.onclick = () => chooseStep(+button.dataset.step));
  renderJudge(calls);
  renderEpisodeSummary(calls);
  renderInspector();
}
function chooseStep(index, fromPlayback = false) {
  if (!fromPlayback) stopReplay();
  state.step = Math.max(0, Math.min(index, state.episode.calls.length - 1));
  if (currentCall()?.role === 'judge') { state.judgeId = currentCall().judge_id; setWorkspace('judge', false); }
  else setWorkspace('arena', false);
  renderStep(); updateHash();
  if (fromPlayback) $('timeline').querySelector('.selected')?.scrollIntoView({behavior:'smooth',block:'nearest',inline:'nearest'});
}
function renderInspector() {
  const call = currentCall();
  $('call-content').setAttribute('aria-labelledby', `tab-${state.tab}`);
  $('call-name').textContent = call ? `${String(state.step+1).padStart(2, '0')} / ${call.name}` : 'No request selected';
  $('call-role').textContent = call?.role.toUpperCase() || 'ACTION';
  $('call-role').className = `call-role ${call?.role || ''}`;
  $('call-status').textContent = call?.review_disposition ? call.review_disposition.toUpperCase() : call?.status.toUpperCase() || '—';
  $('call-duration').textContent = call?.elapsed == null ? 'No duration yet' : `${call.elapsed.toFixed(3)} s`;
  $('call-tokens').textContent = `${number(call?.usage.total_tokens)} tokens`;
  $('call-cost').textContent = call ? badge(call) : '—';
  $('call-model').textContent = call?.model.replace(/^openrouter\//, '') || '';
  document.querySelectorAll('[data-tab]').forEach(button => button.setAttribute('aria-selected', String(button.dataset.tab === state.tab)));
  if (!call) { $('call-content').innerHTML = '<p class="context-description">Choose a run with recorded requests.</p>'; return; }
  if (state.tab === 'input') {
    const messages = call.inputs.messages || [];
    $('call-content').innerHTML = `<div class="field-label">Exact recorded request · image payloads are represented by trace hashes</div>` + messages.map(message => {
      const parts = typeof message.content === 'string' ? [{type:'text', text:message.content}] : message.content || [];
      return `<section class="request-message"><div class="field-label">${esc(message.role)} message</div>${parts.map(part => part.type === 'text' ? `<pre>${esc(part.text)}</pre>` : `<div class="image-reference">▣ ${esc(part.image_url?.url || pretty(part))}</div>`).join('')}</section>`;
    }).join('') + `<details class="report-details"><summary>Request metadata & raw JSON</summary><pre>${esc(JSON.stringify(call.inputs, null, 2))}</pre></details>`;
  } else if (state.tab === 'usage') {
    $('call-content').innerHTML = `<div class="usage-grid"><div class="field-label">INPUT TOKENS<b>${number(call.usage.prompt_tokens)}</b></div><div class="field-label">OUTPUT TOKENS<b>${number(call.usage.completion_tokens)}</b></div><div class="field-label">REQUEST COST<b>${money(call.cost)}</b></div><div class="field-label">EPISODE TAPE SPEND<b>${money(sum(visibleCalls()))}</b></div><p class="usage-note">${call.cost_known ? 'Provider-reported cost for this recorded request.' : '* Cost is unknown. This is the conservative request reserve retained by the audit ledger, not a confirmed provider charge.'} Run accounted total: ${money(state.run.cost)} across ${state.run.calls_count} requests; known cost: ${money(state.run.known_cost)}. ${state.run.unknown_calls} unknown-cost requests retain reserves. Replay itself costs $0 and makes no model calls.</p></div>`;
  } else {
    $('call-content').innerHTML = (call.role === 'judge' ? '<p class="agent-note">Raw judge response. The Judge review panel shows the latest accepted saved assessment. Earlier or rejected responses remain on this tape; request completion alone does not mean the review was accepted.</p>' : '') + (call.status === 'failed' ? `<div class="field-label">Request failed</div><p class="field-text">${esc(call.error || 'No error details recorded.')}</p>` : fieldsHTML(call.outputs));
  }
}
function stopReplay() { clearTimeout(state.timer); state.playing = false; $('play').innerHTML = '▶ <span>Replay</span>'; $('play').setAttribute('aria-label', 'Replay recorded actions'); }
function tick() {
  if (!state.playing) return;
  if (state.step >= state.episode.calls.length - 1) { stopReplay(); return; }
  chooseStep(state.step + 1, true);
  state.timer = setTimeout(tick, +$('speed').value);
}
function toggleReplay() {
  if (state.playing) { stopReplay(); return; }
  if (!state.episode?.calls.length) return;
  if (state.step >= state.episode.calls.length - 1) chooseStep(0);
  state.playing = true;
  $('play').innerHTML = 'Ⅱ <span>Pause</span>';
  $('play').setAttribute('aria-label', 'Pause replay');
  state.timer = setTimeout(tick, +$('speed').value);
}
function renderRegistry() {
  const allCalls = state.run?.episodes.flatMap(e => e.calls) || [];
  $('tool-list').innerHTML = state.tools.map(tool => {
    const calls = allCalls.filter(c => c.action === tool.id);
    const unknown = calls.some(c => !c.cost_known);
    return `<div class="tool-row"><div class="tool-name">${esc(tool.name)}<small>${tool.role.toUpperCase()} / DSPY</small></div><div><p>${esc(tool.description)}</p><p class="tool-inputs">${esc(tool.inputs)}</p></div><div class="tool-price">${calls.length ? money(sum(calls)) + (unknown ? '*' : '') : '<span class="inactive">NOT USED</span>'}<small>${calls.length} requests${calls.length ? '<br>avg '+money(sum(calls)/calls.length) : ''}</small></div></div>`;
  }).join('');
}

$('view-arena').onclick = () => setWorkspace('arena');
$('view-judge').onclick = () => setWorkspace('judge');
$('judge-select').onchange = event => { state.judgeId = event.target.value; setWorkspace('judge'); };
$('refresh-run').onclick = () => { if (state.run) loadRun(state.run.id, state.episode?.id, true); poll(); };
$('search').oninput = renderRuns;
$('episode').onchange = event => { if (state.page === 'live') pauseLiveFollow(); selectEpisode(event.target.value); };
$('prev').onclick = () => chooseStep(state.step - 1);
$('next').onclick = () => chooseStep(state.step + 1);
$('play').onclick = toggleReplay;
$('zoom-in').onclick = () => { state.zoom = Math.min(3, state.zoom + .25); applyImage(); };
$('zoom-out').onclick = () => { state.zoom = Math.max(.5, state.zoom - .25); applyImage(); };
$('invert').onclick = () => { state.inverted = !state.inverted; applyImage(); };
$('reset-image').onclick = resetImage;
$('brightness').oninput = applyImage;
$('contrast').oninput = applyImage;
$('study-image').onerror = () => { $('image-empty').hidden = false; $('study-image').hidden = true; };
$('study-image').onload = () => { $('image-empty').hidden = true; $('study-image').hidden = false; };
$('tools-button').onclick = () => { renderRegistry(); $('tools-dialog').showModal(); };
$('close-tools').onclick = () => $('tools-dialog').close();
$('tools-dialog').onclick = event => { if (event.target === $('tools-dialog')) { const bounds = $('tools-dialog').getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) $('tools-dialog').close(); } };
document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => { state.tab = button.dataset.tab; renderInspector(); });
document.querySelectorAll('[role=tab]').forEach(button => button.onkeydown = event => {
  if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
  const tabs = [...document.querySelectorAll('[role=tab]')];
  const next = tabs[(tabs.indexOf(button) + (event.key === 'ArrowRight' ? 1 : 2)) % tabs.length];
  next.focus(); next.click(); event.preventDefault();
});
document.addEventListener('keydown', event => {
  if (/INPUT|SELECT|TEXTAREA|BUTTON/.test(event.target.tagName) || $('tools-dialog').open || !state.episode) return;
  if (event.code === 'Space') { event.preventDefault(); toggleReplay(); }
  if (event.code === 'ArrowLeft') { event.preventDefault(); chooseStep(state.step - 1); }
  if (event.code === 'ArrowRight') { event.preventDefault(); chooseStep(state.step + 1); }
});
$('watch').onclick = () => {
  state.watch = !state.watch;
  $('watch').setAttribute('aria-pressed', String(state.watch));
  if (state.watch) poll();
};
async function poll() {
  if (state.loading || document.hidden || state.page === 'live') return;
  state.loading = true;
  try {
    const listing = await getJSON('/api/runs');
    state.runs = listing.runs;
    renderRuns();
    if (state.watch && state.run && !state.playing) await loadRun(state.run.id, state.episode?.id, true);
    else if (!state.run && state.runs.length) await loadRun(state.runs[0].id);
    notice('');
  } catch (error) { notice('Local observer disconnected. Watching will retry automatically.'); }
  finally { state.loading = false; }
}
setInterval(poll, 4000);
async function boot() {
  try {
    const data = await getJSON('/api/runs');
    state.runs = data.runs; state.tools = data.tools; renderRuns();
    const params = new URLSearchParams(location.hash.slice(1));
    if (params.get('page') === 'live') { await openLive(params.get('run')); return; }
    if (!state.runs.length) {
      notice('No local traces found. Run a RadArena demo or evaluation from the CLI, then enable Watch new calls.');
      return;
    }
    state.workspace = params.get('view') === 'judge' ? 'judge' : 'arena';
    state.judgeId = params.get('judge');
    await loadRun(state.runs.some(r => r.id === params.get('run')) ? params.get('run') : state.runs[0].id, params.get('episode'));
    const savedStep = Number(params.get('step'));
    if (state.episode && Number.isInteger(savedStep) && savedStep > 0 && savedStep <= state.episode.calls.length) chooseStep(savedStep - 1);
  } catch (error) { notice(error.message); }
}
window.addEventListener('DOMContentLoaded', boot);
