/**
 * 소상공인 체크리스트 구글 폼 만들기
 *
 * script.google.com > 새 프로젝트 > 이 내용 전체를 붙여넣기 > 저장 > 위쪽에서 makeChecklistForm 선택 > 실행.
 * 처음 한 번 권한 허용 창이 뜨면 본인 계정으로 허용합니다. 한 번만 실행하면 됩니다(다시 실행하면 폼이 하나 더 생겨요).
 *
 * 만드는 것
 * - 구글 폼 "소상공인 체크리스트" (로그인 없이, 매번 빈 칸에서 시작, 여러 번 제출 가능)
 * - 응답은 "소상공인 주간 리뷰 정리" 시트의 "체크리스트_전체응답" 탭에 쌓임
 * - 제출될 때마다 가게 이름별 탭("체크_가게이름")에도 한 줄씩 따로 저장
 * - "체크리스트_폼" 탭에 사장님께 보낼 링크와 편집 링크를 적어 둠
 */
const SHEET_ID = '166J4DRXby8TtlsQmXygOkjDGb5q6_DkkPJKUF-JbinQ';
const STORE_Q = '가게 이름을 적어 주세요';

// 질문 정의 (체크리스트 페이지와 같은 내용). type: text | long | num | one | many
const STORE = [
  {type: 'text', q: STORE_Q, required: true},
  {type: 'many', q: '제일 한가한 요일은요?', hint: '여러 개 골라도 돼요', opts: ['월', '화', '수', '목', '금', '토', '일']},
  {type: 'many', q: '제일 한가한 시간은요?', hint: '그 외 시간이면 "기타"에 적어 주세요', opts: ['아침 타임', '점심 타임', '저녁 타임'], other: true},
  {type: 'many', q: '손님들은 보통 어떻게 알고 오세요?', opts: ['지나가다가', '단골·지인 소개', '네이버 지도·검색', '블로그', '인스타그램', '잘 모르겠어요']},
];

const OFFERS = [
  {title: '메뉴판 만들기', price: '크몽 기준 33,000원 → 이번 프로젝트에서는 무료', desc: '가게 메뉴판을 보기 좋게 새로 만들어 드려요.',
    qs: [{type: 'many', q: '어떤 메뉴판이 필요하세요?', opts: ['벽에 거는 메뉴판', '테이블 메뉴판', '가게 밖 입간판']},
         {type: 'one', q: '지금 메뉴판 사진을 찍어 가도 될까요?', opts: ['네', '안 돼요']}]},
  {title: '메뉴 사진 새로 바꾸기', price: '크몽 기준 29,000원 → 이번 프로젝트에서는 무료', desc: '실제 음식을 찍어서 먹음직스럽게 보정해 드려요. 네이버와 메뉴판에 같이 쓸 수 있어요.',
    qs: [{type: 'text', q: '어떤 메뉴부터 바꿀까요?', hint: '메뉴 이름을 적어 주세요. 예: 김치찌개, 제육볶음'},
         {type: 'one', q: '음식 사진은 언제 찍으면 편하세요?', opts: ['장사 시작 전', '한가한 시간', '아무 때나 괜찮아요']}]},
  {title: '가게 포스터 만들기', price: '크몽 기준 8,000원부터(장수에 따라 달라요) → 이번 프로젝트에서는 무료', desc: '유리문이나 벽에 붙일 포스터를 만들어 드려요. 크기는 가로 212mm × 세로 299mm예요(A4보다 조금 커요).',
    qs: [{type: 'long', q: '포스터에 넣을 글을 적어 주세요', hint: '적어 주신 그대로 들어가요. 띄어쓰기도 그대로예요.'},
         {type: 'num', q: '몇 장 필요하세요?'},
         {type: 'many', q: '어디에 붙이실 거예요?', opts: ['가게 유리문·바깥', '가게 안 벽', '아파트·동네 게시판']}]},
  {title: '외국인 손님용 QR 메뉴판', price: '크몽 기준 30,000원 → 이번 프로젝트에서는 무료', desc: '휴대폰으로 QR을 찍으면 번역된 메뉴판이 나와요. 테이블에 세워 두는 작은 카드로 만들어 드려요.',
    qs: [{type: 'one', q: '외국인 손님이 오시나요?', opts: ['자주 와요', '가끔 와요', '거의 없어요']},
         {type: 'many', q: '어느 나라 말로 할까요?', opts: ['영어', '중국어', '일본어', '베트남어']},
         {type: 'num', q: '테이블이 몇 개예요?', hint: '카드를 테이블 수만큼 만들어요'},
         {type: 'one', q: 'QR용으로 메뉴판 사진을 찍어 가도 될까요?', opts: ['네', '안 돼요']}]},
  {title: '홈페이지 제작', price: '크몽 기준 200,000원 · 유료 (무료 제공 대상이 아니에요)', desc: '가게 소개, 메뉴, 오시는 길을 담은 홈페이지를 만들어 드려요.',
    qs: [{type: 'many', q: '홈페이지에 꼭 넣고 싶은 건요?', opts: ['메뉴·가격', '오시는 길', '전화·예약', '가게 사진', '사장님 이야기']},
         {type: 'one', q: '지금 쓰는 홈페이지가 있나요?', opts: ['있어요', '없어요']}]},
  {title: '포토카드 + 인스타 올리기', price: '준비 중 · 가격 미정', desc: '메뉴 사진으로 포토카드를 만들고, 먹스타그램 같은 곳에 올려 드려요. 지금 준비하고 있어요.',
    qs: [{type: 'one', q: '가게 인스타그램이 있나요?', opts: ['있어요', '없는데 만들어도 돼요', '없고 안 만들래요']},
         {type: 'text', q: '있으시면 계정을 적어 주세요', hint: '예: @gage_insta'},
         {type: 'one', q: '사장님 얼굴이나 목소리가 나와도 될까요?', opts: ['얼굴·목소리 다 괜찮아요', '손·음식만 나오게', '안 나오게']}]},
];

