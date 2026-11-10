const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async()=>{
  const out=path.resolve('artifacts/browser'); fs.mkdirSync(out,{recursive:true});
  const browser=await chromium.launch({channel:process.env.RG_BROWSER_CHANNEL||'chrome',headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1100},deviceScaleFactor:1});
  const page=await context.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.RG_BASE_URL || 'http://127.0.0.1:8765');
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='Active');
  await page.screenshot({path:path.join(out,'01-overview.png'),fullPage:true});
  assert.equal(await page.locator('.zone').count(),4);
  // Missing observations must be shown as unknown rather than zero.
  await page.selectOption('#scenario','dropout'); await page.fill('#seed','42');await page.click('#reset');
  await page.waitForFunction(()=>document.querySelectorAll('.zone.uncertain').length>0);
  assert.match(await page.locator('#zones').innerText(),/Heat \?/);
  await page.click('#advise'); await page.locator('[data-decision="accept"]').waitFor();
  await page.waitForFunction(()=>!document.body.classList.contains('busy'));
  const first=await page.locator('.advice-card h3').innerText();
  await page.screenshot({path:path.join(out,'02-evidence.png'),fullPage:true});
  await page.click('[data-decision="alternative"]');
  await page.waitForFunction(()=>!document.body.classList.contains('busy'));
  assert.match(await page.locator('#trail').innerText(),/alternative/i);
  await page.fill('#note','Review alternative evidence before acting');
  await page.click('[data-decision="reject"]');
  await page.waitForFunction(()=>!document.body.classList.contains('busy'));
  assert.equal(await page.locator('#tick').innerText(),'00');
  await page.locator('[data-zone="0"]').click(); await page.selectOption('#action','suppress');
  await page.click('#manual'); await page.waitForFunction(()=>document.querySelector('#tick').textContent==='01');
  await page.waitForFunction(()=>!document.body.classList.contains('busy'));
  assert.match(await page.locator('#trail').innerText(),/EVIDENCE|POWER/);
  assert.equal(await page.locator('#water').innerText(),'18');
  // Execute a complete checked episode using visible controls only.
  await page.click('#reset');await page.waitForFunction(()=>document.querySelector('#tick').textContent==='00');
  let steps=0;
  while(await page.locator('#status').innerText()==='Active' && steps<32){
    await page.click('#advise');await page.locator('[data-decision="accept"]').waitFor();
    await page.click('[data-decision="accept"]');
    await page.waitForFunction(()=>!document.body.classList.contains('busy'));steps++;
  }
  assert.equal(await page.locator('#status').innerText(),'Contained');
  assert.ok(steps>3 && steps<=32);
  await page.screenshot({path:path.join(out,'03-contained.png'),fullPage:true});
  const downloadPromise=page.waitForEvent('download');await page.click('#export');
  const download=await downloadPromise;const replayPath=path.join(out,'browser-replay.json');await download.saveAs(replayPath);
  await page.setInputFiles('#replay-file',replayPath);await page.locator('#replay-controls').waitFor({state:'visible'});
  assert.match(await page.locator('#replay-label').innerText(),/VERIFIED REPLAY/);
  await page.screenshot({path:path.join(out,'04-replay.png'),fullPage:true});
  await page.click('#exit-replay');await page.waitForFunction(()=>document.querySelector('#replay-controls').hidden);
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(out,'05-mobile.png'),fullPage:true});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal mobile overflow');
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({passed:true,checks:['initial render','unknown evidence','advice','alternative','rejection without time advance','invalid manual action blocked','complete checked episode','export','verified replay','mobile overflow','no JS errors'],episode_steps:steps,browser:await browser.version()},null,2));
  await context.close();await browser.close();console.log('Browser end-to-end checks passed; episode steps:',steps);
})().catch(e=>{console.error(e);process.exit(1)});
