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
    if 'Показать все наблюдения этого пункта' in urlopen(url+'?check=monitor-recovery').read().decode():
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
        query=page.locator('#sectionQuery')
        query.evaluate("""input=>{
            input.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));
            input.value='перевозок   история';
            input.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true}));
            for(const key of ['ArrowDown','Enter','Escape']){
                input.dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true,cancelable:true,isComposing:true}));
            }
        }""")
        assert query.evaluate("e=>e===document.activeElement") and page.locator('#dlg').is_visible()
        assert page.locator('#sectionResults button').count()==14
        query.evaluate("e=>e.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true}))")
        assert page.locator('#sectionResults button').count()==1, page.locator('#sectionResults').inner_text()
        print('SECTION SEARCH COMPOSITION',name,'PASS',flush=True)
        result=page.locator('#sectionResults button').filter(has_text='История перевозок')
        assert result.count()==1
        page.locator('#sectionQuery').fill('яяянеизвестно')
        assert page.locator('#sectionResults p').is_visible()
        assert page.locator('#sectionCount').inner_text()=='Найдено разделов: 0'
        query=page.locator('#sectionQuery')
        assert query.get_attribute('aria-describedby')=='sectionKeys'
        query.press('Tab')
        assert page.locator('#clearSectionQuery').evaluate('b=>b===document.activeElement')
        page.keyboard.press('Enter')
        assert query.evaluate('e=>e===document.activeElement') and query.input_value()==''
        assert page.locator('#sectionCount').inner_text()=='Найдено разделов: 14'
        assert page.locator('#sectionResults button').count()==14
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
        pins=page.locator('[data-act="pins"]')
        activate(pins)
        page.reload()
        assert pins.inner_text()=='Показать отметки' and page.locator('.map [data-site]').count()==0
        assert page.locator('#mapQ').input_value()=='S-00' and link.is_visible()
        activate(pins)
        page.reload()
        assert page.locator('.map [data-site="S-003"]').get_attribute('aria-pressed')=='true'
        assert page.locator('table [data-act="site"][data-v="S-003"]').get_attribute('aria-pressed')=='true'
        assert link.is_visible()
        page.locator('#mapQ').fill('несуществующая площадка')
        page.reload()
        assert page.locator('.map [data-site]').count()==0 and not link.count()
        assert page.get_by_text('По заданным условиям площадок нет.',exact=True).is_visible()
        print('MAP RELOAD CONTEXT',name,'PASS',flush=True)
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
            box.focus()
            box.evaluate("""(field, value)=>{
                field.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));
                field.value=value;
                field.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true}));
                if(!field.isConnected)throw Error('Search field replaced during composition');
            }""",query)
            assert rows.count()==total
            box.evaluate("""field=>field.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true}))""")
            assert rows.count()==1
            box.evaluate("""field=>{field.setSelectionRange(1,4,'backward');render()}""")
            assert box.evaluate('f=>[f===document.activeElement,f.selectionStart,f.selectionEnd,f.selectionDirection]')==[True,1,4,'backward']
            print('SEARCH COMPOSITION',name,route,'PASS',flush=True)
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
            if route in ('objects','packaging'):
                query='F-00' if route=='objects' else 'PKG-00'
                box.fill(query)
                assert rows.count()>1
                selected=rows.last.get_attribute('data-v')
                activate(rows.last)
                page.reload()
                assert box.input_value()==query and selected in page.locator('#record-detail h2').inner_text()
                assert rows.last.get_attribute('aria-pressed')=='true' and rows.last.get_attribute('data-v')==selected
                box.fill('несуществующая запись')
                page.reload()
                assert rows.count()==0 and page.locator('#record-detail').count()==0
                box.fill('')
                print('REGISTER RELOAD SELECTION',name,route,'PASS',flush=True)
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
        for pkg,trip,container in [('PKG-001','TR-001','CT-001'),('PKG-002','TR-001','CT-001'),('PKG-003','TR-002','SP-001'),('PKG-004',None,None)]:
            page.locator('#pkgQ').fill(pkg)
            detail=page.locator('#record-detail')
            trip_link=detail.locator('[data-act="pkgTrip"]')
            if trip is None:
                assert trip_link.count()==0 and 'В журнале перевозок нет записей об этой упаковке.' in detail.inner_text()
                continue
            assert trip_link.inner_text()==trip+' · '+container
            activate(trip_link)
            page.wait_for_url('**/#transport')
            assert page.locator('#trip option:checked').inner_text().startswith(trip+' · ')
            assert page.locator('.map g').filter(has_text=container).count()==1
            assert page.locator('[data-act="passport"][data-v="'+pkg+'"]').is_visible()
            activate(page.locator('[data-act="previous"]').first)
            page.wait_for_url('**/#packaging')
            assert page.locator('#pkgQ').input_value()==pkg and pkg in detail.locator('h2').inner_text()
            assert trip_link.evaluate('e=>e===document.activeElement')
        print('PACKAGE TRIP ROUND TRIP',name,'PASS',flush=True)
        page.locator('#pkgQ').fill('PKG-003')
        def shortcut(key):
            return page.locator('[data-inspection-queue="'+key+'"]')
        overdue, pending, returned = [shortcut(key) for key in ('Просрочен', 'На проверке', 'На доработке')]
        assert [b.locator('strong').inner_text() for b in (overdue,pending,returned)] == ['1','0','0']
        activate(pending)
        assert pending.get_attribute('aria-pressed')=='true'
        assert page.locator('table [data-act="inspection"]').count()==0
        empty=page.locator('.inspection-empty')
        assert empty.get_by_role('status').inner_text()=='Нет записей, ожидающих проверки.'
        activate(returned)
        assert empty.get_by_role('status').inner_text()=='Нет записей, возвращённых на доработку.'
        reset=empty.get_by_role('button',name='Показать все упаковки')
        assert reset.bounding_box()['height']>=44
        activate(reset)
        assert not empty.count()
        assert page.locator('#inspectionTerm').input_value()==''
        assert page.locator('#inspectionTerm').evaluate('el=>el===document.activeElement')
        assert page.locator('#pkgQ').input_value()=='PKG-003'
        assert page.locator('table [data-act="inspection"]').count()>0
        activate(pending)
        activate(pending)
        assert pending.get_attribute('aria-pressed')=='false'
        print('EMPTY QUEUE RECOVERY',name,'PASS',flush=True)
        activate(overdue)
        assert overdue.evaluate('el=>el===document.activeElement')
        opener=page.locator('table [data-act="inspection"][data-v="PKG-004"]')
        inspection_list=page.locator('.inspection-list')
        captions=inspection_list.locator('tbody tr').first.locator('.inspection-caption')
        assert captions.count()==6
        if name=='phone':
            assert all(c.is_visible() for c in captions.all())
            assert inspection_list.evaluate('el=>el.scrollWidth<=el.clientWidth+1')
            for button in inspection_list.locator('button').all():
                box=button.bounding_box()
                assert box and box['height']>=44 and box['x']>=0 and box['x']+box['width']<=w+1
        else:
            assert not captions.first.is_visible()
            assert inspection_list.locator('thead th').first.is_visible()
        print('INSPECTION ROW LAYOUT',name,'PASS',flush=True)
        assert '14.11.2026' in inspection_list.inner_text()
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
        page.locator('#iresult').select_option('2')
        page.locator('#iaction').fill('Повторная проверка')
        page.locator('#iref').fill('DEMO-TEST-CHECK')
        for field,value,reason in [
            ('iday','31.02.2026','существующую дату'),
            ('iday','01.11.2026','последнему подтверждённому'),
            ('iday','21.11.2026','отчётной даты'),
            ('inext','31.11.2026','существующую дату'),
            ('inext','20.11.2026','позже текущего')]:
            box=page.locator('#'+field)
            box.fill(value)
            activate(page.locator('#entry button.primary'))
            assert box.evaluate('el=>el===document.activeElement')
            assert reason in page.locator('#'+field+'-error').inner_text()
            assert box.get_attribute('aria-invalid')=='true'
            assert page.locator('#iref').input_value()=='DEMO-TEST-CHECK'
            box.fill('20.11.2026' if field=='iday' else '20.12.2026')
            assert not page.locator('#'+field+'-error').count()
        print('INSPECTION DATE VALIDATION',name,'PASS',flush=True)
        activate(page.locator('#entry button.primary'))
        page.locator('#dlg').wait_for(state='hidden')
        assert pending.locator('strong').inner_text()=='1'
        activate(pending)
        activate(opener)
        assert page.locator('#dlg h3').count()==2
        assert 'DEMO-TEST-CHECK' in page.locator('#dlg').inner_text()
        assert '20.12.2026' in page.locator('#dlg').inner_text()
        assert '14.11.2026' in page.locator('#dlg').inner_text()
        assert 'Просрочен на 6 дн.' in page.locator('#dlg').inner_text()
        page.keyboard.press('Escape')
        review=page.locator('[data-act="inspectReview"][data-v="PKG-004"]')
        edit=page.locator('[data-act="inspectSubmit"][data-v="PKG-004"]')
        page.locator('#role').select_option('review')
        activate(review)
        comparison_table=page.locator('.inspection-review-table')
        assert comparison_table.locator('tbody tr').count()==4
        next_row=comparison_table.get_by_role('rowheader',name='Следующий осмотр').locator('..')
        assert '14.11.2026' in next_row.locator('td').nth(0).inner_text()
        assert '20.12.2026' in next_row.locator('td').nth(1).inner_text()
        assert 'DEMO-TEST-CHECK' in comparison_table.locator('tbody tr').last.locator('td').last.inner_text()
        assert 'Повторная проверка' in page.locator('#dlg dd').all_text_contents()
        assert comparison_table.locator('td small').first.is_visible()==(name=='phone')
        assert page.locator('#dlg').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
        print('CONFIRMED AND SUBMITTED',name,'PASS',flush=True)
        activate(page.locator('[data-act="inspectReturn"]'))
        page.locator('#ireason').fill('Уточните номер протокола.')
        activate(page.locator('#entry button.primary'))
        assert returned.locator('strong').inner_text()=='1'
        activate(returned)
        assert edit.is_disabled()
        page.locator('#role').select_option('edit')
        activate(edit)
        assert 'Уточните номер протокола.' in page.locator('#dlg').inner_text()
        assert page.locator('#iresult').input_value()=='2'
        assert page.locator('#iref').input_value()=='DEMO-TEST-CHECK'
        assert page.locator('#inext').input_value()=='2026-12-20'
        assert page.locator('#iaction').input_value()=='Повторная проверка'
        page.locator('#iref').fill('DEMO-TEST-R2')
        activate(page.locator('#entry button.primary'))
        assert edit.count()==0
        page.locator('#inspectionTerm').select_option('На проверке')
        page.locator('#role').select_option('review')
        activate(review)
        comparison=page.locator('.inspection-correction')
        assert 'Уточните номер протокола.' in comparison.inner_text()
        assert comparison.locator('.inspection-change h4').all_text_contents()==['Протокол']
        assert comparison.locator('.inspection-change dd').all_text_contents()==['DEMO-TEST-CHECK','DEMO-TEST-R2']
        activate(page.locator('[data-act="inspectReturn"]'))
        page.locator('#ireason').fill('Подтвердите редакцию.')
        activate(page.locator('#entry button.primary'))
        page.locator('#inspectionTerm').select_option('На доработке')
        page.locator('#role').select_option('edit')
        activate(edit)
        activate(page.locator('#entry button.primary'))
        page.locator('#inspectionTerm').select_option('На проверке')
        page.locator('#role').select_option('review')
        activate(review)
        assert 'Подтвердите редакцию.' in comparison.inner_text()
        assert 'без изменений' in comparison.inner_text()
        assert comparison.locator('.inspection-change').count()==0
        activate(page.locator('[data-act="inspectApprove"]'))
        print('REVIEW COMPARISON',name,'PASS',flush=True)
        assert review.count()==0
        assert [b.locator('strong').inner_text() for b in (overdue,pending,returned)] == ['0','0','0']
        print('QUEUE SHORTCUTS',name,'PASS',flush=True)
        page.locator('#inspectionTerm').select_option('Запланирован')
        activate(opener)
        assert 'DEMO-TEST-R2' in page.locator('#dlg').inner_text()
        assert page.locator('#dlg h3').count()==1
        page.keyboard.press('Escape')
        page.locator('#pkgQ').fill('PKG-004')
        decisions=page.locator('.inspection-decision')
        assert decisions.count()==3
        for index,expected in enumerate(['Редакция 3 · Подтверждено','Редакция 2 · Возвращено на доработку','Редакция 1 · Возвращено на доработку']):
            item=decisions.nth(index)
            assert item.locator('summary').inner_text()==expected
            activate(item.locator('summary'))
            assert 'Время решения (UTC)' in item.inner_text()
        assert 'без изменений' in decisions.nth(0).inner_text()
        assert decisions.nth(1).locator('.inspection-change dd').all_text_contents()==['DEMO-TEST-CHECK','DEMO-TEST-R2']
        assert 'Подтвердите редакцию.' in decisions.nth(1).inner_text()
        assert 'Уточните номер протокола.' in decisions.nth(2).inner_text()
        assert 'DEMO-TEST-R2' not in decisions.nth(2).inner_text()
        with page.expect_download() as event:
            activate(page.locator('[data-inspection-export="PKG-004"]'))
        downloaded=event.value
        assert downloaded.suggested_filename=='Task1_PKG-004_inspection_history_RU.html'
        offline=browser.new_context(offline=True,viewport={'width':w,'height':h})
        copy=offline.new_page()
        saved=out/(name+'-'+downloaded.suggested_filename)
        downloaded.save_as(saved)
        copy.goto(saved.resolve().as_uri())
        assert copy.locator('html').get_attribute('lang')=='ru'
        dates=[h.inner_text().split(' · ')[0] for h in copy.locator('article h2').all()]
        from datetime import datetime
        parsed=[datetime.strptime(day,'%d.%m.%Y') for day in dates]
        assert parsed==sorted(parsed,reverse=True) and dates[0]=='20.11.2026'
        print('RUSSIAN INSPECTION DATES',name,'PASS',flush=True)
        assert 'PKG-004' in copy.title()
        assert copy.locator('article').count()==4
        assert copy.locator('.inspection-decision[open]').count()==3
        for history in [decisions,copy.locator('.inspection-decision')]:
            for decision in history.all():
                baseline=decision.locator('.inspection-baseline')
                assert baseline.locator('dd').count()==4
                assert baseline.locator('dd').nth(2).inner_text()=='14.11.2026'
                assert '20.12.2026' in decision.inner_text()
                assert 'DEMO-TEST-R2' not in baseline.inner_text()
        print('REVIEW BASELINE HISTORY',name,'PASS',flush=True)
        assert copy.locator('.inspection-decision summary').all_text_contents()==decisions.locator('summary').all_text_contents()
        assert copy.locator('.inspection-decision').all_text_contents()==decisions.all_text_contents()
        assert 'PKG-003' not in copy.locator('main').inner_text()
        assert copy.evaluate('document.documentElement.scrollWidth<=innerWidth')
        offline.close()
        print('OFFLINE INSPECTION EXPORT',name,'PASS',flush=True)
        page.locator('#pkgQ').fill('PKG-003')
        assert decisions.count()==0
        print('INSPECTION HISTORY',name,'PASS',flush=True)
        print('INSPECTION CORRECTION',name,'PASS',flush=True)
        print('INSPECTION QUEUE',name,'PASS',flush=True)
        print('SECTION TRANSITIONS',name,'PASS',flush=True)
        print('REGISTER SEARCH',name,'PASS',flush=True)
        home()
        page.screenshot(path=str(out/(name+'.png')))
        print(name,'HOME',geometry(),flush=True)
        for label,flow in [('map-card-home',map_flow),('stock-filter',metric_flow),('search-navigation',sections_flow)]:
            check(label,flow)
        page.goto(url+'#packaging')
        page.locator('#pkgQ').fill('PKG-003')
        page.locator('#inspectionTerm').select_option('Просрочен')
        pdf=page.pdf(prefer_css_page_size=True)
        assert pdf.startswith(b'%PDF-')
        page.emulate_media(media='print')
        for field,expected in [('pkgQ','PKG-003'),('inspectionTerm','Просрочен')]:
            value=page.locator('#'+field).locator('..').locator('.print-value')
            assert value.is_visible() and value.inner_text()==expected
        page.emulate_media(media='screen')
        assert not page.locator('.print-brand').is_visible()
        page.reload()
        assert page.locator('#pkgQ').input_value()=='PKG-003'
        assert page.locator('#inspectionTerm').input_value()=='Просрочен'
        page.keyboard.press('Control+k')
        page.locator('#dlg[open]').wait_for()
        page.evaluate("location.hash='map'")
        page.locator('#mapQ').wait_for()
        assert not page.locator('#dlg').is_visible()
        page.go_back()
        assert page.locator('#pkgQ').input_value()=='PKG-003'
        page.go_forward()
        assert page.locator('#nav [aria-current]').get_attribute('href')=='#map'
        page.goto(url+'#unknown-module')
        page.wait_for_url('**/#overview')
        assert page.locator('#nav [aria-current]').get_attribute('href')=='#overview'
        print('RELOAD AND HISTORY',name,'PASS',flush=True)
        for route in routes:
            page.goto(url+'#'+route)
            page.locator('#main h1:visible').first.wait_for()
            page.reload()
            assert page.locator('#nav [aria-current]').get_attribute('href')=='#'+route
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
            if route=='transport':
                play=page.locator('[data-act="play"]')
                cursor=page.locator('#cursor')
                play.focus()
                if mobile: activate(play)
                else: play.press('Enter')
                page.wait_for_function("Number(document.querySelector('#cursor').value)>=2")
                assert play.evaluate('e=>e===document.activeElement')
                page.keyboard.press('Space')
                assert play.inner_text()=='Воспроизвести'
                cursor.focus()
                cursor.press('End')
                assert cursor.get_attribute('aria-valuetext')==page.locator('.time').inner_text()
                assert page.locator('[data-act="step"][data-v="1"]').is_disabled()
                cursor.press('ArrowLeft')
                advance=page.locator('[data-act="step"][data-v="1"]')
                advance.focus()
                advance.press('Enter')
                assert advance.is_disabled() and cursor.evaluate('e=>document.activeElement===e')
                cursor.press('Home')
                assert cursor.get_attribute('aria-valuetext')=='00:00 UTC'
                cursor.scroll_into_view_if_needed()
                rect=cursor.bounding_box()
                y=rect['y']+rect['height']/2
                xs=[rect['x']+rect['width']*frac for frac in (.08,.32,.64,.999)]
                cursor.evaluate('e=>window.seekSource=e')
                if mobile:
                    session=page.context.new_cdp_session(page)
                    session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':xs[0],'y':y}]})
                else:
                    page.mouse.move(xs[0],y)
                    page.mouse.down()
                positions=[]
                for x in xs[1:]:
                    if mobile: session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y}]})
                    else: page.mouse.move(x,y,steps=3)
                    assert cursor.evaluate('e=>e===window.seekSource')
                    positions.append(int(cursor.input_value()))
                    assert cursor.get_attribute('aria-valuetext')==page.locator('.time').inner_text()
                if mobile:
                    session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                    session.detach()
                else: page.mouse.up()
                assert positions[0]<positions[1]<positions[2]==160,positions
                assert cursor.get_attribute('aria-valuetext')=='02:40 UTC'
                assert 'Прибытие. Ожидается приёмка' in page.locator('table strong').inner_text()
                assert page.locator('[data-act="step"][data-v="1"]').is_disabled()
                cursor.press('Home')
                marker=page.locator('.map g').filter(has_text='CT-001')
                gap=page.get_by_text('Между 00:40 и 02:00 UTC координаты не поступали.',exact=False)
                activate(page.locator('[data-act="at"][data-v="90"]'))
                assert gap.is_visible() and cursor.get_attribute('aria-valuetext')=='01:30 UTC'
                assert marker.locator('title').text_content()=='Последняя отметка: 00:40 UTC'
                def check_marker(lon,lat):
                    x,y=marker.locator('circle').last.evaluate("e=>[Number(e.getAttribute('cx')),Number(e.getAttribute('cy'))]")
                    assert abs(x-(65+(lon-46.49)*770/40.83))<0.01
                    assert abs(y-(460-(lat-40.55)*420/14.89))<0.01
                check_marker(57.3,48.1)
                lines=page.locator('.map > path[stroke="#e5b768"]')
                previous_lines=lines.evaluate_all("els=>els.map(e=>e.getAttribute('d'))")
                activate(page.locator('[data-act="step"][data-v="1"]'))
                assert cursor.get_attribute('aria-valuetext')=='02:00 UTC' and gap.count()==0
                assert marker.locator('title').text_content()=='Последняя отметка: 02:00 UTC'
                check_marker(62.2,50.1)
                assert lines.evaluate_all("els=>els.map(e=>e.getAttribute('d'))")==previous_lines and len(previous_lines)==2
                cursor.press('Home')
                for index in ['0','1']:
                    page.locator('#trip').select_option(index)
                    page.locator('#speed').select_option('4')
                    minute,utc,container=('90','01:30','CT-001') if index=='0' else ('20','00:20','SP-001')
                    activate(page.locator('[data-act="at"][data-v="'+minute+'"]'))
                    expected=page.evaluate('currentTrip()')
                    pin=page.locator('.map g').filter(has_text=container).locator('circle').last
                    location=pin.evaluate("e=>[e.getAttribute('cx'),e.getAttribute('cy')]")
                    page.reload()
                    assert page.locator('#trip').input_value()==index and page.locator('#speed').input_value()=='4'
                    assert cursor.get_attribute('aria-valuetext')==utc+' UTC' and play.inner_text()=='Воспроизвести'
                    assert pin.evaluate("e=>[e.getAttribute('cx'),e.getAttribute('cy')]")==location
                    assert gap.count()==(1 if index=='0' else 0)
                    print('TRANSPORT RELOAD',name,expected['id'],'PASS',flush=True)
                    with page.expect_download() as download:
                        activate(page.get_by_role('button',name='Скачать историю в JSON'))
                    file=download.value
                    assert file.suggested_filename==expected['id']+'.json'
                    saved=json.loads(Path(file.path()).read_text(encoding='utf-8'))
                    meta=saved.pop('metadata')
                    assert saved==expected
                    assert meta['date']=='2026-11-14' and meta['timezone']=='UTC' and '14.11.2026' in page.locator('#main').inner_text()
                    assert meta['pts_columns']==['Минута','Долгота (°)','Широта (°)'] and meta['events_columns']==['Минута','Событие']
                    assert '00:00 UTC' in meta['time_unit'] and '30 минут' in meta['track_note'] and 'Демонстрационные' in meta['source']
                page.locator('#trip').select_option('0')
                print('TRANSPORT JSON EXPORT',name,'PASS',flush=True)
                print('TRANSPORT MAP GAP',name,'PASS',flush=True)
                print('TRANSPORT NATIVE DRAG',name,'PASS',positions,flush=True)
                print('TRANSPORT PLAYBACK FOCUS',name,'PASS',flush=True)
            if route=='monitor':
                for media in ['screen','print']:
                    page.emulate_media(media=media)
                    assert page.locator('.observation-key').is_visible()
                    for status,shape in [('Проверено','circle:not(.point-hit)'),('На проверке','rect')]:
                        points=page.locator('.observation-point[aria-label$="'+status+'"]')
                        assert points.count()>0 and points.locator(shape).count()==points.count()
                        for mark in points.all():
                            row=page.locator('tbody tr').filter(has_text=mark.get_attribute('data-v'))
                            assert status in row.inner_text()
                page.emulate_media(media='screen')
                print('OBSERVATION STATUS SHAPES',name,'PASS',flush=True)
                page.locator('#measure').select_option('P-002')
                page.locator('#period').select_option('late')
                page.locator('#qc').select_option('На проверке')
                export_button=page.locator('[data-act="measCsv"]')
                mode_label=page.locator('[data-act="corrected"]').inner_text()
                assert export_button.is_disabled() and page.locator('.observation-point').count()==0
                activate(page.get_by_role('button',name='Показать все наблюдения этого пункта'))
                assert page.locator('#measure').input_value()=='P-002'
                assert page.locator('#period').input_value()=='all' and page.locator('#qc').input_value()==''
                assert page.locator('[data-act="corrected"]').inner_text()==mode_label
                assert page.locator('#main tbody td:first-child').all_inner_texts()==['M-007','M-008']
                assert page.locator('.observation-point').count()==2 and export_button.is_enabled()
                print('MONITOR EMPTY RECOVERY',name,'PASS',flush=True)
                for station,mode,unit in [('P-001',False,'мкЗв/ч'),('P-002',True,'м')]:
                    page.locator('#measure').select_option(station)
                    page.locator('#period').select_option('early')
                    page.locator('#qc').select_option('Проверено')
                    activate(page.locator('[data-act="corrected"]'))
                    rows=page.locator('#main tbody tr')
                    before=rows.all_inner_texts()
                    summary=page.locator('.obsstats').inner_text()
                    assert before and all(r.locator('td').nth(4).inner_text()==unit for r in rows.all())
                    page.reload()
                    assert page.locator('#measure').input_value()==station
                    assert page.locator('#period').input_value()=='early' and page.locator('#qc').input_value()=='Проверено'
                    label='Показать исходные значения' if mode else 'Показать с учётом поправок'
                    assert page.locator('[data-act="corrected"]').inner_text()==label
                    assert rows.all_inner_texts()==before and page.locator('.obsstats').inner_text()==summary
                    import csv
                    for corrected in [mode,not mode]:
                        if corrected!=mode: activate(page.locator('[data-act="corrected"]'))
                        with page.expect_download() as event:
                            activate(page.locator('[data-act="measCsv"]'))
                        with open(event.value.path(),encoding='utf-8-sig',newline='') as file:
                            data=list(csv.DictReader(file))
                        assert [r['ID'] for r in data]==rows.locator('td:first-child').all_inner_texts()
                        values=page.locator('svg[aria-label="Измерения по датам"] text[fill="white"]').all_text_contents()
                        assert len(values)==len(data)
                        for row,value in zip(data,values):
                            expected=(row['Уточнённое'] or row['Исходное']) if corrected else row['Исходное']
                            assert row['Пункт']==station and row['Единица']==unit and row['Статус проверки']=='Проверено'
                            assert row['Режим отображения']==('С учётом поправок' if corrected else 'Исходные значения')
                            assert float(row['Значение на графике'])==float(expected)==float(value.replace(',','.'))
                    activate(page.locator('[data-act="corrected"]'))
                    point=page.locator('.observation-point').last
                    observation=point.get_attribute('data-v')
                    assert observation in point.get_attribute('aria-label') and unit in point.get_attribute('aria-label')
                    if mobile: activate(point.locator('.point-hit'))
                    else:
                        point.focus()
                        point.press('Enter')
                    dialog=page.locator('#dlg')
                    assert dialog.is_visible() and observation in dialog.locator('h2').inner_text()
                    assert 'DEMO-OBS-'+observation in dialog.inner_text() and station in dialog.inner_text()
                    page.keyboard.press('Escape')
                    assert not dialog.is_visible() and point.evaluate('e=>e===document.activeElement')
                    print('OBSERVATION POINT DETAIL',name,station,'PASS',flush=True)
                    print('MONITOR CHART CSV',name,station,'PASS',flush=True)
                    print('MONITOR RELOAD',name,station,'PASS',flush=True)
                page.locator('#measure').select_option('P-001')
                page.locator('#period').select_option('all')
                page.locator('#qc').select_option('')
            if route=='national':
                page.locator('#natSite').select_option('S-003')
                page.evaluate("declarations.set('S-001',{kind:'zero',received:null});render()")
                for status_key,expected in [('submitted',{'S-001','S-003'}),('missing',{'S-002','S-004'})]:
                    indicator=page.locator('[data-act="reportingMap"][data-v="'+status_key+'"]')
                    assert indicator.locator('b').inner_text().split(' / ')[0]==str(len(expected))
                    activate(indicator)
                    page.wait_for_url('**/#map')
                    assert page.locator('#mapStatus').input_value()==status_key
                    assert set(page.locator('table [data-act="site"]').all_text_contents())==expected
                    assert page.locator('.map [data-site]').count()==len(expected)
                    page.go_back()
                    assert page.locator('#natSite').input_value()=='S-003'
                page.evaluate("declarations.delete('S-001');render()")
                page.locator('#natSite').select_option('')
                empty_site=page.evaluate("sites.find(([id])=>!stock().some(o=>o.site===id) && !declarations.has(id))[0]")
                page.locator('#natSite').select_option(empty_site)
                for kind,message in [('missing','Объём РАО неизвестен'),('zero','нулевую декларацию'),('reported','По выбранным условиям')]:
                    page.evaluate("([id,kind])=>{declarations.set(id,{kind,received:null});render()}",[empty_site,kind])
                    section=page.locator('#inventory-reconciliation')
                    assert message in section.inner_text() and section.locator('[data-act="stockCsv"]').is_disabled()
                page.evaluate("id=>{declarations.delete(id);render()}",empty_site)
                page.locator('#basis').select_option('Прогноз')
                reset=section.get_by_role('button',name='Сбросить фильтры')
                if mobile:
                    reset.tap()
                else:
                    reset.focus()
                    reset.press('Enter')
                assert section.evaluate('el=>el===document.activeElement')
                assert page.locator('#natSite').input_value()==page.locator('#basis').input_value()==''
                assert reset.count()==0 and section.locator('[data-act="stockCsv"]').is_enabled()
                assert set(section.locator('[data-act="inventoryCard"]').all_text_contents())==set(page.evaluate('stock().map(o=>o.id)'))
                print('RESET INVENTORY FILTERS',name,'PASS',flush=True)
                assert 'Объём РАО неизвестен' not in page.locator('#inventory-reconciliation').inner_text()
                print('EMPTY INVENTORY SELECTION',name,'PASS',flush=True)
                import csv
                from decimal import Decimal
                reconciliation=page.locator('#inventory-reconciliation')
                for basis in ['Фактический запас','Прогноз']:
                    page.locator('#natSite').select_option('S-001')
                    metric=page.locator('.metrics [data-act="basisBoard"][data-v="'+basis+'"]')
                    total=Decimal(metric.locator('b').inner_text().split('м³')[0].replace(',','.').strip().replace('\u00a0',''))
                    activate(metric)
                    assert page.locator('#natSite').input_value()=='' and page.locator('#basis').input_value()==basis
                    assert reconciliation.evaluate('e=>e===document.activeElement && e.getBoundingClientRect().top<innerHeight')
                    ids=reconciliation.locator('[data-act="inventoryCard"]').all_text_contents()
                    with page.expect_download() as event:
                        activate(reconciliation.locator('[data-act="stockCsv"]'))
                    with open(event.value.path(),encoding='utf-8-sig',newline='') as file:
                        dialect=csv.Sniffer().sniff(file.readline(),delimiters=',;')
                        file.seek(0)
                        exported=list(csv.DictReader(file,dialect=dialect))
                    assert [row['ID'] for row in exported]==ids and ids
                    kind='forecast' if basis=='Прогноз' else 'stock'
                    assert event.value.suggested_filename==f'Task1_RU_inventory_2026-10-31_all-sites_{kind}_demo.csv'
                    assert all(row['Основание']==basis and row['Выборка по виду сведений']==basis and
                               row['Отчётная дата']=='31.10.2026' and row['Выборка по площадкам']=='Все площадки' and
                               row['Статус данных']=='Демонстрационные данные' for row in exported)
                    assert sum(Decimal(row['Заявленный объём, м³'].replace(',','.')) for row in exported)==total
                page.locator('#basis').select_option('')
                site=exported[0]['Площадка']
                page.locator('#natSite').select_option(site)
                with page.expect_download() as scoped:
                    activate(reconciliation.locator('[data-act="stockCsv"]'))
                assert scoped.value.suggested_filename==f'Task1_RU_inventory_2026-10-31_{site}_all_demo.csv'
                with open(scoped.value.path(),encoding='utf-8-sig',newline='') as file:
                    scoped_rows=list(csv.DictReader(file,dialect=dialect))
                assert scoped_rows and all(row['Площадка']==site and row['Выборка по площадкам']==site and
                                           row['Выборка по виду сведений']=='Все виды сведений' for row in scoped_rows)
                page.locator('#natSite').select_option('')
                print('CSV EXPORT CONTEXT',name,'PASS',flush=True)
                print('NATIONAL VOLUME CSV',name,'PASS',flush=True)
                print('NATIONAL REPORT TO MAP',name,'PASS',flush=True)
            if route in ['overview','map']:
                legend=page.locator('.mapkey')
                assert 'Нулевая декларация' in legend.inner_text()
                page.evaluate("""() => {
                    window.savedDeclaration=declarations.get('S-001');
                    declarations.set('S-001',{kind:'zero',received:null});render();
                }""")
                for kind,shape,status in [('reported','circle','Сведения представлены'),('zero','path','нулевая декларация'),('missing','rect','Сведения не представлены')]:
                    symbol=page.locator('.map [data-report-kind="'+kind+'"]').first
                    assert symbol.evaluate('e=>e.localName')==shape
                    pin=symbol.locator('..')
                    assert status.lower() in pin.get_attribute('aria-label').lower()
                    pin.focus()
                    pin.press('Enter')
                    assert pin.get_attribute('aria-pressed')=='true'
                page.evaluate("""() => {
                    if(window.savedDeclaration)declarations.set('S-001',window.savedDeclaration);
                    else declarations.delete('S-001');
                    render();
                }""")
                if route=='map':
                    status=page.locator('#mapStatus')
                    status.select_option('missing')
                    pins=page.locator('.map [data-site]')
                    assert pins.count()==3
                    assert all('Сведения не представлены' in p.get_attribute('aria-label') for p in pins.all())
                    assert page.locator('table [data-act="site"]').count()==3
                    page.locator('#mapQ').fill('S-001')
                    assert pins.count()==1 and pins.first.get_attribute('data-site')=='S-001'
                    activate(page.locator('[data-act="siteObjects"][data-v="S-001"]'))
                    page.go_back()
                    assert status.input_value()=='missing' and page.locator('#mapQ').input_value()=='S-001'
                    page.reload()
                    assert status.input_value()=='missing'
                    report=page.pdf(prefer_css_page_size=True)
                    from subprocess import run
                    report_text=' '.join(run(['pdftotext','-layout','-','-'],input=report,capture_output=True,check=True).stdout.decode().split())
                    assert 'Статус отчётности' in report_text and 'Сведения не представлены' in report_text,report_text[:850]
                    assert status.locator('..').locator('.print-value').text_content()=='Сведения не представлены'
                    status.select_option('zero')
                    assert pins.count()==0 and page.locator('table [data-act="site"]').count()==0
                    activate(page.locator('.panel [data-act="clearPageFilters"]'))
                    assert pins.count()==4 and status.input_value()==''
                    print('DECLARATION FILTER',name,'PASS',flush=True)
                print('MAP DECLARATION SYMBOLS',name,route,'PASS',flush=True)
            page.locator('#main').focus()
            page.keyboard.press('Control+k')
            assert page.locator('#sectionQuery').evaluate('e=>e===document.activeElement')
            page.keyboard.press('ArrowDown')
            assert page.locator('#sectionResults button:focus').count()==1
            page.keyboard.press('Escape')
            assert not page.locator('#dlg').is_visible()
            assert page.locator('#main').evaluate('e=>e===document.activeElement')
            print('KEYBOARD ROUND TRIP',name,route,'PASS',flush=True)
            page.emulate_media(media='print')
            data=page.pdf(prefer_css_page_size=True)
            assert data.startswith(b'%PDF-') and len(data)>5000
            assert page.locator('.print-brand').is_visible()
            assert not page.locator('.mast').is_visible()
            assert not page.locator('.rail').is_visible()
            from subprocess import run
            import re
            extracted=run(['pdftotext','-layout','-','-'],input=data,capture_output=True,check=True).stdout.decode()
            sheets=extracted.split('\f')
            if not sheets[-1].strip(): sheets.pop()
            expected_title=page.title().split(' · ГИС учёта РАО')[0]
            if route in ['map','transport']:
                assert 'КАЗАХСТАН' in ''.join(sheets[0].split()),(route,'map must appear on first sheet')
            if route in ['map','overview']:
                assert 'Нулевая декларация' in ' '.join(extracted.split())
            for number,sheet in enumerate(sheets,1):
                lines=[' '.join(line.split()) for line in sheet.splitlines() if line.strip()]
                assert expected_title in lines[0],(name,route,number,lines[:2])
                assert 'Демонстрационные данные' in lines[-1] and f'Стр. {number} из {len(sheets)}' in lines[-1],(route,number,lines[-2:])
                assert len(' '.join(lines[1:-1]))>10,('empty sheet',route,number,lines)
            print('PAGINATED',name,route,len(sheets),flush=True)
            if name=='wall':
                (out/(route+'-print.pdf')).write_bytes(data)
            page.emulate_media(media='screen')
            print('MODULE PRINT',name,route,'PASS',len(data),flush=True)
            page.screenshot(path=str(out/(name+'-'+route+'.png')))
            print(name,route,g['viewport'],g['width'],g['overflow'],flush=True)
        print(name,'JS errors',errors,flush=True)
        assert not errors, errors
        page.close()
    browser.close()
