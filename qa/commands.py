"""Exercise the live R3.0 demo in independent Chromium contexts."""
import csv
import io
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.request import urlopen

URL = "https://pal1126.github.io/NNC-ISTC-Task/"
source = urlopen(URL).read().decode()
dispatcher = source.split('function run(act,v){')[1].split("document.addEventListener")[0]
expected = set(re.findall(r"act==='([^']+)'", dispatcher))
for group in re.findall(r"\[([^\]]*)\]\.includes\(act\)", dispatcher):
    expected.update(re.findall(r"'([^']+)'", group))
results = []
# route | command | argument (JS expression) | expected postcondition
cases = """
0|sections||D
0|openSection|7|st.page===7
7|boardHome||st.page===0 && document.body.classList.contains('wall')
0|screen||!!document.fullscreenElement
0|workspace||!document.body.classList.contains('wall')
0|nav|1|st.page===1
1|site|'S-003'|st.site==='S-003'
1|pins||st.mapPins!==before.mapPins
1|siteObjects|'S-003'|st.page===2 && st.objQ==='S-003'
2|previous||st.page===1
0|siteCard|'S-003'|st.page===1
1|siteReport|'S-003'|st.natSite==='S-003' && st.page===8
8|basisBoard|'Прогноз'|st.basis==='Прогноз'
8|coverage||!!document.querySelector('#decls') && inView('decls')
8|clearPageFilters||!st.natSite && !st.basis
8|annualHome||document.activeElement.id==='annualCompare'
8|receiptHome||document.activeElement.id==='receiptArea'
2|object|'W-002'|st.object==='W-002' && st.page===2
2|pickObj|'W-001'|st.object==='W-001'
2|inventoryCard|'W-001'|D
2|volumeEvidence|'W-001'|ob('W-001').volumeEvidence.ref==='QA'
8|variantAdd|'W-002'|planningVariants.some(x=>x.label==='QA')
8|variantCSV|'W-002'|FILE
8|capacity|capacityRecords[0].facility|D
8|capacityCsv|capacityRecords[0].facility|FILE
8|streamCard|demoStreams[0].id|D
8|streamFile|demoStreams[0].id|FILE
8|legacySite|'S-001'|st.page===8 && st.natSite==='S-001'
8|legacyCard|legacySites[0].id|D
8|legacyCsv||FILE
8|processDetails|processLedger[0].id|D
8|processCSV|processLedger[0].id|FILE
8|sectorCsv||FILE
8|classCSV||FILE
8|annualCsv||FILE
8|stockCsv||FILE
2|objCsv||FILE
3|stationOpen|'P-001'|st.page===3 && st.measure==='P-001' && st.period==='all'
3|measurement|measures[0].id|D
3|corrected||st.showCorrected!==before.showCorrected
3|measCsv||FILE
4|reviewObj|'W-002'|D
4|correctObj|'W-002'|ob('W-002').scenario==='QA'
4|approve|'W-002'|ob('W-002').status==='Утверждено'
4|return|'W-002'|ob('W-002').status.includes('уточн')
4|report||reports.some(r=>!r.cycle)
4|snap|0|FILE
8|nationalFreeze||reports.at(-1).cycle
8|versionDetail|reports.length-1|D
8|frozenCsv|reports.length-1|FILE
8|releaseFile|reports.length-1|FILE
8|print||window.__printCalled
5|ticket||tickets.has('qa-test')
5|dictJson||FILE
5|dictCsv||FILE
6|inspectQueue||st.inspectionTerm==='Просрочен'
6|inspection|'PKG-003'|st.pkgQ==='PKG-003'
6|pickPkg|'PKG-004'|st.pkg==='PKG-004'
6|inspect|'PKG-004'|pk('PKG-004').notes==='QA'
6|addObservation|'PKG-004'|inspectionLog[0].source==='QA'
6|inspectSubmit|'PKG-004'|inspectionPending.has('PKG-004')
6|inspectReview|'PKG-004'|D
6|inspectReturn|'PKG-004'|!inspectionPending.has('PKG-004') && inspectionLog[0].scope.includes('возвращена')
6|inspectSubmit|'PKG-004'|inspectionPending.has('PKG-004')
6|inspectApprove|'PKG-004'|!inspectionPending.has('PKG-004') && pk('PKG-004').next==='2027-01-01'
6|state|'На хранении'|st.pkgFilter==='На хранении'
6|pkgCsv||FILE
6|passport|'PKG-004'|st.page===11 && st.tab==='Паспорт'
11|tab|'История'|st.tab==='История'
11|assayCsv||FILE
11|evidence|assays[0].source_ref|D
9|case|'PKG-003'|st.selectedCase==='PKG-003'
9|request|'PKG-003'|requests.at(-1).q==='QA'
9|reply|requests.at(-1).id|requests.at(-1).reply==='QA'
9|verify|requests.at(-1).id|requests.at(-1).state==='Закрыто'
7|pkgTrip|0|st.page===7 && st.min===0
7|play||timer!==null
7|step|1|st.min>0 && timer===null
7|at|0|st.min===0
7|tripFile||FILE
12|reserve||moves[0].status==='Зарезервировано'
12|cancelMove|moves[0].id|moves[0].status==='Отменено'
12|reserve||moves[0].status==='Зарезервировано'
12|moveCheck|moves[0].id|moves[0].status==='Проверено'
12|dispatch|moves[0].id|moves[0].status==='В пути'
12|receive|moves[0].id|moves[0].status==='Принято' && pk('PKG-003').place===moves[0].to
12|manifest||manifests.length>0
12|manifestFile|0|FILE
12|receiptEntry|0|receiptHistory.get(manifests[0].id).at(-1).clean
12|receiptCheck|0|receiptHistory.get(manifests[0].id).at(-1).checked
13|sample|'good'|importText===demoIngestCSV09(false)
13|template||FILE
13|precheck||staged.a.counts.new>0
13|rawLine|staged.a.rows[0].line|D
13|commit||staged.accepted && batchLog.length===1
13|receipt|0|FILE
10|refs||FILE
10|jumpTop||scrollY===0 && document.activeElement.id==='main'
""".strip().splitlines()
edit=set('volumeEvidence variantAdd correctObj ticket inspect addObservation inspectSubmit reply reserve cancelMove dispatch manifest receiptEntry precheck'.split())
forms=set('volumeEvidence variantAdd correctObj approve return inspect addObservation inspectSubmit inspectReturn request reply verify receiptEntry'.split())
fields=dict(day='2026-11-20',iday='2026-11-20',inext='2027-01-01',startDay='2027-01-01',endDay='2027-12-31',refday='2026-11-20',estimate='2',low='0.9',high='1.1')
fields.update({'from':'2027','to':'2028'})
assert {c.split('|')[1] for c in cases}==expected
with sync_playwright() as pw:
    browser=pw.chromium.launch()
    for size,w,h in [('wall',1920,1080),('tablet',820,1180),('phone',390,844)]:
        page=browser.new_page(viewport={'width':w,'height':h},has_touch=size!='wall',is_mobile=size!='wall')
        page.set_default_timeout(1800)
        page.goto(URL)
        page.evaluate("window.inView=id=>{let r=document.getElementById(id).getBoundingClientRect(); return r.top>=-2 && r.top<innerHeight}; window.print=()=>window.__printCalled=true")
        for line in cases:
            n,cmd,arg,check=line.split('|',3)
            method='handler'
            detail=''
            try:
                role='edit' if cmd in edit else 'review'
                page.evaluate("""([n,cmd,role])=>{
                    if($('dlg').open && !['openSection','inspectApprove','inspectReturn'].includes(cmd)) $('dlg').close();
                    if(st.page!==n)nav(n);
                    if(st.role!==role){$('role').value=role;$('role').dispatchEvent(new Event('change'))}
                    if(cmd==='ticket'){st.fields='qa-test';render()}
                    if(cmd==='reserve'){st.slot=slots().find(s=>s!==pk('PKG-003').place);render()}
                    window.before={...st}
                }""",[int(n),cmd,role])
                value=str(page.evaluate("String("+ (arg or "''") +")"))
                buttons=page.locator('[data-act="'+cmd+'"]' + ('[data-v="'+value+'"]' if arg else '')+':visible:enabled')
                def invoke():
                    global method
                    if buttons.count() and not(page.locator('#dlg').is_visible() and not buttons.first.evaluate("e=>!!e.closest('dialog')")):
                        if size=='wall':buttons.first.click()
                        else:buttons.first.tap()
                        method='click' if size=='wall' else 'tap'
                    else:page.evaluate('([c,v])=>{run(c,v)}',[cmd,value])
                if check=='FILE':
                    with page.expect_download() as event:invoke()
                    d=event.value
                    raw=Path(d.path()).read_bytes()
                    assert raw
                    content=raw.decode('utf-8-sig')
                    if d.suggested_filename.endswith('.json'):json.loads(content)
                    elif d.suggested_filename.endswith('.csv'):assert len(next(csv.reader(io.StringIO(content))))>1
                    elif d.suggested_filename.endswith('.html'):assert '<html' in content.lower()
                    detail=d.suggested_filename+' '+str(len(raw))
                else:
                    invoke()
                    if cmd in forms:
                        form=page.locator('#entry')
                        for e in form.locator('input').all():
                            key=e.get_attribute('id')
                            val=fields.get(key,'QA')
                            if key=='receiptIds':val=page.evaluate("manifests[0].packages.map(x=>x.id).join(' ') || 'нет'")
                            e.fill(val)
                        form.locator('button').click()
                        assert not form.is_visible(),'form submission not accepted'
                    if cmd=='print':
                        assert page.pdf().startswith(b'%PDF')
                    predicate="document.querySelector('#dlg').open && !!document.querySelector('#dialogTitle').textContent" if check=='D' else check
                    page.wait_for_function("()=>("+predicate+")", timeout=1800)
                    detail=page.locator('#dialogTitle').inner_text() if check=='D' else check
                result='PASS'
            except Exception as ex:
                result='FAIL';detail=str(ex).split('Call log:')[0][:350]
            row=[size,cmd,method,result,detail]
            results.append(row)
            print('CASE',json.dumps(row,ensure_ascii=False),flush=True)
        page.close()
    browser.close()
with open('command-results.csv','w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['viewport','command','interaction','result','evidence']);writer.writerows(results)
print('Failed',sum(r[3]!='PASS' for r in results))
