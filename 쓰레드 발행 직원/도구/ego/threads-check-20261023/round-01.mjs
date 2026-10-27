const t0 = Date.now();
const task = await taskSpace("threads popular posts check");
const page = task.page("p1");
const t1 = Date.now();
await page.goto("https://www.threads.com/search?q=%EC%9E%90%EC%98%81%EC%97%85&serp_type=default");
await page.waitForLoadState();
await page.waitForTimeout(2500);
const t2 = Date.now();
const posts = await page.evaluate(() => {
  const out = [];
  for (const el of document.querySelectorAll("div[data-pressable-container]")) {
    const text = el.innerText.trim();
    if (text.length > 30) out.push(text.slice(0, 600));
    if (out.length >= 12) break;
  }
  return { url: location.href, title: document.title, count: out.length, posts: out };
});
const t3 = Date.now();
console.log(JSON.stringify({ spaceId: task.spaceId, ms: { space: t1 - t0, load: t2 - t1, extract: t3 - t2, total: t3 - t0 }, ...posts }, null, 1));
