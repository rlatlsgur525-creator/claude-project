// 디스코드와 클로드 없이 지시 흐름·기록·진단 경로만 확인하는 시험. 사용량을 쓰지 않는다.
process.env.FAKE_CLAUDE = '1';
const { startTask, resumeTask, decide, diagnose, loadState } = await import('./orchestrator.mjs');
const lines = [];
const say = async (role, text) => { lines.push(`#${role}: ${String(text).split('\n')[0]}`); };

const id = await startTask('가상 시험: 오늘 블로그 글 준비해 줘', say);
const s1 = await loadState(id);
await resumeTask(id, '도입을 더 짧게', say);
await decide(id, 'approve', say);
await diagnose(id, `왜 이렇게 나왔어? ${id}`, say);
const s2 = await loadState(id);
console.log(lines.join('\n'));
console.log({ id, 방향확인_상태: s1.stage, 최종_상태: s2.stage });
