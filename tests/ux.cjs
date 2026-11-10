const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const axePath=require.resolve('axe-core/axe.min.js');

(async()=>{
  const output=path.resolve('artifacts/redesign');fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({channel:process.env.RG_BROWSER_CHANNEL||'chrome',headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1100}});
  const page=await context.newPage();const checks=[],violations=[],errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  const idle=()=>page.waitForFunction(()=>!document.body.classList.contains('busy'));
  const check=(name)=>checks.push(name);
  await page.goto(process.env.RG_BASE_URL||'http://127.0.0.1:8765');
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='Active');await idle();
  await page.locator('[data-zone="0"]').focus();await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('[data-zone="1"]').getAttribute('aria-pressed'),'true');
  assert.equal(await page.evaluate(()=>document.activeElement.dataset.zone),'1');check('Arrow-key zone selection preserves focus and pressed state');
  await page.fill('#seed','');await page.click('#reset');await idle();
  assert.equal(await page.locator('#seed-error').isVisible(),true);
  assert.equal(await page.evaluate(()=>document.activeElement.id),'seed');check('Inline seed validation and focus');
  await page.fill('#seed','42');await page.selectOption('#scenario','dropout');await page.click('#reset');await idle();
  await page.click('#advise');await idle();await page.locator('[data-decision="accept"]').waitFor();
  await page.selectOption('#action','evacuate');await page.locator('[data-zone="2"]').click();
  assert.match(await page.locator('[data-decision="modify"]').innerText(),/evacuate \/ Materials store/);check('Manual substitution names the action and target');
  await page.locator('.plan summary').click();assert.equal(await page.locator('.plan').getAttribute('open'),'');check('Conditional plan disclosure');
  await page.click('[data-filter="decisions"]');assert.match(await page.locator('#trail').innerText(),/No events match/);
  await page.click('[data-filter="advice"]');assert.match(await page.locator('#trail').innerText(),/Advice/);check('Decision trail filters');
  await page.click('[data-filter="all"]');await page.click('[data-decision="reject"]');await idle();
  assert.equal(await page.locator('#tick').innerText(),'00');check('Rejection retains incident time');
  await page.click('#advise');await idle();
  const downloadEvent=page.waitForEvent('download');await page.click('#export');const download=await downloadEvent;
  const replayFile=path.join(output,'ux-replay.json');await download.saveAs(replayFile);await idle();
  await page.setInputFiles('#replay-file',replayFile);await idle();await page.locator('#replay-banner').waitFor({state:'visible'});
  assert.match(await page.locator('#advice').innerText(),/Live recommendations are hidden/);
  assert.equal(await page.locator('#advise').isDisabled(),true);assert.match(await page.locator('#view-badge').innerText(),/Replay truth/);check('Replay separates recorded truth from live advice');
  await page.click('#replay-next');assert.equal(await page.locator('#replay-slider').inputValue(),'1');
  await page.click('#replay-prev');assert.equal(await page.locator('#replay-slider').inputValue(),'0');check('Replay has non-drag controls');
  await page.click('#exit-replay-top');await idle();assert.equal(await page.locator('#replay-banner').isVisible(),false);check('Return to live restores adviser');
  await page.route('**/v1/sessions/*/advice',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Test provider unavailable. Retry or select offline mode.'})}));
  await page.click('#advise');await idle();assert.match(await page.locator('#error-banner').innerText(),/Test provider unavailable/);
  await page.click('#dismiss-error');assert.equal(await page.locator('#error-banner').isVisible(),false);check('Persistent dismissible API error');
  await page.unroute('**/v1/sessions/*/advice');
  await page.selectOption('#mode','scripted');assert.equal(await page.locator('[data-decision="accept"]').count(),0);check('Policy changes clear obsolete visible advice');
  await page.selectOption('#mode','offline_checked');await page.click('#advise');await idle();
  await page.locator('#adviser-panel').scrollIntoViewIfNeeded();
  // Wait for temporary status messages to clear before visual evidence capture.
  await page.waitForFunction(()=>!document.querySelector('#toast').classList.contains('show'));
  for(const width of [375,768,1024,1440]){
    await page.setViewportSize({width,height:1000});await page.evaluate(()=>scrollTo(0,0));
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`No overflow at ${width}`);
    await page.addScriptTag({path:axePath});
    const report=await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}}));
    violations.push(...report.violations.map(v=>({width,id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})));
    await page.screenshot({path:path.join(output,`workspace-${width}.png`),fullPage:true});
    check(`Responsive layout and WCAG automated scan at ${width}px`);
  }
  await page.setViewportSize({width:844,height:390});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));check('Landscape layout');
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior),'auto');
  assert.equal(await page.evaluate(()=>getComputedStyle(document.querySelector('.primary')).transitionDuration),'0s');check('Reduced motion');
  // Browser zoom reduces the CSS viewport. CSS zoom is not equivalent because it
  // does not update media-query breakpoints; test the equivalent layout viewport.
  await page.setViewportSize({width:375,height:500});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Zoom-equivalent reflow');check('375px CSS viewport reflow (200%-zoom equivalent on a 750px viewport)');
  fs.writeFileSync(path.join(output,'ux-results.json'),JSON.stringify({passed:violations.length===0&&errors.length===0,checks,axe_version:require('axe-core').version,violations,js_errors:errors,note:'Automated checks are not a full accessibility conformance audit.'},null,2));
  await context.close();await browser.close();assert.deepEqual(errors,[]);assert.deepEqual(violations,[]);
  console.log('UI/UX regression checks passed:',checks.length);
})().catch(error=>{console.error(error);process.exit(1)});
