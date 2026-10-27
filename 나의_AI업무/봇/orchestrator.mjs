// 지시 흐름과 기록을 맡는 모듈. 디스코드와 상관없이 say(역할키, 글)만 받아서 동작한다.
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import os from 'node:os';

const HERE = import.meta.dirname;
export const ROOT = path.resolve(HERE, '..');
const TRACE_DIR = path.join(ROOT, '04_기록', '추적');
export const cfg = JSON.parse(await fs.readFile(path.join(HERE, 'roles.json'), 'utf8'));
const CLAUDE = process.env.CLAUDE_EXE || path.join(os.homedir(), '.local', 'bin', 'claude.exe');

export class LimitError extends Error {}

// 한 번에 한 지시만 처리한다(사용량과 파일 충돌을 줄이려는 것).
let queue = Promise.resolve();
export const enqueue = (fn) => (queue = queue.then(fn, fn));

const tracePath = (id) => path.join(TRACE_DIR, `${id}.jsonl`);
const statePath = (id) => path.join(TRACE_DIR, `${id}.state.json`);

async function nextId() {
  await fs.mkdir(TRACE_DIR, { recursive: true });
  const names = await fs.readdir(TRACE_DIR);
  const nums = names.map((n) => /^T-(\d+)\.jsonl$/.exec(n)?.[1]).filter(Boolean).map(Number);
  return 'T-' + String((nums.length ? Math.max(...nums) : 0) + 1).padStart(4, '0');
}
async function log(id, entry) {
  await fs.mkdir(TRACE_DIR, { recursive: true });
  await fs.appendFile(tracePath(id), JSON.stringify({ ts: new Date().toISOString(), ...entry }) + '\n', 'utf8');
}
const saveState = (s) => fs.writeFile(statePath(s.id), JSON.stringify(s, null, 2), 'utf8');
export async function loadState(id) {
  try { return JSON.parse(await fs.readFile(statePath(id), 'utf8')); } catch { return null; }
}

function fakeClaude(role, prompt) {
  if (role === 'secretary' && /^\[모드\] 배정$/m.test(prompt)) {
    return '가상 배정입니다.\n```json\n' + JSON.stringify({
      platform: 'blog', topic: '가상 주제',
      instructions: { research: '가상 조사 지시', brief: '가상 브리프 지시', blog: '가상 초안 지시' }
    }) + '\n```';
  }
  return `[가상 응답: ${role}] 처리했습니다.\n결과 파일: 03_결과/가상_${role}.md`;
}

function runClaude(roleKey, prompt) {
  if (process.env.FAKE_CLAUDE) return Promise.resolve(fakeClaude(roleKey, prompt));
  const role = cfg.roles[roleKey];
  const args = ['-p', '--output-format', 'text', '--model', cfg.model, '--permission-mode', 'acceptEdits',
    '--allowedTools', role.tools];
  for (const d of role.addDirs || []) args.push('--add-dir', path.resolve(ROOT, d));
  return new Promise((resolve, reject) => {
    const child = spawn(CLAUDE, args, { cwd: ROOT, windowsHide: true });
    let out = '', err = '';
    const timer = setTimeout(() => { child.kill(); reject(new Error('시간 초과')); }, cfg.timeoutMinutes * 60000);
    child.stdout.on('data', (b) => (out += b));
    child.stderr.on('data', (b) => (err += b));
    child.on('error', (e) => { clearTimeout(timer); reject(e); });
    child.on('close', (code) => {
      clearTimeout(timer);
      const text = (out + '\n' + err).trim();
      if (code === 0) return resolve(out.trim());
      if (/limit|usage|한도|rate/i.test(text)) return reject(new LimitError(text.slice(0, 300)));
      reject(new Error(`종료 코드 ${code}: ${text.slice(0, 300)}`));
    });
    child.stdin.end(prompt, 'utf8');
  });
}

