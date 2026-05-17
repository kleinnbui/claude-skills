"""Generate CRO Engine v2.5 JS code for [CRO] Journey Tracker GTM tag.

Mirrors generateEngineCode() in cro-wizard.html:1072-1769 — feed in the same
wizard JSON config and emit the same <script> output.

Config schema (subset of wizard JSON export):
{
  "project": {"clientName": "...", "gtmContainerId": "GTM-XXXXXXX"},
  "forms":   [{name, triggerType, formSelector, successSelector,
               successGlobal, validationErrorSelector, timeout,
               cf7SuccessClass, cf7FailClasses, cf7ResponseSelector,
               thankYouPath, thankYouParam}, ...],
  "others":  [{name, triggerType, pattern}, ...],
  "abTests": [{testId, pages, variants, split}, ...]
}
"""
from __future__ import annotations


def _esc(s) -> str:
    """JS single-quote string escape."""
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def _build_form_list_entries(forms: list[dict]) -> str:
    """Build FORM_LIST entries — only standard dom_change (non-global) + cf7_class."""
    standard = [f for f in forms
                if f["triggerType"] == "dom_change" and not f.get("successGlobal")]
    cf7 = [f for f in forms if f["triggerType"] == "cf7_class"]
    entries = []
    for f in standard + cf7:
        entries.append(
            f"        {{ selector: '{_esc(f.get('formSelector', ''))}', "
            f"name: '{_esc(f.get('name', ''))}', "
            f"success: '{_esc(f.get('successSelector', ''))}' }}"
        )
    return ",\n".join(entries)


def _build_map_block(forms: list[dict]) -> str:
    """Build CRO_CONFIG = FORM_LIST.map(...) for standard dom_change OR cf7."""
    has_standard_dom = any(
        f["triggerType"] == "dom_change" and not f.get("successGlobal")
        for f in forms
    )
    has_cf7 = any(f["triggerType"] == "cf7_class" for f in forms)

    if has_standard_dom:
        return """
    var CRO_CONFIG = FORM_LIST.map(function(f) {
      return {
        conversionId:            f.name,
        triggerType:             'dom_change',
        conversionSelector:      f.selector,
        successSelector:         f.success,
        validationErrorSelector: '.error-text:not(:empty)',
        timeout:                 15000,
        eventSuccess:            'conversion_success',
        eventFailed:             'conversion_attempt_failed',
        eventFormStart:          'form_interaction'
      };
    });"""
    if has_cf7:
        return """
    var CRO_CONFIG = FORM_LIST.map(function(f) {
      return {
        conversionId:            f.name,
        triggerType:             'cf7_class',
        conversionSelector:      f.selector,
        cf7SuccessClass:         'wpcf7-mail-sent-ok',
        cf7FailClasses:          ['wpcf7-mail-sent-ng', 'wpcf7-validation-errors', 'wpcf7-spam-blocked'],
        cf7ResponseSelector:     '.wpcf7-response-output',
        timeout:                 15000,
        eventSuccess:            'conversion_success',
        eventFailed:             'conversion_attempt_failed',
        eventFormStart:          'form_interaction'
      };
    });"""
    return "\n    var CRO_CONFIG = [];"


