// report.html -> 카톡으로 보낼 PNG 이미지들.
//   node render.mjs <store_dir> [<out_dir>]
// <out_dir>(기본: <store_dir>/out)에 01_요약.png ... 05_점수기준.png 와 00_전체.png 를 만듭니다.
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const storeDir = path.resolve(process.argv[2] ?? "");
const outDir = path.resolve(process.argv[3] ?? path.join(storeDir, "out"));
const html = path.join(storeDir, "report.html");
if (!fs.existsSync(html)) {
  console.error(`report.html이 없습니다: ${html}. build.py를 먼저 실행하세요.`);
  process.exit(1);
}
const browsers = [
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
];
const executablePath = browsers.find((p) => fs.existsSync(p));
if (!executablePath) {
  console.error("Edge나 Chrome을 찾지 못했습니다.");
  process.exit(1);
}
fs.mkdirSync(outDir, { recursive: true });

const browser = await puppeteer.launch({ executablePath, headless: true, args: ["--allow-file-access-from-files"] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 430, height: 900, deviceScaleFactor: 2 });
  await page.goto(pathToFileURL(html).href, { waitUntil: "networkidle0", timeout: 60000 });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map((im) => (im.complete ? 0 : new Promise((r) => { im.onload = im.onerror = r; }))));
  });
  const broken = await page.evaluate(() => [...document.images].filter((im) => !im.naturalWidth).map((im) => im.getAttribute("src")));
  if (broken.length) console.warn("사진을 못 불러왔습니다: " + broken.join(", "));
  const font = await page.evaluate(() => document.fonts.check("16px 'Noto Sans KR'"));
  if (!font) console.warn("Noto Sans KR 글꼴을 못 불러와 맑은 고딕으로 그렸습니다 (인터넷 연결 확인).");

  const shots = await page.$$("[data-shot]");
  for (const el of shots) {
    const name = await el.evaluate((n) => n.dataset.shot);
    await el.screenshot({ path: path.join(outDir, `${name}.png`) });
    console.log("saved", path.join(outDir, `${name}.png`));
  }
  await page.screenshot({ path: path.join(outDir, "00_전체.png"), fullPage: true });
  console.log("saved", path.join(outDir, "00_전체.png"));
} finally {
  await browser.close();
}