async function rolePrompt(roleKey, id, instruction, context, mode) {
  const role = cfg.roles[roleKey];
  const md = await fs.readFile(path.join(ROOT, role.md), 'utf8');
  return [
    `[당신의 역할 지시서: ${role.md}]`, md, '',
    `[작업번호] ${id}`, mode ? `[모드] ${mode}` : '',
    '[지시]', instruction, '',
    context ? '[앞 단계 결과]\n' + context + '\n' : '',
    '[작업 규칙] 이 폴더(나의_AI업무) 안에서만 읽고 쓴다. 결과는 파일로 저장하고, 답변 마지막 줄에 "결과 파일: <상대경로>"를 쓴다. 답변은 5줄 이내로 요약한다.'
  ].join('\n');
}

async function writeResume(id, why) {
  const note = `# 재개 메모\n- 작업번호: ${id}\n- 멈춘 이유: ${why}\n- 이어 하기: 비서실에서 "${id} 진행"이라고 보내거나, 한도가 풀린 뒤 같은 지시를 다시 보낸다.\n- 기록: 04_기록/추적/${id}.jsonl\n`;
  await fs.writeFile(path.join(ROOT, '04_기록', '재개메모.md'), note, 'utf8');
}

// 한 직원에게 일을 시키고 방에 보이게 남긴다.
async function dispatchTo(roleKey, id, instruction, context, say, fromName = '비서') {
  const role = cfg.roles[roleKey];
  await say(roleKey, `📨 [${id}] ${fromName}의 지시\n${instruction}`);
  const started = Date.now();
  let output;
  try {
    output = await runClaude(roleKey, await rolePrompt(roleKey, id, instruction, context));
  } catch (e) {
    await log(id, { role: roleKey, instruction, error: String(e.message), ms: Date.now() - started });
    if (e instanceof LimitError) {
      await writeResume(id, `${role.name} 실행 중 사용량 제한 신호`);
      await say('secretary', `⏸ [${id}] 사용량 제한 신호가 와서 멈췄어요. 진행 상태는 04_기록/재개메모.md에 저장했어요. 한도가 풀리면 "${id} 진행"이라고 보내 주세요.`);
    } else {
      await say('secretary', `⚠️ [${id}] ${role.name}가 일을 마치지 못했어요: ${e.message}\n"왜 안 됐어? ${id}"라고 물으면 기록을 보고 원인을 찾아볼게요.`);
    }
    throw e;
  }
  await log(id, { role: roleKey, instruction, context: context?.slice(0, 2000), output, ms: Date.now() - started });
  await say(roleKey, `✅ [${id}] ${role.name} 결과\n${output}`);
  return output;
}

function parseDispatch(text) {
  const m = [...text.matchAll(/```json\s*([\s\S]*?)```/g)].pop();
  if (!m) return null;
  try { return JSON.parse(m[1]); } catch { return null; }
}