const ETC = [
  {type: 'text', q: '마케팅 업체와 계약 중이시면, 언제 끝나요?', hint: "업체가 없으면 '없음', 모르시면 '모름'이라고 적어 주세요"},
  {type: 'one', q: '네이버 가게 정보는 누가 고치세요?', opts: ['사장님', '가족', '마케팅 업체', '잘 모르겠어요']},
];

const CHOICES = ['해주세요', '나중에', '괜찮아요'];

function addQ(form, d) {
  let it;
  if (d.type === 'text') it = form.addTextItem();
  else if (d.type === 'long') it = form.addParagraphTextItem();
  else if (d.type === 'num') {
    it = form.addTextItem();
    it.setValidation(FormApp.createTextValidation().setHelpText('숫자만 적어 주세요').requireWholeNumber().build());
  } else if (d.type === 'one') {
    it = form.addMultipleChoiceItem().setChoiceValues(d.opts);
  } else {
    it = form.addCheckboxItem().setChoiceValues(d.opts);
    if (d.other) it.showOtherOption(true);
  }
  it.setTitle(d.q);
  if (d.hint) it.setHelpText(d.hint);
  if (d.required) it.setRequired(true);
  return it;
}

function makeChecklistForm() {
  const form = FormApp.create('소상공인 체크리스트');
  form.setDescription('소상공인 문제해결 프로젝트\n\n5분이면 끝나요. 모르는 건 건너뛰셔도 돼요.\n' +
      '적힌 가격은 크몽에서 비슷한 서비스가 팔리는 가격이에요. 이번 프로젝트에서는 무료로 해 드려요. 홈페이지 제작만 유료예요.')
    .setCollectEmail(false)
    .setLimitOneResponsePerUser(false)
    .setAllowResponseEdits(false)
    .setShowLinkToRespondAgain(false)
    .setProgressBar(true)
    .setConfirmationMessage('보내 주셔서 감사해요. 확인하고 바로 연락드릴게요.');
  try { form.setRequireLogin(false); } catch (e) {} // 회사 계정에서만 쓰는 설정이라 개인 계정이면 넘어감

  form.addSectionHeaderItem().setTitle('가게 이야기');
  STORE.forEach(d => addQ(form, d));

  // 서비스마다: 고르기 페이지 → (해주세요일 때만) 추가 질문 페이지 → 다음 서비스
  const pages = OFFERS.map(o => {
    const pick = form.addPageBreakItem().setTitle(o.title).setHelpText(o.price + '\n' + o.desc);
    const mc = form.addMultipleChoiceItem().setTitle(o.title + ', 해 드릴까요?').setRequired(true);
    const more = form.addPageBreakItem().setTitle(o.title + ' · 몇 가지만 더 여쭤볼게요');
    o.qs.forEach(d => addQ(form, d));
    return {pick, mc, more};
  });
  const etc = form.addPageBreakItem().setTitle('마지막으로 두 가지만');
  ETC.forEach(d => addQ(form, d));

  pages.forEach((p, i) => {
    const next = i + 1 < pages.length ? pages[i + 1].pick : etc;
    p.mc.setChoices([
      p.mc.createChoice(CHOICES[0], p.more),
      p.mc.createChoice(CHOICES[1], next),
      p.mc.createChoice(CHOICES[2], next),
    ]);
  });

  form.setDestination(FormApp.DestinationType.SPREADSHEET, SHEET_ID);
  SpreadsheetApp.flush();
  Utilities.sleep(3000);
  const ss = SpreadsheetApp.openById(SHEET_ID);
  const formId = form.getId();
  ss.getSheets().forEach(sh => {
    const url = sh.getFormUrl();
    if (url && url.indexOf(formId) >= 0) sh.setName('체크리스트_전체응답');
  });

  let info = ss.getSheetByName('체크리스트_폼') || ss.insertSheet('체크리스트_폼');
  info.clear();
  info.getRange(1, 1, 4, 2).setValues([
    ['사장님께 보낼 링크', form.shortenFormUrl(form.getPublishedUrl())],
    ['폼 편집 링크', form.getEditUrl()],
    ['폼 ID', formId],
    ['만든 날', new Date()],
  ]);

  ScriptApp.newTrigger('onChecklistSubmit').forForm(form).onFormSubmit().create();
  Logger.log('사장님께 보낼 링크: ' + form.getPublishedUrl());
}

