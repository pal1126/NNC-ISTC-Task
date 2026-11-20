from pathlib import Path
import json
from playwright.sync_api import sync_playwright
url = "https://pal1126.github.io/NNC-ISTC-Task/"
out = Path("evidence")
out.mkdir(exist_ok=True)
routes = "overview map objects monitor review spec packaging transport national acceptance benchmark workbench storage receiving".split()
# Wait for Pages to serve the revision under acceptance.
from urllib.request import urlopen
from time import sleep
for attempt in range(30):
    if 'max-height: 31vh' in urlopen(url+'?check=wall-fit').read().decode():
        break
    sleep(5)
else:
    raise RuntimeError('New Pages stylesheet unavailable')
with sync_playwright() as p:
    browser = p.chromium.launch()
    for name,w,h,mobile in [('wall',1920,1080,False),('tablet',820,1180,True),('phone',390,844,True)]:
        page = browser.new_page(viewport={'width':w,'height':h},is_mobile=mobile,has_touch=mobile)
        page.set_default_timeout(4500)
        errors = []
        page.on('pageerror',lambda error: errors.append(str(error)))
        def activate(locator):
            if mobile: locator.tap()
            else: locator.click()
        def check(label, operation):
            try:
                operation()
                print(name,label,'PASS',flush=True)
            except Exception as error:
                print(name,label,'FAIL',str(error)[:500],flush=True)
        def home():
            page.goto(url)
            page.locator('.hq').wait_for()
        def geometry():
            return page.evaluate("""() => ({viewport:document.documentElement.clientWidth,width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,overflow:[...document.querySelectorAll('#main *')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0 && r.right>document.documentElement.clientWidth+1 && !e.closest('.scroll')}).slice(0,5).map(e=>e.tagName+'.'+e.className)})""")
        def map_flow():
            home()
            activate(page.locator('[data-act="site"][data-v="S-003"]'))
            assert 'Западная' in page.locator('.sel20 h3').inner_text()
            activate(page.locator('[data-act="siteCard"]'))
            page.wait_for_url('**/#map')
            assert 'S-003' in page.locator('#main').inner_text()
            activate(page.locator('[data-act="boardHome"]'))
            page.locator('.hq').wait_for()
        def metric_flow():
            home()
            activate(page.locator('.hqmetrics [data-act="basisBoard"]').first)
            page.wait_for_url('**/#national')
            assert page.locator('#basis').input_value()=='Фактический запас'
        def sections_flow():
            home()
            activate(page.locator('[data-act="sections"]'))
            page.locator('#sectionQuery').fill('перевоз')
            activate(page.locator('#sectionResults button').filter(has_text='История перевозок').first)
            page.wait_for_url('**/#transport')
            assert not page.locator('#dlg').is_visible()
        home()
        for site in ['S-001','S-002','S-003','S-004']:
            activate(page.locator('[data-act="site"][data-v="'+site+'"]'))
            assert site in page.locator('.sel20').inner_text()
            g=geometry()
            bounds=page.locator('.hq button:visible, .mapfoot, .foot').evaluate_all('es=>es.map(e=>e.getBoundingClientRect()).map(r=>[r.left,r.top,r.right,r.bottom])')
            print('LAYOUT',name,site,g,'last',max(r[3] for r in bounds),flush=True)
            assert g['width']==w
            if name=='wall':
                assert g['height']<=h and all(0<=r[0] and 0<=r[1] and r[2]<=w+1 and r[3]<=h+1 for r in bounds)
        home()
        page.screenshot(path=str(out/(name+'.png')))
        print(name,'HOME',geometry(),flush=True)
        for label,flow in [('map-card-home',map_flow),('stock-filter',metric_flow),('search-navigation',sections_flow)]:
            check(label,flow)
        for route in routes:
            page.goto(url+'#'+route)
            page.locator('#main h1:visible').first.wait_for()
            g=geometry()
            print(name,route,g['viewport'],g['width'],g['overflow'],flush=True)
        print(name,'JS errors',errors,flush=True)
        page.close()
    browser.close()
