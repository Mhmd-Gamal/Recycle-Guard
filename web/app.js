const $ = id => document.getElementById(id);
let sid = null, obs = null, advice = null, selected = 0, replay = null;
let busy = false, toastTimer, trailEvents = [], trailFilter = 'all';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
  shield:'<path d="M12 3 3 7v6c0 5 9 9 9 9s9-4 9-9V7Z"/><path d="m8 12 3 3 5-6"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  history:'<path d="M3 11a9 9 0 1 1 2 7M3 4v7h7m2-5v6l4 3"/>',
  arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>', reset:'<path d="M4 10a8 8 0 1 1 1 8M4 4v6h6"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',upload:'<path d="M12 16V4m-5 5 5-5 5 5M4 16v5h16v-5"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',users:'<circle cx="9" cy="7" r="3"/><path d="M3 21v-4a6 6 0 0 1 12 0v4M17 4a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 4v3"/>',
  drop:'<path d="M12 3S5 11 5 15a7 7 0 0 0 14 0c0-4-7-12-7-12Z"/>',alert:'<path d="m12 3 10 18H2Z M12 9v5m0 3v1"/>',
  eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  check:'<path d="m5 12 4 4L19 6"/>',close:'<path d="m6 6 12 12M6 18 18 6"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 10v7m0-11v1"/>'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${paths[name] || paths.info}</svg>`;
document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
const label = a => `${a.kind.toUpperCase()}${a.zone >= 0 ? ' / ' + (obs?.zones[a.zone]?.name || a.zone) : ''}`;
const titleCase = s => s.charAt(0).toUpperCase() + s.slice(1);

function facilityArt(id) {
  const drawings = [
    [20,64,108,152].map(x => `<rect x="${x}" y="9" width="30" height="35" rx="2"/><path d="M${x+9} 9V5h12v4m-17 8h22m-17 7h12m-6-5v10"/>`).join(''),
    '<rect x="10" y="19" width="180" height="19" rx="9"/>' + Array.from({length:11},(_,i)=>`<path d="M${23+i*15} 20v17"/>`).join('') + '<path d="M35 38v9m130-9v9"/><rect x="48" y="9" width="21" height="10"/><rect x="108" y="5" width="25" height="14"/>',
    [15,60,105,150].map(x=>`<rect x="${x}" y="9" width="33" height="14"/><rect x="${x}" y="29" width="33" height="14"/><path d="M${x+16} 9v14m0 6v14"/>`).join(''),
    '<path d="M12 8h180M12 46h180m-160-37v36m48-36v36m48-36v36m48-36v36"/><rect x="37" y="17" width="30" height="20" rx="2"/><path d="M67 22h9v15h-9m-29 2v4m25-4v4"/><rect x="133" y="17" width="30" height="20" rx="2"/>'
  ];
  return `<svg class="facility-art" viewBox="0 0 205 52" fill="none" stroke="currentColor" stroke-width="1.1" aria-hidden="true" focusable="false">${drawings[id]}</svg>`;
}
function toast(message) {
  $('toast').textContent = message; $('toast').classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('show'), 5500);
}
function showError(message) { $('error-message').textContent = message; $('error-banner').hidden = false; }
async function api(path, body, method) {
  const response = await fetch(path, {method:method || (body ? 'POST' : 'GET'), headers:body ? {'Content-Type':'application/json'} : {}, body:body ? JSON.stringify(body) : undefined});
  const data = await response.json();
  if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}
async function task(fn) {
  if (busy) return;
  const active = document.activeElement;
  const previousDecision = active?.dataset?.decision;
  busy = true; document.body.classList.add('busy'); $('error-banner').hidden = true; controls();
  try { await fn(); }
  catch (error) { showError(error.message); }
  finally {
    busy = false; document.body.classList.remove('busy'); controls();
    if (!$('seed-error').hidden) $('seed').focus();
    if (active && !active.isConnected && previousDecision) {
      const next = document.querySelector(`[data-decision="${previousDecision}"]`) || $('advise');
      next.focus({preventScroll:true});
    }
  }
}
function controls() {
  for (const id of ['advise','manual']) $(id).disabled = busy || !!replay || !obs || obs.status !== 'active';
  for (const id of ['reset','import','scenario','seed','mode']) $(id).disabled = busy || (id === 'mode' && !!replay);
  $('export').disabled = busy || !sid;
  for (const id of ['action','note']) $(id).disabled = busy || !!replay;
  document.querySelectorAll('[data-decision]').forEach(button => button.disabled = busy || !!replay);
  $('advice').setAttribute('aria-busy', String(busy));
  $('advise-label').textContent = busy ? 'Updating workspace…' : obs?.status !== 'active' && obs ? 'Incident complete' : 'Request recommendation';
}
function renderObservation(o, truth = false) {
  const zoneHadFocus = document.activeElement?.dataset?.zone;
  $('status').textContent = titleCase(o.status);
  $('status-detail').textContent = truth ? 'Recorded replay state' : ({active:'Awaiting operator decision',contained:'All occupants cleared; heat below 25',escalated:'Damage limit reached',timeout:'Decision horizon reached'}[o.status]);
  $('status-dot').style.background = o.status === 'escalated' || o.status === 'timeout' ? 'var(--red)' : 'var(--green)';
  $('tick').textContent = String(o.tick).padStart(2,'0'); $('crews').textContent = o.crews;
  $('water').textContent = o.water; $('damage').textContent = o.damage;
  $('tick-meter').style.width = `${o.tick / 32 * 100}%`; $('water-meter').style.width = `${o.water / 18 * 100}%`;
  $('selected').textContent = o.zones[selected].name;
  const current = o.zones[selected];
  $('selected-evidence').textContent = truth ? 'Recorded truth' : current.age < 0 ? 'Evidence unavailable' : current.age === 0 ? 'Current observation' : `Delayed by ${current.age} ticks`;
  $('view-badge').innerHTML = icon(truth ? 'history' : 'eye') + (truth ? 'Replay truth' : 'Observed state');
  $('zones').innerHTML = o.zones.map(z => {
    const uncertain = !truth && z.age !== 0;
    const status = !truth && z.age < 0 ? 'MISSING' : uncertain ? 'DELAYED' : z.heat >= 25 ? 'ELEVATED' : 'BELOW 25';
    const age = truth ? 'Recorded simulator truth' : z.age < 0 ? 'No current observation' : z.age === 0 ? `Current / ${z.source}` : `Observation age: ${z.age} ticks`;
    return `<button class="zone ${z.id===selected?'selected':''} ${z.heat>=25?'hot':''} ${uncertain?'uncertain':''}" data-zone="${z.id}" aria-pressed="${z.id===selected}" aria-label="Select ${esc(z.name)}. ${status}. Heat ${z.heat<0?'unknown':z.heat}. People ${z.people<0?'unknown':z.people}. ${esc(age)}."><div class="zone-top"><span>ZONE 0${z.id+1}</span><span class="zone-status">${icon(uncertain || z.heat>=25 ? 'alert':'check')}${status}</span></div><h3>${esc(z.name)}</h3>${facilityArt(z.id)}<div class="zone-values"><span>Heat <b>${z.heat<0?'?':z.heat}</b></span><span>People <b>${z.people<0?'?':z.people}</b></span><span class="power">${z.isolated<0?'Power unknown':z.isolated?'Isolated':'Powered'}</span></div><div class="zone-bar"><span style="width:${Math.max(0,z.heat)}%"></span></div><span class="age">${esc(age)}</span></button>`;
  }).join('');
  document.querySelectorAll('[data-zone]').forEach(button => {
    button.onclick = () => { selected = Number(button.dataset.zone); renderObservation(o,truth); renderAdvice(); };
    button.onkeydown = event => {
      const delta = {ArrowRight:1,ArrowLeft:-1,ArrowDown:2,ArrowUp:-2}[event.key];
      if (delta === undefined) return;
      event.preventDefault(); selected = (Number(button.dataset.zone) + delta + 4) % 4;
      renderObservation(o,truth); renderAdvice(); document.querySelector(`[data-zone="${selected}"]`).focus();
    };
  });
  if (zoneHadFocus !== undefined) document.querySelector(`[data-zone="${selected}"]`)?.focus({preventScroll:true});
  controls();
}
function emptyAdvice(title, text, symbol = 'shield') {
  return `<div class="empty"><div class="empty-symbol">${icon(symbol)}</div><h3>${esc(title)}</h3><p>${esc(text)}</p><div class="empty-steps"><span><b>01</b>Observe</span><span><b>02</b>Review</span><span><b>03</b>Decide</span></div></div>`;
}
function renderAdvice() {
  if (replay) { $('advice').innerHTML = emptyAdvice('Reviewing a past decision','Live recommendations are hidden during replay. Explore the decision trail below, or return to the live incident.','history'); return; }
  if (!advice) {
    const ended = obs && obs.status !== 'active';
    $('advice').innerHTML = emptyAdvice(ended ? 'Incident complete.' : 'Your decision comes first.', ended ? 'Export this session for review, or start a new seeded incident to compare your decisions.' : 'Request a recommendation to inspect its evidence and constraints. Nothing executes until you act.');
    return;
  }
  const a = advice;
  const target = a.recommendation.zone >= 0 ? obs.zones[a.recommendation.zone]?.name : 'Advance the simulation';
  const manualTarget = $('action').value === 'wait' ? 'one tick' : obs.zones[selected].name;
  $('advice').innerHTML = `<div class="advice-card"><span class="advice-tag ${a.violations.length?'warning':''}">${icon(a.intervention?'alert':'shield')}${a.intervention?'PROPOSAL REVISED':a.mode.includes('checked')?'OBSERVED CONSTRAINTS PASSED':'UNCHECKED POLICY'}</span><div class="recommendation-title"><h3>${esc(titleCase(a.recommendation.kind))}</h3><span class="revision">REV ${a.revision}</span></div><div class="target-label">${esc(target)}</div><p class="why">${esc(a.explanation)}</p><div class="evidence"><b>${icon('eye')}SUPPORTING EVIDENCE</b>${a.evidence.map(e=>`<p>${esc(e)}</p>`).join('')}</div>${a.missing.length?`<div class="missing">${icon('alert')}<span><b>Evidence gaps</b><br>${a.missing.map(esc).join('<br>')}</span></div>`:''}${a.plan?.length?`<details class="plan"><summary>Conditional next steps</summary><ol>${a.plan.map(step=>`<li>${esc(step)}</li>`).join('')}</ol></details>`:''}<div class="actions"><button class="primary" data-decision="accept">${icon('check')}Accept & execute</button><button data-decision="reject">${icon('close')}Reject</button><button data-decision="alternative">${icon('reset')}Alternative</button><button class="modify-button" data-decision="modify">Apply manual choice: ${esc($('action').value)} / ${esc(manualTarget)}</button></div><p class="uncertainty">${esc(a.uncertainty)}</p><div class="provider-line"><span>${esc(a.provider)}</span><span>${a.latency_ms.toFixed(2)} ms</span></div></div>`;
  document.querySelectorAll('[data-decision]').forEach(button => button.onclick = () => task(() => button.dataset.decision === 'alternative' ? getAdvice(true) : decide(button.dataset.decision)));
  controls();
}
function apply(data) { obs = data.observation; advice = data.advice; renderObservation(obs); renderAdvice(); }
async function history() {
  if (!sid) return;
  const log = await api(`/v1/sessions/${sid}/replay`); showTrail(log.events); return log;
}
function showTrail(events) {
  trailEvents = events;
  const filtered = events.filter(e => trailFilter === 'all' || (trailFilter === 'advice' ? ['advice','alternative'].includes(e.decision) : !['advice','alternative'].includes(e.decision)));
  $('event-count').textContent = events.length;
  $('trail').innerHTML = filtered.length ? [...filtered].reverse().map(e => {
    let detail = e.action ? `${e.action.kind} / zone ${e.action.zone} — ${e.reason}` : e.note;
    if (e.decision === 'advice' || e.decision === 'alternative') { try { const a = JSON.parse(e.note); detail = `${label(a.recommendation)} · ${a.explanation}`; } catch {} }
    const symbol = e.action ? (e.accepted?'check':'alert') : e.decision==='reject' ? 'close':'shield';
    return `<div class="trail-row"><span class="time">T+${String(e.tick).padStart(2,'0')}</span><span class="event ${e.action&&!e.accepted?'error':''}">${icon(symbol)}${esc(e.decision)}</span><span class="detail">${esc(detail)}${e.action&&e.note?'<br>Rationale: '+esc(e.note):''}</span></div>`;
  }).join('') : `<div class="trail-empty">${icon('history')}<span>${events.length?'No events match this filter.':'A clear record starts with your first decision. Actions and evidence will appear here.'}</span></div>`;
}
async function reset() {
  const seed = Number($('seed').value);
  const valid = $('seed').value.trim() !== '' && Number.isInteger(seed) && seed >= -2147483648 && seed <= 2147483647;
  $('seed-error').hidden = valid; $('seed').setAttribute('aria-invalid',String(!valid));
  if (!valid) { $('seed-error').textContent = 'Enter a whole-number seed between −2147483648 and 2147483647.'; $('seed').focus(); return; }
  const data = await api('/v1/sessions',{seed,scenario:$('scenario').value});
  const previous = sid; sid = data.id; replay = null;
  $('replay-controls').hidden = true; $('replay-banner').hidden = true;
  apply(data); await history();
  if (previous) await api(`/v1/sessions/${previous}`,null,'DELETE');
}
async function getAdvice(alternative = false) {
  apply(await api(`/v1/sessions/${sid}/advice`,{mode:$('mode').value,alternative}));
  await history(); toast('Recommendation ready. Review the evidence before accepting.');
}
async function decide(decision) {
  const kind = $('action').value;
  const action = {kind,zone:kind==='wait'?-1:selected,revision:obs.revision};
  const data = await api(`/v1/sessions/${sid}/decision`,{decision,action:decision==='manual'||decision==='modify'?action:null,note:$('note').value});
  apply(data); await history();
  toast(data.result ? (data.result.accepted ? `Action applied. Tick ${data.observation.tick}; incident ${data.observation.status}.` : 'Action blocked: '+data.result.reason) : 'Recommendation rejected. Simulation time has not advanced.');
}
function showReplay() {
  const index = Number($('replay-slider').value), event = replay.events[index];
  $('replay-label').textContent = `VERIFIED REPLAY / EVENT ${index+1} OF ${replay.events.length} / ${event.decision}`;
  $('replay-prev').disabled = index === 0; $('replay-next').disabled = index === replay.events.length-1;
  renderObservation(event.after,true); renderAdvice(); showTrail(replay.events.slice(0,index+1)); controls();
}
async function exitReplay() {
  const data = await api(`/v1/sessions/${sid}`);
  replay = null; $('replay-controls').hidden = true; $('replay-banner').hidden = true;
  apply(data); await history();
}
$('reset').onclick = () => task(reset);
$('advise').onclick = () => task(() => getAdvice());
$('manual').onclick = () => task(() => decide('manual'));
$('action').onchange = renderAdvice;
$('mode').onchange = () => {
  advice = null; renderAdvice();
  $('policy-note').textContent = $('mode').value.startsWith('llm') ? 'Requires a configured model endpoint. No automatic offline substitution.' : $('mode').value === 'scripted' ? 'Fixed-priority baseline. No language model is used.' : 'Offline proposals are test fixtures, not LLM outputs.';
};
$('dismiss-error').onclick = () => { $('error-banner').hidden = true; $('advise').focus(); };
$('seed').oninput = () => { $('seed-error').hidden = true; $('seed').removeAttribute('aria-invalid'); };
document.querySelectorAll('[data-filter]').forEach(button => button.onclick = () => {
  trailFilter = button.dataset.filter;
  document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  showTrail(trailEvents);
});
$('export').onclick = () => task(async () => {
  const log = replay || await history();
  const url = URL.createObjectURL(new Blob([JSON.stringify(log,null,2)],{type:'application/json'}));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = `recycleguard-${log.seed}-${log.scenario}.json`; anchor.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000); toast('Replay exported with decision evidence and state snapshots.');
});
$('import').onclick = () => $('replay-file').click();
$('replay-file').onchange = () => task(async () => {
  const file = $('replay-file').files[0]; if (!file) return;
  try {
    if (file.size > 2000000) throw Error('Replay must be smaller than 2 MB.');
    const log = JSON.parse(await file.text()); await api('/v1/replay/verify',log);
    if (!log.events.length) throw Error('Replay has no events.');
    replay = log; $('replay-controls').hidden = false; $('replay-banner').hidden = false;
    $('replay-slider').max = log.events.length-1; $('replay-slider').value = 0;
    showReplay(); toast('Replay verified. Debrief displays recorded truth, not live observations.');
  } finally { $('replay-file').value = ''; }
});
$('replay-slider').oninput = showReplay;
$('replay-prev').onclick = () => { $('replay-slider').value = Math.max(0,Number($('replay-slider').value)-1); showReplay(); };
$('replay-next').onclick = () => { $('replay-slider').value = Math.min(replay.events.length-1,Number($('replay-slider').value)+1); showReplay(); };
$('exit-replay').onclick = () => task(exitReplay); $('exit-replay-top').onclick = () => task(exitReplay);
document.querySelectorAll('.rail-link').forEach(link => link.onclick = () => {
  document.querySelectorAll('.rail-link').forEach(item=>item.classList.toggle('current',item===link));
});
renderAdvice(); task(reset);
document.addEventListener('focusin', event => {
  if (!$('toast').classList.contains('show')) return;
  const a = event.target.getBoundingClientRect(), b = $('toast').getBoundingClientRect();
  if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) $('toast').classList.remove('show');
});
