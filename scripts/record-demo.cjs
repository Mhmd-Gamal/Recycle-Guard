const {chromium}=require('playwright');const fs=require('node:fs');const path=require('node:path');
(async()=>{
 const output=path.resolve('artifacts/demo');fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({channel:process.env.RG_BROWSER_CHANNEL||'chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1080},recordVideo:{dir:output,size:{width:1440,height:1080}}});
 const page=await context.newPage();
 await page.goto(process.env.RG_BASE_URL || 'http://127.0.0.1:8765');await page.waitForFunction(()=>document.querySelector('#status').textContent==='Active');
 // Recording-only pacing; verification lives in tests/browser.cjs.
 const pause=ms=>new Promise(r=>setTimeout(r,ms));
 async function caption(text){await page.evaluate(text=>{let el=document.querySelector('#demo-caption');if(!el){el=document.createElement('div');el.id='demo-caption';el.style='position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:100;background:#142e26;color:#fff;padding:16px 28px;border-radius:8px;font:600 16px Segoe UI;box-shadow:0 5px 30px #0003;white-space:nowrap;max-width:96vw';document.body.append(el)}el.textContent=text},text);await pause(3500)}
 await caption('RecycleGuard · Browser demonstration of the shared C# simulation');
 await page.selectOption('#scenario','dropout');await page.fill('#seed','42');await page.click('#reset');await pause(400);
 await caption('Seed 42 · Sensor dropout makes uncertainty visible');
 await page.click('#advise');await page.locator('[data-decision="accept"]').waitFor();
 await caption('Offline test proposals + explicit constraints · No LLM claims');
 await page.click('[data-decision="alternative"]');await page.waitForFunction(()=>!document.body.classList.contains('busy'));
 await caption('The operator can request alternatives and inspect the evidence');
 await page.fill('#note','Need current evidence before committing resources');await page.click('[data-decision="reject"]');await pause(400);
 await caption('Rejecting a suggestion does not advance simulation time');
 await page.selectOption('#action','suppress');await page.locator('[data-zone="0"]').click();await page.click('#manual');await pause(500);
 await caption('The C# engine independently blocks an invalid manual action');
 await page.click('#reset');await page.waitForFunction(()=>document.querySelector('#tick').textContent==='00');
 await caption('Every action needs human approval · Fresh evidence before commitment');
 for(let i=0;i<32&&await page.locator('#status').innerText()==='Active';i++){
  await page.click('#advise');await page.locator('[data-decision="accept"]').waitFor();await pause(600);
  await page.click('[data-decision="accept"]');await page.waitForFunction(()=>!document.body.classList.contains('busy'));await pause(450);
 }
 await caption('Incident contained · Resource use and every decision are recorded');
 const dp=page.waitForEvent('download');await page.click('#export');const download=await dp;
 const rp=path.join(output,'demo-replay.json');await download.saveAs(rp);
 await page.setInputFiles('#replay-file',rp);await page.locator('#replay-controls').waitFor({state:'visible'});await page.locator('#replay-controls').scrollIntoViewIfNeeded();
 await caption('Exported replay verified by re-running the authoritative C# model');
 await page.locator('#replay-slider').fill('10');await page.locator('#replay-slider').dispatchEvent('input');await pause(1800);
 await page.locator('#exit-replay').click();await page.locator('header').scrollIntoViewIfNeeded();
 await caption('Unity client source included · Unity build validation remains pending');
 const video=page.video();await context.close();await video.saveAs(path.join(output,'RecycleGuard-browser-demo.webm'));await browser.close();
 console.log('Saved browser demonstration video. This is not Unity footage.');
})().catch(e=>{console.error(e);process.exit(1)});