// 새 지시: 비서 배정 → 조사 → 브리프 → (방향 확인에서 멈춤)
export async function startTask(text, say) {
  const id = await nextId();
  await log(id, { role: 'captain', instruction: text });
  await say('secretary', `📝 [${id}] 지시를 받았어요. 담당을 정할게요.`);
  let secText;
  try {
    secText = await runClaude('secretary', await rolePrompt('secretary', id, text, '', '배정'));
  } catch (e) {
    await log(id, { role: 'secretary', error: String(e.message) });
    await say('secretary', e instanceof LimitError ? `⏸ [${id}] 사용량 제한 신호가 와서 멈췄어요.` : `⚠️ [${id}] 비서가 배정하지 못했어요: ${e.message}`);
    if (e instanceof LimitError) await writeResume(id, '비서 배정 중 사용량 제한');
    return id;
  }
  await log(id, { role: 'secretary', mode: '배정', instruction: text, output: secText });
  const plan = parseDispatch(secText);
  if (!plan?.instructions) {
    await say('secretary', `⚠️ [${id}] 비서의 배정 형식이 맞지 않아 멈췄어요. 원문:\n${secText.slice(0, 1200)}`);
    return id;
  }
  await say('secretary', `📋 [${id}] 배정 완료 (${plan.platform || '플랫폼 미정'} · ${plan.topic || '주제 미정'}). 조사 → 브리프 순서로 진행해요.`);
  const state = { id, text, plan, results: {}, stage: 'running' };
  await saveState(state);
  try {
    let context = '';
    for (const key of cfg.pipeline) {
      const out = await dispatchTo(key, id, plan.instructions[key] || text, context, say);
      state.results[key] = out;
      context = `${cfg.roles[key].name} 결과:\n${out}`;
      await saveState(state);
    }
  } catch { state.stage = 'stopped'; await saveState(state); return id; }
  state.stage = 'await_direction';
  await saveState(state);
  await say('secretary', `🧭 [${id}] 방향 확인이 필요해요. 브리프 요약:\n${(state.results.brief || '').slice(0, 1200)}\n\n이 방향으로 초안을 쓸까요?\n- 그대로면: "${id} 진행"\n- 바꾸려면: "${id} 수정: 바꿀 내용"`);
  return id;
}

// 방향 확인 뒤 발행 AI 호출, 또는 승인안 수정 요청
export async function resumeTask(id, revision, say) {
  const state = await loadState(id);
  if (!state) return say('secretary', `${id} 기록을 찾지 못했어요.`);
  const briefCtx = `작성 직원 브리프:\n${state.results.brief || '(없음)'}`;
  const extra = revision ? `\n캡틴의 수정 방향: ${revision}` : '';
  const prev = state.results.blog ? `\n이전 승인안:\n${state.results.blog}` : '';
  try {
    for (const key of cfg.afterDirection) {
      const out = await dispatchTo(key, id, (state.plan.instructions[key] || state.text) + extra, briefCtx + prev, say);
      state.results[key] = out;
    }
  } catch { state.stage = 'stopped'; await saveState(state); return; }
  state.stage = 'await_approval';
  await saveState(state);
  await say('approval', `🗳 [${id}] 최종 승인안이 올라왔어요.\n${(state.results.blog || '').slice(0, 1500)}`, { approvalFor: id });
}

export async function decide(id, decision, say) {
  const state = await loadState(id);
  if (!state) return;
  await log(id, { role: 'captain', decision });
  state.stage = 'decided:' + decision;
  await saveState(state);
  const msg = {
    approve: '승인됐어요. 발행은 캡틴이 직접 해 주세요. AI는 발행하지 않아요.',
    revise: `수정 요청을 받았어요. 비서실에 "${id} 수정: 바꿀 내용"을 보내 주세요.`,
    reject: '반려됐어요. 이 지시는 여기서 닫아요.'
  }[decision];
  await say('approval', `[${id}] ${msg}`);
}

// "왜 이렇게 나왔어?" → 비서가 기록을 대조해 원인을 가린다.
export async function diagnose(id, question, say) {
  let trace;
  try { trace = await fs.readFile(tracePath(id), 'utf8'); } catch { return say('secretary', `${id} 기록이 없어요.`); }
  await say('secretary', `🔎 [${id}] 기록을 단계별로 대조해 볼게요.`);
  const mdList = Object.values(cfg.roles).filter((r) => r.md).map((r) => r.md).join(', ');
  const ctx = `추적 기록(${id}.jsonl):\n${trace.slice(0, 24000)}\n\n역할 지시서 경로: ${mdList}`;
  try {
    const out = await runClaude('secretary', await rolePrompt('secretary', id, question, ctx, '진단'));
    await log(id, { role: 'secretary', mode: '진단', instruction: question, output: out });
    await say('secretary', out);
  } catch (e) {
    await say('secretary', e instanceof LimitError ? '⏸ 사용량 제한 신호가 와서 진단을 못 했어요.' : `⚠️ 진단 중 오류: ${e.message}`);
  }
}