def _build_extras(forms: list[dict], others: list[dict]) -> str:
    """Build CRO_CONFIG.concat([...]) for global dom + manual + others."""
    extras = []

    # global dom_change (successGlobal=true)
    for f in forms:
        if f["triggerType"] != "dom_change" or not f.get("successGlobal"):
            continue
        extras.append(
            "      {\n"
            f"        conversionId:            '{_esc(f.get('name', ''))}',\n"
            f"        triggerType:             'dom_change',\n"
            f"        conversionSelector:      '{_esc(f.get('formSelector', ''))}',\n"
            f"        successSelector:         '{_esc(f.get('successSelector', ''))}',\n"
            f"        successGlobal:           true,\n"
            f"        validationErrorSelector: '{_esc(f.get('validationErrorSelector') or '.error-text:not(:empty)')}',\n"
            f"        timeout:                 {int(f.get('timeout') or 15000)},\n"
            f"        eventSuccess:            'conversion_success',\n"
            f"        eventFailed:             'conversion_attempt_failed',\n"
            f"        eventFormStart:          'form_interaction'\n"
            "      }"
        )

    # manual: thank_you_url, button_click, form_submit
    for f in forms:
        t = f["triggerType"]
        if t == "thank_you_url":
            require_line = "        requireAttempt:     true,\n" if f.get("requireAttempt") else ""
            hs_form_id = f.get("hubspotFormId", "")
            hs_line = f"        hubspotFormId:      '{_esc(hs_form_id)}',\n" if hs_form_id else ""
            extras.append(
                "      {\n"
                f"        conversionId:       '{_esc(f.get('name', ''))}',\n"
                f"        triggerType:        'thank_you_url',\n"
                f"        conversionSelector: '{_esc(f.get('formSelector') or 'form')}',\n"
                f"        thankYouPath:       '{_esc(f.get('thankYouPath', ''))}',\n"
                f"        thankYouParam:      '{_esc(f.get('thankYouParam', ''))}',\n"
                f"{hs_line}"
                f"{require_line}"
                f"        timeout:            {int(f.get('timeout') or 15000)},\n"
                f"        eventSuccess:       'conversion_success',\n"
                f"        eventFailed:        'conversion_attempt_failed'\n"
                "      }"
            )
        elif t == "button_click":
            global_line = "        successGlobal:      true,\n" if f.get("successGlobal") else ""
            extras.append(
                "      {\n"
                f"        conversionId:       '{_esc(f.get('name', ''))}',\n"
                f"        triggerType:        'button_click',\n"
                f"        conversionSelector: '{_esc(f.get('formSelector', ''))}',\n"
                f"        successSelector:    '{_esc(f.get('successSelector', ''))}',\n"
                f"{global_line}"
                f"        timeout:            {int(f.get('timeout') or 15000)},\n"
                f"        eventSuccess:       'conversion_success',\n"
                f"        eventFailed:        'conversion_attempt_failed'\n"
                "      }"
            )
        elif t == "form_submit":
            extras.append(
                "      {\n"
                f"        conversionId:       '{_esc(f.get('name', ''))}',\n"
                f"        triggerType:        'form_submit',\n"
                f"        conversionSelector: '{_esc(f.get('formSelector', ''))}',\n"
                f"        eventSuccess:       'conversion_success'\n"
                "      }"
            )

    # others
    for o in others:
        t = o["triggerType"]
        name = _esc(o.get("name", ""))
        pat = _esc(o.get("pattern", ""))
        if t == "url_contains":
            extras.append(
                "      {\n"
                f"        conversionId: '{name}',\n"
                f"        triggerType:  'url_contains',\n"
                f"        urlContains:  '{pat}',\n"
                f"        eventSuccess: 'conversion_success'\n"
                "      }"
            )
        elif t == "text_contains":
            extras.append(
                "      {\n"
                f"        conversionId: '{name}',\n"
                f"        triggerType:  'text_contains',\n"
                f"        textContains: '{pat}',\n"
                f"        targetTag:    'a,button,div,span',\n"
                f"        eventSuccess: 'conversion_success'\n"
                "      }"
            )
        elif t == "click_class":
            extras.append(
                "      {\n"
                f"        conversionId:  '{name}',\n"
                f"        triggerType:   'click_class',\n"
                f"        classContains: '{pat}',\n"
                f"        eventSuccess:  'conversion_success'\n"
                "      }"
            )
        elif t == "page_url_contains":
            extras.append(
                "      {\n"
                f"        conversionId:    '{name}',\n"
                f"        triggerType:     'page_url_contains',\n"
                f"        pageUrlContains: '{pat}',\n"
                f"        eventSuccess:    'conversion_success'\n"
                "      }"
            )
        elif t == "data_attribute":
            extras.append(
                "      {\n"
                f"        conversionId:  '{name}',\n"
                f"        triggerType:   'data_attribute',\n"
                f"        dataAttribute: '{pat}',\n"
                f"        eventSuccess:  'conversion_success'\n"
                "      }"
            )
        elif t == "hubspot_chat":
            extras.append(
                "      {\n"
                f"        conversionId: '{name}',\n"
                f"        triggerType:  'hubspot_chat',\n"
                f"        eventSuccess: 'conversion_success'\n"
                "      }"
            )

    if not extras:
        return ""
    return "\n    CRO_CONFIG = CRO_CONFIG.concat([\n" + ",\n\n".join(extras) + "\n    ]);"


def _build_ab_tests_block(ab_tests: list[dict]) -> str:
    if not ab_tests:
        return "      // Chưa khai báo A/B test nào — bỏ qua section này"
    out = []
    for t in ab_tests:
        variants_raw = t.get("variants", "")
        variants = [v.strip() for v in str(variants_raw).split(",") if v.strip()] \
            if isinstance(variants_raw, str) else list(variants_raw)
        splits_raw = t.get("split", "")
        splits = [int(s.strip()) for s in str(splits_raw).split(",") if s.strip()] \
            if isinstance(splits_raw, str) else list(splits_raw)
        variants_js = ", ".join("'" + _esc(v) + "'" for v in variants)
        splits_js = ", ".join(str(s) for s in splits)
        out.append(
            "      {\n"
            f"        testId:   '{_esc(t.get('testId', ''))}',\n"
            f"        pages:    '{_esc(t.get('pages', '.*'))}',\n"
            f"        variants: [{variants_js}],\n"
            f"        split:    [{splits_js}]\n"
            "      }"
        )
    return ",\n".join(out)


# ── The engine runtime (verbatim port of cro-wizard.html L1226-1768) ─────────
# This is the JS body. Wizard config (FORM_LIST/CRO_CONFIG/AB_TESTS) is
# injected before, runtime stays untouched.