// ── 2페이지 + 예시 사진 버전으로 이미 만든 폼을 다시 짜기 (링크는 그대로) ──
// 구글 드라이브 "체크리스트_예시사진" 폴더에 ex-*.jpg 사진 5장을 먼저 올린 뒤 rebuildChecklistForm 을 실행합니다.
const FORM_ID = '1rllPn_FGWz2EP9AAb75F-7UpuKAgjVqfPoY1O__ZmIs';
const IMG_FOLDER_ID = '13ezMlaGtMxm8ze9YtZ_BidI4DdWAafP4';
const IMG = {  // 서비스 제목 → 예시 사진 파일 이름 (QR 메뉴판은 아직 예시가 없어 사진 없음)
  '메뉴판 만들기': ['ex-board.jpg', '예시 이미지예요. 실제 메뉴판은 가게 메뉴로 새로 만들어요.'],
  '메뉴 사진 새로 바꾸기': ['ex-photo.jpg', '실제 작업 예시: 숙이네 밥상 생선찌개, 왼쪽이 원래 사진이에요.'],
  '가게 포스터 만들기': ['ex-poster.jpg', '실제 작업 예시: 숙이네 밥상 홍보 포스터'],
  '홈페이지 제작': ['ex-home.jpg', '예시 이미지예요. 메뉴, 오시는 길, 예약을 한 페이지에 담아요.'],
  '포토카드 + 인스타 올리기': ['ex-card.jpg', '실제 작업 예시: 숙이네 밥상 인스타용 카드'],
};

