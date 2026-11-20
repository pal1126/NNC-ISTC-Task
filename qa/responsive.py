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
    if 'function showInspectionSummary' in urlopen(url+'?check=wall-fit').read().decode():
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
                raise AssertionError(f'{name} {label}') from error
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
            page.locator('#dlg').wait_for(state='hidden')
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
        picker=page.locator('[data-act="site"][data-v="S-002"]')
        activate(picker)
        assert picker.evaluate("e=>e===document.activeElement") and picker.get_attribute('aria-pressed')=='true'
        pin=page.locator('[data-site="S-003"]')
        if mobile:
            assert picker.bounding_box()['height']>=44
            circle=pin.locator('.site-hit')
            point=circle.evaluate("""e=>{
                const r=e.getBoundingClientRect(), x=r.x+r.width/2+19,y=r.y+r.height/2;
                return [x,y,document.elementFromPoint(x,y)?.closest('[data-site]')?.dataset.site]
            }""") if circle.is_visible() else None
            if point is None or point[2]!='S-003':
                circle.scroll_into_view_if_needed()
                point=circle.evaluate("""e=>{const r=e.getBoundingClientRect(),x=r.x+r.width/2+19,y=r.y+r.height/2;return [x,y,document.elementFromPoint(x,y)?.closest('[data-site]')?.dataset.site]}""")
            assert point[2]=='S-003',point
            page.touchscreen.tap(*point[:2])
        else:
            pin.focus()
            pin.press('Space')
        assert pin.evaluate("e=>e===document.activeElement") and pin.get_attribute('aria-pressed')=='true'
        opener=page.locator('[data-act="sections"]')
        activate(opener)
        page.locator('#sectionQuery').fill('перевозок   история')
        result=page.locator('#sectionResults button').filter(has_text='История перевозок')
        assert result.count()==1
        page.locator('#sectionQuery').fill('яяянеизвестно')
        assert page.locator('#sectionResults p').is_visible()
        page.keyboard.press('Escape')
        assert not page.locator('#dlg').is_visible()
        assert opener.evaluate('e=>e===document.activeElement')
        home()
        print('FOCUS TOUCH SEARCH',name,'PASS',flush=True)
        page.goto(url+'#map')
        page.locator('#mapQ').fill('S-00')
        activate(page.locator('[data-act="site"][data-v="S-003"]'))
        link=page.locator('[data-act="siteObjects"][data-v="S-003"]')
        link.scroll_into_view_if_needed()
        # Emulate horizontal reading position only if the table overflows.
        left=page.locator('.scroll').last.evaluate("e=>{e.scrollLeft=62;return e.scrollLeft}")
        top=page.evaluate('scrollY')
        activate(link)
        page.wait_for_url('**/#objects')
        assert page.locator('#objQ').input_value()=='S-003'
        activate(page.locator('[data-act="previous"]'))
        page.wait_for_url('**/#map')
        def verify_return():
            assert page.locator('#mapQ').input_value()=='S-00'
            assert link.evaluate('e=>document.activeElement===e')
            assert page.locator('.scroll').last.evaluate('e=>e.scrollLeft')==left
            assert abs(page.evaluate('scrollY')-top)<=2
        verify_return()
        page.go_forward()
        page.wait_for_url('**/#objects')
        page.go_back()
        page.wait_for_url('**/#map')
        verify_return()
        print('RETURN CONTEXT',name,'PASS',top,left,flush=True)
        home()
        for route,field,action,query,wanted in [
            ('map','mapQ','site','  площадка   S ‑ 003  Западная ','S-003'),
            ('objects','objQ','pickObj','реабилитации  f – 001','F-001'),
            ('packaging','pkgQ','pickPkg','Р02   pkg − 003','PKG-003')
        ]:
            page.goto(url+'#'+route)
            box=page.locator('#'+field)
            rows=page.locator('#main table [data-act="'+action+'"]')
            box.fill(' ')
            total=rows.count()
            assert total>1
            box.fill(query)
            assert rows.count()==1 and rows.first.get_attribute('data-v')==wanted
            assert rows.first.get_attribute('aria-pressed')=='true'
            if route in ('objects','packaging'):
                assert '1 из '+str(total) in page.locator('.register-summary').inner_text()
                history_size=page.evaluate('history.length')
                if mobile:
                    activate(rows.first)
                else:
                    rows.first.focus()
                    rows.first.press('Enter')
                detail=page.locator('#record-detail')
                assert wanted in detail.locator('h2').inner_text()
                assert detail.evaluate('e=>document.activeElement===e')
                assert detail.locator('h2').evaluate('e=>{const r=e.getBoundingClientRect();return r.top>=0 && r.bottom<=innerHeight}')
                activate(detail.locator('[data-record-back]'))
                assert rows.first.evaluate('e=>document.activeElement===e')
                assert rows.first.evaluate('e=>{const r=e.getBoundingClientRect();return r.top>=0 && r.bottom<=innerHeight}')
                assert box.input_value()==query and page.evaluate('history.length')==history_size
                print('REGISTER DETAIL',name,route,'PASS',flush=True)
            box.fill(query+' xyz')
            assert rows.count()==0
            if route in ('objects','packaging'):
                assert not page.locator('#record-detail').count()
            box.fill('')
            assert rows.count()==total
        home()
        activate(page.locator('[data-act="sections"]'))
        query=page.locator('#sectionQuery')
        query.fill('перевозок история')
        query.press('ArrowDown')
        assert page.locator('#sectionResults button:focus').count()==1
        page.keyboard.press('ArrowUp')
        assert query.evaluate('e=>e===document.activeElement')
        query.press('Enter')
        page.wait_for_url('**/#transport')
        assert page.locator('h1:focus').inner_text()=='История перевозок'
        back=page.locator('[data-act="previous"]:visible')
        assert 'Сводная панель' in back.inner_text()
        activate(back)
        page.locator('.hq').wait_for()
        assert page.locator('[data-act="sections"]:focus').count()==1
        page.emulate_media(reduced_motion='reduce')
        activate(page.locator('[data-act="siteCard"]'))
        assert page.locator('#main').evaluate('e=>e.getAnimations().length')==0
        activate(page.locator('.pagejump [data-act="sections"]'))
        page.go_back()
        page.locator('.hq').wait_for()
        assert not page.locator('#dlg').is_visible()
        page.emulate_media(reduced_motion='no-preference')
        page.goto(url+'#packaging')
        page.locator('#pkgQ').fill('PKG-003')
        page.locator('#inspectionTerm').select_option('Просрочен')
        opener=page.locator('table [data-act="inspection"][data-v="PKG-004"]')
        opener.scroll_into_view_if_needed()
        top=page.evaluate('scrollY')
        activate(opener)
        assert 'Просрочен на 6 дн.' in page.locator('#dlg').inner_text()
        assert not page.locator('#dlg h3').filter(has_text='Передано на проверку').count()
        if mobile:
            activate(page.locator('#dlg>form button'))
        else:
            page.keyboard.press('Escape')
        assert opener.evaluate('el=>el===document.activeElement')
        assert abs(page.evaluate('scrollY')-top)<=2
        assert page.locator('#pkgQ').input_value()=='PKG-003'
        assert page.locator('#inspectionTerm').input_value()=='Просрочен'
        page.locator('#role').select_option('edit')
        activate(page.locator('[data-act="inspectSubmit"][data-v="PKG-004"]'))
        page.locator('#inext').fill('2026-12-20')
        page.locator('#iaction').fill('Повторная проверка')
        page.locator('#iref').fill('DEMO-TEST-CHECK')
        activate(page.locator('#entry button.primary'))
        page.locator('#dlg').wait_for(state='hidden')
        page.locator('#inspectionTerm').select_option('На проверке')
        activate(opener)
        assert page.locator('#dlg h3').count()==2
        assert 'DEMO-TEST-CHECK' in page.locator('#dlg').inner_text()
        assert 'Просрочен на 6 дн.' in page.locator('#dlg').inner_text()
        page.keyboard.press('Escape')
        print('INSPECTION QUEUE',name,'PASS',flush=True)
        print('SECTION TRANSITIONS',name,'PASS',flush=True)
        print('REGISTER SEARCH',name,'PASS',flush=True)
        home()
        page.screenshot(path=str(out/(name+'.png')))
        print(name,'HOME',geometry(),flush=True)
        for label,flow in [('map-card-home',map_flow),('stock-filter',metric_flow),('search-navigation',sections_flow)]:
            check(label,flow)
        for route in routes:
            page.goto(url+'#'+route)
            page.locator('#main h1:visible').first.wait_for()
            g=geometry()
            assert g['width']==w,(name,route,g)
            if route!='overview':
                title=page.locator('#main h1:visible').first.inner_text()
                assert page.title().startswith(title)
            if route=='objects':
                wide=page.locator('#main .wide-table').first
                if mobile and w<500:
                    wide.wait_for()
                    assert wide.get_attribute('tabindex')=='0'
                    assert wide.locator('+ .table-help').is_visible()
                if name=='tablet':
                    menu=page.locator('#menu')
                    activate(menu)
                    assert page.locator('#nav a[aria-current]').is_visible()
                    menu.press('Escape')
                    assert menu.get_attribute('aria-expanded')=='false'
            page.screenshot(path=str(out/(name+'-'+route+'.png')))
            print(name,route,g['viewport'],g['width'],g['overflow'],flush=True)
        print(name,'JS errors',errors,flush=True)
        assert not errors, errors
        page.close()
    browser.close()