_ENGINE_RUNTIME = r"""
    var GLOBAL = {
      maxPagesStored: 12,
      debug:          false,
      trackBehavior:  true,
      trackSource:    true,
      trackDevice:    true,
      firstTouchDays: 30
    };

    /* ══════════════════════════════════════════════════════════
       PHẦN 2 — ENGINE (không chỉnh sửa)
       ══════════════════════════════════════════════════════════ */

    var JOURNEY_KEY = 'cro_journey';
    var log = GLOBAL.debug ? function(id, msg, data) { console.log('[CRO:' + (id || 'core') + ']', msg, data !== undefined ? data : ''); } : function() {};

    var OPTIONAL_PARAMS = ['cro_interaction','cro_fail_reason','cro_detection','cro_elapsed_ms','cro_success_selector','cro_cf7_class','cro_clicked_url','cro_clicked_text','cro_clicked_tag','cro_clicked_href','cro_clicked_class','cro_thank_you_path','cro_submission_guid','cro_timeout_ms'];

    function setCookie(name, value, days) { try { var e=''; if(days){var d=new Date();d.setTime(d.getTime()+(days*24*60*60*1000));e='; expires='+d.toUTCString();} document.cookie=name+'='+encodeURIComponent(value)+e+'; path=/; SameSite=Lax'; } catch(e) {} }
    function getCookie(name) { try { var n=name+'=', ca=document.cookie.split(';'); for(var i=0;i<ca.length;i++){var c=ca[i].trim(); if(c.indexOf(n)===0)return decodeURIComponent(c.substring(n.length));} } catch(e) {} return null; }

    var _deviceCache = null;
    function getDeviceInfo() {
      if (_deviceCache) return _deviceCache;
      if (!GLOBAL.trackDevice) return {};
      var info = {};
      try {
        info.cro_screen_size   = (screen.width||0)+'x'+(screen.height||0);
        info.cro_viewport_size = (window.innerWidth||0)+'x'+(window.innerHeight||0);
        info.cro_pixel_ratio   = window.devicePixelRatio||1;
        info.cro_orientation   = (window.innerHeight>=window.innerWidth)?'portrait':'landscape';
        var w = window.innerWidth||0;
        info.cro_device_type   = w<768?'mobile':(w<1024?'tablet':'desktop');
        var ua = navigator.userAgent||'', os='unknown', br='unknown';
        if (/iPhone|iPad|iPod/i.test(ua)) os='iOS';
        else if (/Android/i.test(ua)) os='Android';
        else if (/Windows NT/i.test(ua)) os='Windows';
        else if (/Macintosh|Mac OS/i.test(ua)) os='macOS';
        else if (/Linux/i.test(ua)) os='Linux';
        info.cro_os = os;
        if (/Edg\//i.test(ua)) br='Edge';
        else if (/Chrome/i.test(ua)) br='Chrome';
        else if (/Firefox/i.test(ua)) br='Firefox';
        else if (/Safari/i.test(ua)) br='Safari';
        else if (/MSIE|Trident/i.test(ua)) br='IE';
        info.cro_browser = br;
        var conn = navigator.connection||navigator.mozConnection||navigator.webkitConnection;
        info.cro_connection = conn?(conn.effectiveType||'unknown'):'unknown';
      } catch(e) {}
      _deviceCache = info;
      return info;
    }

    var _localeCache = null;
    function getLocaleInfo() {
      if (_localeCache) return _localeCache;
      if (!GLOBAL.trackDevice) return {};
      var info = {};
      try {
        info.cro_timezone = (Intl&&Intl.DateTimeFormat)?Intl.DateTimeFormat().resolvedOptions().timeZone:'unknown';
        info.cro_language = navigator.language||navigator.userLanguage||'unknown';
      } catch(e) {}
      _localeCache = info;
      return info;
    }

    var FIRST_TOUCH_KEY = 'cro_first_touch';
    function parseUTM() { var p={}; try { var qs=window.location.search; if(!qs)return p; var q=qs.substring(1).split('&'); for(var i=0;i<q.length;i++){var pr=q[i].split('='),k=decodeURIComponent(pr[0]||''),v=decodeURIComponent(pr[1]||''); if(k.indexOf('utm_')===0)p[k]=v;} } catch(e) {} return p; }
    function captureFirstTouch() {
      if (getCookie(FIRST_TOUCH_KEY)) return;
      var utm = parseUTM(), ref='', src='direct';
      try { ref = document.referrer||''; } catch(e) {}
      if (utm.utm_source) src = utm.utm_source + (utm.utm_medium?'/'+utm.utm_medium:'');
      else if (ref) {
        try {
          var h = new URL(ref).hostname.replace(/^www\./,'');
          if (/google\./i.test(h)) src='google/organic';
          else if (/bing\./i.test(h)) src='bing/organic';
          else if (/facebook\./i.test(h)) src='facebook/referral';
          else if (/youtube\./i.test(h)) src='youtube/referral';
          else src = h+'/referral';
        } catch(e) {}
      }
      setCookie(FIRST_TOUCH_KEY, JSON.stringify({source:src, campaign:utm.utm_campaign||'', ts:Date.now()}), GLOBAL.firstTouchDays);
    }
    function getSourceInfo() {
      if (!GLOBAL.trackSource) return {};
      var info = {};
      try {
        var utm = parseUTM();
        info.cro_utm_source   = utm.utm_source||'';
        info.cro_utm_medium   = utm.utm_medium||'';
        info.cro_utm_campaign = utm.utm_campaign||'';
        info.cro_referrer     = (document.referrer||'').substring(0,200);
        var ftRaw = getCookie(FIRST_TOUCH_KEY);
        if (ftRaw) { try { info.cro_first_touch_source = JSON.parse(ftRaw).source||''; } catch(e) { info.cro_first_touch_source=''; } }
        else info.cro_first_touch_source = '';
        info.cro_visitor_type = ftRaw?'returning':'new';
      } catch(e) {}
      return info;
    }

    var _behavior = { maxScrollPct: 0, clicksBeforeConvert: 0, formFillStart: null };
    function initBehaviorTracking() {
      if (!GLOBAL.trackBehavior) return;
      window.addEventListener('scroll', function() {
        try {
          var doc=document.documentElement, body=document.body;
          var st = window.pageYOffset||doc.scrollTop||body.scrollTop||0;
          var dh = Math.max(body.scrollHeight,doc.scrollHeight,body.offsetHeight,doc.offsetHeight,body.clientHeight,doc.clientHeight);
          var wh = window.innerHeight||doc.clientHeight;
          var sc = dh - wh;
          if (sc > 0) {
            var p = Math.round((st/sc)*100);
            if (p > _behavior.maxScrollPct) _behavior.maxScrollPct = Math.min(p, 100);
          }
        } catch(e) {}
      }, { passive: true });
      document.addEventListener('click', function() { _behavior.clicksBeforeConvert++; }, true);
      document.addEventListener('focusin', function(e) {
        try {
          var t=e.target; if(!t||!t.tagName)return;
          var tag=t.tagName.toUpperCase();
          if ((tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT') && _behavior.formFillStart===null) _behavior.formFillStart = Date.now();
        } catch(err) {}
      }, true);
    }
    function getBehaviorMetrics() {
      if (!GLOBAL.trackBehavior) return {};
      return {
        cro_max_scroll_pct:        _behavior.maxScrollPct,
        cro_clicks_before_convert: _behavior.clicksBeforeConvert,
        cro_form_fill_time_ms:     _behavior.formFillStart ? Date.now() - _behavior.formFillStart : 0
      };
    }

    var AB_COOKIE_PREFIX = 'cro_ab_';
    function pickVariant(test) {
      var existing = getCookie(AB_COOKIE_PREFIX + test.testId);
      if (existing && test.variants.indexOf(existing)!==-1) return existing;
      var rand = Math.random()*100, cum=0;
      for (var i=0; i<test.variants.length; i++) {
        cum += (test.split[i]||0);
        if (rand < cum) {
          var pk = test.variants[i];
          setCookie(AB_COOKIE_PREFIX+test.testId, pk, 90);
          return pk;
        }
      }
      var fb = test.variants[0];
      setCookie(AB_COOKIE_PREFIX+test.testId, fb, 90);
      return fb;
    }
    function pageMatches(pattern) { try { return new RegExp(pattern).test(window.location.pathname||'/'); } catch(e) { return false; } }
    var _activeTests = null;
    function getActiveTests() {
      if (_activeTests) return _activeTests;
      _activeTests = [];
      for (var i=0; i<AB_TESTS.length; i++) {
        var t = AB_TESTS[i];
        if (!pageMatches(t.pages)) continue;
        var v = pickVariant(t);
        _activeTests.push({ testId: t.testId, variant: v });
        try { if (document.body) document.body.classList.add(t.testId+'-'+v); } catch(e) {}
        log(null, 'A/B assigned', { test: t.testId, variant: v });
      }
      return _activeTests;
    }
    function getABDimensions() {
      var tests = getActiveTests();
      if (tests.length === 0) return {};
      var ids=[], vrs=[];
      for (var i=0; i<tests.length; i++) { ids.push(tests[i].testId); vrs.push(tests[i].variant); }
      return { cro_ab_test_id: ids.join('|'), cro_ab_variant: vrs.join('|') };
    }
    function initABTests() {
      if (document.body) getActiveTests();
      else document.addEventListener('DOMContentLoaded', function() { getActiveTests(); });
    }

    function getJourney() { try { return JSON.parse(sessionStorage.getItem(JOURNEY_KEY)) || { landingPage: '', pages: [], startTime: Date.now() }; } catch(e) { return { landingPage: '', pages: [], startTime: Date.now() }; } }
    function saveJourney(j) { try { sessionStorage.setItem(JOURNEY_KEY, JSON.stringify(j)); } catch(e) {} }
    function encodeSlug(url) { try { return (url || window.location.href).replace(/^https?:\/\/[^\/]+/, '').split('?')[0] || '/'; } catch(e) { return '/'; } }
    function buildPagesString(pages) { var str = pages.join('>'); if (str.length <= 95) return str; var half = Math.floor(GLOBAL.maxPagesStored / 2); return pages.slice(0, half).join('>') + '>…>' + pages.slice(-half).join('>'); }
    function recordPageView() { var j = getJourney(); var slug = encodeSlug(window.location.href); if (!j.landingPage) j.landingPage = slug; if (j.pages[j.pages.length - 1] !== slug) { j.pages.push(slug); if (j.pages.length > GLOBAL.maxPagesStored) j.pages = j.pages.slice(-GLOBAL.maxPagesStored); } saveJourney(j); log(null, 'Pageview recorded', j.pages); }

    function pushEvent(cfg, eventName, extra) {
      var j = getJourney();
      var payload = { event: eventName, cro_conversion_id: cfg.conversionId || 'unknown', cro_trigger_type: cfg.triggerType, cro_landing_page: j.landingPage, cro_pages_visited: buildPagesString(j.pages), cro_journey_length: j.pages.length, cro_submission_page: encodeSlug(window.location.href), cro_session_ms: Date.now() - j.startTime };
      var mergeAll = [getDeviceInfo(), getLocaleInfo(), getSourceInfo(), getBehaviorMetrics(), getABDimensions()];
      for (var m = 0; m < mergeAll.length; m++) {
        var src = mergeAll[m];
        for (var k1 in src) { if (Object.prototype.hasOwnProperty.call(src, k1) && payload[k1] === undefined) payload[k1] = src[k1]; }
      }
      for (var i = 0; i < OPTIONAL_PARAMS.length; i++) payload[OPTIONAL_PARAMS[i]] = undefined;
      if (extra) for (var k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) payload[k] = extra[k];
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push(payload);
      log(cfg.conversionId, 'Event → ' + eventName, payload);
    }

    function attemptKey(id) { return 'cro_attempt_' + id; }
    function setAttempt(id, page) { try { sessionStorage.setItem(attemptKey(id), JSON.stringify({ page: page, ts: Date.now(), status: 'pending' })); } catch(e) {} }
    function clearAttempt(id) { try { sessionStorage.removeItem(attemptKey(id)); } catch(e) {} }
    function getAttempt(id) { try { return JSON.parse(sessionStorage.getItem(attemptKey(id))); } catch(e) { return null; } }
    function checkStaleAttempt(cfg) { var a = getAttempt(cfg.conversionId); if (!a || a.status !== 'pending') return; if ((Date.now() - a.ts) > (cfg.timeout || 15000)) { clearAttempt(cfg.conversionId); if (cfg.eventFailed) pushEvent(cfg, cfg.eventFailed, { cro_fail_reason: 'stale_attempt', cro_submission_page: a.page }); log(cfg.conversionId, 'Stale attempt → fired as fail'); } }

    function getScope(cfg) { if (!cfg.conversionSelector) return document; return document.querySelector(cfg.conversionSelector) || document; }
    function scopedQuery(cfg, selector) { var scope = getScope(cfg); return scope === document ? document.querySelector(selector) : scope.querySelector(selector); }
    function findSuccessEl(cfg) { if (cfg.successGlobal) return document.querySelector(cfg.successSelector); return scopedQuery(cfg, cfg.successSelector); }
    function isSuccessVisible(el) { if (!el) return false; if (!el.offsetWidth && !el.offsetHeight && !el.getClientRects().length) return false; var cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return false; return true; }

    function watchForSuccess(cfg, clickTime) {
      var fired = false, observer, pollInterval, failTimer, validationTimer;
      function cleanup() { if (observer) observer.disconnect(); if (pollInterval) clearInterval(pollInterval); if (failTimer) clearTimeout(failTimer); if (validationTimer) clearTimeout(validationTimer); }
      function fireSuccess(how) { if (fired) return; fired = true; cleanup(); clearAttempt(cfg.conversionId); pushEvent(cfg, cfg.eventSuccess, { cro_success_selector: cfg.successSelector, cro_elapsed_ms: Date.now() - clickTime, cro_detection: how }); log(cfg.conversionId, 'SUCCESS (' + how + ') — after ' + (Date.now() - clickTime) + 'ms'); }
      function fireFail(reason) { if (fired) return; fired = true; cleanup(); clearAttempt(cfg.conversionId); if (cfg.eventFailed) pushEvent(cfg, cfg.eventFailed, { cro_fail_reason: reason, cro_elapsed_ms: Date.now() - clickTime }); log(cfg.conversionId, 'FAIL (' + reason + ')'); }
      function checkNow() { if (fired) return; var el = findSuccessEl(cfg); if (isSuccessVisible(el)) fireSuccess(observer ? 'mutation' : 'poll'); }
      if (cfg.validationErrorSelector) validationTimer = setTimeout(function() { if (fired) return; var errEl = scopedQuery(cfg, cfg.validationErrorSelector); if (errEl && isSuccessVisible(errEl)) fireFail('validation_error'); }, 500);
      observer = new MutationObserver(checkNow);
      observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class', 'hidden'], characterData: true });
      pollInterval = setInterval(checkNow, 300);
      failTimer = setTimeout(function() { fireFail('timeout'); }, cfg.timeout || 15000);
    }

    function bindDomChange(cfg) {
      var scope = getScope(cfg);
      var clickTarget = scope === document ? document.body : scope;
      var initialSuccessEl = findSuccessEl(cfg);
      if (isSuccessVisible(initialSuccessEl)) {
        console.warn('[CRO:' + cfg.conversionId + '] ⚠ Success element đã visible từ page load — config có thể sai:', cfg.successSelector);
      }
      clickTarget.addEventListener('click', function(e) {
        if (scope !== document && !scope.contains(e.target)) return;
        var matched = null, el = e.target;
        while (el && el !== clickTarget) {
          if (el.tagName === 'BUTTON' || (el.tagName === 'INPUT' && el.getAttribute('type') === 'submit') || el.getAttribute('type') === 'submit') { matched = el; break; }
          el = el.parentElement;
        }
        if (!matched) return;
        if (getAttempt(cfg.conversionId)) return;
        var clickTime = Date.now();
        setAttempt(cfg.conversionId, encodeSlug(window.location.href));
        log(cfg.conversionId, 'Attempt started — watching for success');
        watchForSuccess(cfg, clickTime);
      }, true);
      log(cfg.conversionId, 'dom_change bound:', cfg.conversionSelector, '→', cfg.successSelector, cfg.successGlobal ? '(global)' : '(scoped)');
    }

    function bindCf7(cfg) {
      var scope = getScope(cfg);
      var target = scope === document ? document : scope;
      var forms = target.tagName === 'FORM' ? [target] : target.querySelectorAll('form');
      if (!forms.length) { log(cfg.conversionId, 'CF7: no forms found'); return; }
      forms.forEach(function(form) {
        form.addEventListener('submit', function() {
          setAttempt(cfg.conversionId, encodeSlug(window.location.href));
          var successClass = cfg.cf7SuccessClass || 'wpcf7-mail-sent-ok';
          var failClasses = cfg.cf7FailClasses || ['wpcf7-mail-sent-ng', 'wpcf7-validation-errors', 'wpcf7-spam-blocked'];
          var responseSelector = cfg.cf7ResponseSelector || '.wpcf7-response-output';
          var timer;
          var observer = new MutationObserver(function() {
            var responseScope = getScope(cfg);
            var el = (responseScope === document ? document : responseScope).querySelector(responseSelector);
            if (!el) return;
            if (el.classList.contains(successClass)) { observer.disconnect(); clearTimeout(timer); clearAttempt(cfg.conversionId); pushEvent(cfg, cfg.eventSuccess, { cro_cf7_class: successClass }); return; }
            for (var i = 0; i < failClasses.length; i++) if (el.classList.contains(failClasses[i])) { observer.disconnect(); clearTimeout(timer); clearAttempt(cfg.conversionId); if (cfg.eventFailed) pushEvent(cfg, cfg.eventFailed, { cro_fail_reason: failClasses[i] }); return; }
          });
          observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
          timer = setTimeout(function() { if (getAttempt(cfg.conversionId)) { observer.disconnect(); clearAttempt(cfg.conversionId); if (cfg.eventFailed) pushEvent(cfg, cfg.eventFailed, { cro_fail_reason: 'timeout' }); } }, cfg.timeout || 15000);
        });
      });
    }

    function checkThankYouUrl(cfg) {
      var path = window.location.pathname, query = window.location.search, hit = false;
      if (cfg.thankYouPath && path.indexOf(cfg.thankYouPath) !== -1) hit = true;
      if (cfg.thankYouParam && query.indexOf(cfg.thankYouParam + '=') !== -1) hit = true;
      if (!hit) return false;
      // v2.5.1: nếu cfg.requireAttempt=true → chỉ fire khi form match (cfg.conversionId)
      // đã có attempt active trong sessionStorage. Dùng khi nhiều form share cùng
      // thank-you URL, mỗi form có conversionSelector riêng phân biệt.
      var attempt = getAttempt(cfg.conversionId);
      if (cfg.requireAttempt && !attempt) {
        log(cfg.conversionId, 'SKIP — thank-you URL matched but no attempt for this form');
        return false;
      }
      var guid = '';
      if (cfg.thankYouParam) { var match = query.match(new RegExp('[?&]' + cfg.thankYouParam + '=([^&]+)')); if (match) guid = decodeURIComponent(match[1]); }
      clearAttempt(cfg.conversionId);
      pushEvent(cfg, cfg.eventSuccess, { cro_thank_you_path: path, cro_submission_guid: guid, cro_submission_page: attempt ? attempt.page : encodeSlug(window.location.href) });
      return true;
    }

    function bindThankYouUrl(cfg) {
      if (checkThankYouUrl(cfg)) return;
      var scope = getScope(cfg);
      var target = scope === document ? document : scope;
      // Standard forms in main DOM
      var forms = target.tagName === 'FORM' ? [target] : target.querySelectorAll('form');
      forms.forEach(function(form) { form.addEventListener('submit', function() { setAttempt(cfg.conversionId, encodeSlug(window.location.href)); }); });
      // HubSpot fires hsFormCallback from parent window (not iframe) — e.source matching fails.
      // Use onFormSubmit (before redirect) + formId + modal-context to distinguish same-formId embeds.
      window.addEventListener('message', function(e) {
        var data;
        try { data = typeof e.data === 'string' ? JSON.parse(e.data) : e.data; } catch(ex) { return; }
        if (!data || data.type !== 'hsFormCallback') return;
        if (data.eventName !== 'onFormSubmit') return;
        if (cfg.hubspotFormId && data.id !== cfg.hubspotFormId) return;
        // Same-formId disambiguation via modal visibility at submit time.
        // Works for any modal implementation that uses role="dialog" or class="modal".
        if (cfg.hubspotFormId && target !== document) {
          var modalAncestor = target.closest ? (target.closest('[role="dialog"]') || target.closest('.modal')) : null;
          if (modalAncestor) {
            // Scope is inside a modal → only proceed when that modal is currently visible
            if (getComputedStyle(modalAncestor).display === 'none') return;
            log(cfg.conversionId, 'modal ancestor visible — proceeding');
          } else {
            // Scope is outside any modal → skip when any modal is currently open
            var dialogs = document.querySelectorAll('[role="dialog"], .modal');
            for (var m = 0; m < dialogs.length; m++) {
              if (getComputedStyle(dialogs[m]).display !== 'none') {
                log(cfg.conversionId, 'SKIP — modal is open, this form is not the active one');
                return;
              }
            }
          }
        }
        setAttempt(cfg.conversionId, encodeSlug(window.location.href));
        log(cfg.conversionId, 'HubSpot form submit via postMessage id=' + data.id);
      });
    }

    function bindUrlContains(cfg) {
      document.addEventListener('click', function(e) {
        var el = e.target;
        while (el && el.tagName !== 'A') el = el.parentElement;
        if (!el) return;
        var href = el.getAttribute('href') || '';
        if (href.indexOf(cfg.urlContains) !== -1) pushEvent(cfg, cfg.eventSuccess, { cro_clicked_url: href, cro_clicked_text: (el.innerText || '').trim().slice(0, 80) });
      });
    }

    function bindTextContains(cfg) {
      var tags = cfg.targetTag || 'a,button,div,span,p';
      document.addEventListener('click', function(e) {
        var el = e.target;
        while (el && el !== document.body) {
          if (el.matches && el.matches(tags)) {
            var text = (el.innerText || el.textContent || '').trim();
            if (text.indexOf(cfg.textContains) !== -1) { pushEvent(cfg, cfg.eventSuccess, { cro_clicked_text: text.slice(0, 80), cro_clicked_tag: el.tagName.toLowerCase(), cro_clicked_href: el.getAttribute('href') || '' }); return; }
          }
          el = el.parentElement;
        }
      });
    }

    function bindClickClass(cfg) {
      if (!cfg.classContains) return;
      var pattern = String(cfg.classContains).replace(/^\./, '');
      document.addEventListener('click', function(e) {
        var el = e.target;
        while (el && el !== document.body) {
          var cls = (el.className && typeof el.className === 'string') ? el.className : (el.getAttribute && el.getAttribute('class')) || '';
          if (cls && cls.indexOf(pattern) !== -1) {
            pushEvent(cfg, cfg.eventSuccess, {
              cro_clicked_class: cls.slice(0, 120),
              cro_clicked_tag:   el.tagName.toLowerCase(),
              cro_clicked_text:  ((el.innerText || el.textContent || '').trim()).slice(0, 80),
              cro_clicked_href:  el.getAttribute && el.getAttribute('href') || ''
            });
            return;
          }
          el = el.parentElement;
        }
      });
    }

    function bindPageUrlContains(cfg) {
      if (!cfg.pageUrlContains) return;
      var pattern = cfg.pageUrlContains;
      var fired = false;
      function check() {
        if (fired) return;
        var url = window.location.href;
        if (url.indexOf(pattern) !== -1) {
          fired = true;
          pushEvent(cfg, cfg.eventSuccess, {
            cro_page_url:     url.slice(0, 200),
            cro_page_pattern: pattern,
            cro_page_title:   (document.title || '').slice(0, 120)
          });
        }
      }
      check();
      window.addEventListener('popstate', function() { fired = false; check(); });
      var origPush = history.pushState;
      history.pushState = function() { var r = origPush.apply(this, arguments); fired = false; check(); return r; };
      var origReplace = history.replaceState;
      history.replaceState = function() { var r = origReplace.apply(this, arguments); fired = false; check(); return r; };
    }

    function bindDataAttribute(cfg) {
      if (!cfg.dataAttribute) return;
      var spec = String(cfg.dataAttribute);
      var eq = spec.indexOf('=');
      var attrName = eq === -1 ? spec.trim() : spec.substring(0, eq).trim();
      var attrValue = eq === -1 ? null : spec.substring(eq + 1).trim();
      document.addEventListener('click', function(e) {
        var el = e.target;
        while (el && el !== document.body) {
          if (el.getAttribute) {
            var actual = el.getAttribute(attrName);
            if (actual !== null && (attrValue === null || actual === attrValue)) {
              pushEvent(cfg, cfg.eventSuccess, {
                cro_clicked_tag:   el.tagName.toLowerCase(),
                cro_clicked_text:  ((el.innerText || el.textContent || '').trim()).slice(0, 80),
                cro_clicked_attr:  attrName + '=' + (actual || ''),
                cro_clicked_href:  (el.getAttribute && el.getAttribute('href')) || ''
              });
              return;
            }
          }
          el = el.parentElement;
        }
      });
      log(cfg.conversionId, 'data_attribute bound: ' + attrName + (attrValue ? '="' + attrValue + '"' : ' (any value)'));
    }

    function bindHubspotChat(cfg) {
      function attach(api) {
        api.on('conversationStarted', function(payload) {
          var convId = (payload && payload.conversation && payload.conversation.conversationId) || '';
          pushEvent(cfg, cfg.eventSuccess, {
            cro_clicked_tag:  'iframe',
            cro_clicked_text: 'hubspot_chat_started',
            cro_clicked_attr: 'conversationId=' + convId
          });
          log(cfg.conversionId, 'HubSpot conversation started', convId);
        });
        log(cfg.conversionId, 'hubspot_chat bound via HubSpotConversations API');
      }
      if (window.HubSpotConversations) {
        attach(window.HubSpotConversations);
      } else {
        window.hsConversationsOnReady = window.hsConversationsOnReady || [];
        window.hsConversationsOnReady.push(function() { attach(window.HubSpotConversations); });
      }
    }

    function bindFormSubmit(cfg) {
      var scope = getScope(cfg);
      var target = scope === document ? document : scope;
      var forms = target.tagName === 'FORM' ? [target] : target.querySelectorAll('form');
      forms.forEach(function(form) { form.addEventListener('submit', function() { pushEvent(cfg, cfg.eventSuccess, {}); }); });
    }

    function bindButtonClick(cfg) {
      var matcher = cfg.conversionSelector || '';
      var matchType = 'selector';
      var matchPattern = matcher;
      if (matcher.indexOf('text:') === 0) { matchType = 'text'; matchPattern = matcher.slice(5).trim(); }
      else if (matcher.indexOf('url:') === 0) { matchType = 'url'; matchPattern = matcher.slice(4).trim(); }

      function fire(el) {
        var extras = {
          cro_clicked_tag:   el.tagName.toLowerCase(),
          cro_clicked_text:  ((el.innerText || el.textContent || '').trim()).slice(0, 80),
          cro_clicked_href:  (el.getAttribute && el.getAttribute('href')) || '',
          cro_clicked_class: ((el.className && typeof el.className === 'string') ? el.className : (el.getAttribute && el.getAttribute('class')) || '').slice(0, 120),
          cro_match_mode:    matchType
        };
        if (cfg.successSelector) {
          if (getAttempt(cfg.conversionId)) return;
          var clickTime = Date.now();
          setAttempt(cfg.conversionId, encodeSlug(window.location.href));
          watchForSuccess(cfg, clickTime);
        } else {
          pushEvent(cfg, cfg.eventSuccess, extras);
        }
      }

      if (matchType === 'selector') {
        var btns = document.querySelectorAll(matchPattern);
        if (!btns.length) { log(cfg.conversionId, 'SKIP — selector not found:', matchPattern); return; }
        btns.forEach(function(btn) { btn.addEventListener('click', function() { fire(btn); }); });
        log(cfg.conversionId, 'button_click bound (selector): ' + matchPattern + ' → ' + btns.length + ' element(s)');
      } else if (matchType === 'text') {
        document.addEventListener('click', function(e) {
          var el = e.target;
          while (el && el !== document.body) {
            if (el.matches && el.matches('a,button,div,span,p')) {
              var text = (el.innerText || el.textContent || '').trim();
              if (text.indexOf(matchPattern) !== -1) { fire(el); return; }
            }
            el = el.parentElement;
          }
        });
        log(cfg.conversionId, 'button_click bound (text contain): "' + matchPattern + '"');
      } else if (matchType === 'url') {
        document.addEventListener('click', function(e) {
          var el = e.target;
          while (el && el.tagName !== 'A') el = el.parentElement;
          if (!el) return;
          var href = el.getAttribute('href') || '';
          if (href.indexOf(matchPattern) !== -1) fire(el);
        });
        log(cfg.conversionId, 'button_click bound (url contain): "' + matchPattern + '"');
      }
    }

    function trackFormInteraction(cfg) {
      if (!cfg.eventFormStart || !cfg.conversionSelector) return;
      var scope = document.querySelector(cfg.conversionSelector);
      if (!scope) return;
      var form = scope.tagName === 'FORM' ? scope : (scope.querySelector('form') || scope);
      var started = false;
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function(entries) { if (entries[0].isIntersecting) { pushEvent(cfg, cfg.eventFormStart, { cro_interaction: 'form_in_view' }); io.disconnect(); } }, { threshold: 0.2 });
        io.observe(form);
      }
      form.addEventListener('focusin', function() { if (!started) { started = true; pushEvent(cfg, cfg.eventFormStart, { cro_interaction: 'form_focus' }); } }, { once: true });
      form.addEventListener('focusout', function() { setTimeout(function() { if (started && !form.contains(document.activeElement)) pushEvent(cfg, cfg.eventFormStart, { cro_interaction: 'form_abandon' }); }, 200); });
    }

    function initConversion(cfg) {
      if (!cfg.conversionId || !cfg.triggerType) return;
      var type = cfg.triggerType;
      var needsSelector = ['dom_change', 'cf7_class', 'form_submit', 'button_click'];
      var sel = cfg.conversionSelector || '';
      var isPrefixed = type === 'button_click' && (sel.indexOf('text:') === 0 || sel.indexOf('url:') === 0);
      if (needsSelector.indexOf(type) !== -1 && cfg.conversionSelector && !isPrefixed) {
        if (!document.querySelector(cfg.conversionSelector)) { log(cfg.conversionId, 'SKIP — selector not found:', cfg.conversionSelector); return; }
      }
      log(cfg.conversionId, 'Initializing', type);
      if (type === 'url_contains') { bindUrlContains(cfg); return; }
      if (type === 'text_contains') { bindTextContains(cfg); return; }
      if (type === 'click_class') { bindClickClass(cfg); return; }
      if (type === 'page_url_contains') { bindPageUrlContains(cfg); return; }
      if (type === 'data_attribute') { bindDataAttribute(cfg); return; }
      if (type === 'hubspot_chat') { bindHubspotChat(cfg); return; }
      if (type === 'thank_you_url') { bindThankYouUrl(cfg); return; }
      function onDomReady() {
        checkStaleAttempt(cfg);
        if (type === 'cf7_class') bindCf7(cfg);
        if (type === 'dom_change') bindDomChange(cfg);
        if (type === 'form_submit') bindFormSubmit(cfg);
        if (type === 'button_click') bindButtonClick(cfg);
        trackFormInteraction(cfg);
      }
      if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', onDomReady);
      else onDomReady();
    }

    function init() {
      recordPageView();
      captureFirstTouch();
      initBehaviorTracking();
      initABTests();
      var configs = Array.isArray(CRO_CONFIG) ? CRO_CONFIG : [CRO_CONFIG];
      configs.forEach(function(cfg) { try { initConversion(cfg); } catch(e) { if (GLOBAL.debug) console.error('[CRO] Error in', cfg.conversionId, e); } });
      log(null, 'CRO Engine v2.5 started — ' + configs.length + ' config(s) loaded, ' + AB_TESTS.length + ' A/B test(s)');
    }

    init();
  })();
"""