function rebuildChecklistForm() {
  const form = FormApp.openById(FORM_ID);
  const folder = DriveApp.getFolderById(IMG_FOLDER_ID);
  const blobOf = name => {
    const it = folder.getFilesByName(name);
    if (!it.hasNext()) throw new Error('드라이브 "체크리스트_예시사진" 폴더에 ' + name + ' 이(가) 없습니다. 사진 5장을 먼저 올려 주세요.');
    return it.next().getBlob();
  };
  Object.keys(IMG).forEach(k => blobOf(IMG[k][0]));  // 지우기 전에 사진이 다 있는지 먼저 확인

  form.getItems().forEach(it => form.deleteItem(it));

  // 1페이지: 가게 이야기 + 서비스 전부
  form.addSectionHeaderItem().setTitle('가게 이야기');
  STORE.forEach(d => addQ(form, d));
  OFFERS.forEach(o => {
    form.addSectionHeaderItem().setTitle(o.title).setHelpText(o.price + '\n' + o.desc);
    if (IMG[o.title]) form.addImageItem().setImage(blobOf(IMG[o.title][0])).setHelpText(IMG[o.title][1]);
    form.addMultipleChoiceItem().setTitle(o.title + ', 해 드릴까요?').setChoiceValues(CHOICES).setRequired(true);
    o.qs.forEach(d => addQ(form, Object.assign({}, d, {hint: (d.hint ? d.hint + ' · ' : '') + "'해주세요'를 고르셨을 때만 적어 주세요"})));
  });

  // 2페이지: 마지막 질문
  form.addPageBreakItem().setTitle('마지막으로 두 가지만');
  ETC.forEach(d => addQ(form, d));
  Logger.log('다시 짰어요. 링크는 그대로입니다: ' + form.getPublishedUrl());
}

// 여분 폼 2개(이미 휴지통)를 시트에서 연결 해제하고, 빈 응답 탭 2개를 지운다. 한 번만 실행.
function cleanupExtraForms() {
  ['1M9n4UXGzWhUMyxA2yzWZ4BURdyuW1BFD0hPJpi_I9us', '1lhSOWxndMMhew4JgP249hgHEJztRwQBlakzyEnxEQ_8'].forEach(id => {
    try { FormApp.openById(id).removeDestination(); } catch (e) { Logger.log(id + ' 연결 해제 실패: ' + e); }
  });
  SpreadsheetApp.flush();
  const ss = SpreadsheetApp.openById(SHEET_ID);
  ['설문지 응답 시트2', '설문지 응답 시트3'].forEach(name => {
    const sh = ss.getSheetByName(name);
    if (!sh) return;
    if (sh.getLastRow() > 1) { Logger.log(name + ' 에 응답이 있어 지우지 않았어요.'); return; }
    ss.deleteSheet(sh);
    Logger.log(name + ' 지움');
  });
}

// 제출될 때마다 가게 이름별 탭에 한 줄 저장
function onChecklistSubmit(e) {
  const answers = e.response.getItemResponses();
  const titles = answers.map(r => r.getItem().getTitle());
  const values = answers.map(r => {
    const v = r.getResponse();
    return Array.isArray(v) ? v.join(', ') : v;
  });
  const nameAt = titles.indexOf(STORE_Q);
  const store = String(nameAt >= 0 ? values[nameAt] : '이름 없음').trim() || '이름 없음';
  const tab = ('체크_' + store).replace(/[\[\]\*\?\/\\:]/g, ' ').slice(0, 90);

  const ss = SpreadsheetApp.openById(SHEET_ID);
  const sh = ss.getSheetByName(tab) || ss.insertSheet(tab);
  if (sh.getLastRow() === 0) sh.appendRow(['제출 시각'].concat(titles));
  // 질문 구성이 제출마다 달라서(해주세요를 고른 서비스만 추가 질문이 있음) 항목:답 형태로도 남긴다
  const header = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
  const row = new Array(header.length).fill('');
  row[0] = e.response.getTimestamp();
  titles.forEach((t, i) => {
    let col = header.indexOf(t);
    if (col < 0) {
      col = header.length;
      header.push(t);
      sh.getRange(1, col + 1).setValue(t);
      row.push('');
    }
    row[col] = values[i];
  });
  sh.appendRow(row);
}