def build_engine_html(config: dict) -> str:
    """Generate the full <script>...</script> for [CRO] Journey Tracker tag."""
    project = config.get("project", {})
    forms = config.get("forms", [])
    others = config.get("others", [])
    ab_tests = config.get("abTests", [])

    client_name = project.get("clientName", "")
    gtm_id = project.get("gtmContainerId", "(chưa khai báo)")

    form_list = _build_form_list_entries(forms) or \
        "        // (không có form dom_change/cf7_class standard)"
    map_block = _build_map_block(forms)
    extras = _build_extras(forms, others)
    ab_block = _build_ab_tests_block(ab_tests)

    header = f"""<script data-cfasync="false">
/**
 * ============================================================
 *  CRO TRACKING ENGINE — Custom HTML Tag for GTM
 *  Version: 2.5 — Expanded dimensions (Display, Device, Locale, Source, Behavior) + A/B Split
 *  Generated by /cro-setup for: {client_name}
 *  GTM Container: {gtm_id}
 * ============================================================
 */
;(function() {{

    if (window.__CRO_ENGINE_LOADED__) {{
      console.log('[CRO:core] Already loaded — skip duplicate init');
      return;
    }}
    window.__CRO_ENGINE_LOADED__ = true;

    /* ══════════════════════════════════════════════════════════
       PHẦN 1 — CONFIG (cro-setup generated)
       ══════════════════════════════════════════════════════════ */

    var FORM_LIST = [
{form_list}
    ];{map_block}{extras}

    var AB_TESTS = [
{ab_block}
    ];
"""

    return header + _ENGINE_RUNTIME + "</" + "script>"


if __name__ == "__main__":
    # Smoke test
    import json
    import sys

    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            cfg = json.load(f)
    else:
        cfg = {
            "project": {"clientName": "Test", "gtmContainerId": "GTM-XXXXXXX"},
            "forms": [
                {"name": "footer_form", "triggerType": "dom_change",
                 "formSelector": "#contact-form", "successSelector": ".success-msg"}
            ],
            "others": [
                {"name": "phone_click", "triggerType": "url_contains", "pattern": "tel:"}
            ],
            "abTests": []
        }
    print(build_engine_html(cfg))
