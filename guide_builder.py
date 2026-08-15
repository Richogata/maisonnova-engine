# -*- coding: utf-8 -*-
"""Génération du GUIDE D'INSTALLATION INTERACTIF (client_guide.html).

Un fichier HTML autonome (CSS + JS inclus, aucune dépendance externe payante) :
  - écran d'accueil personnalisé (agence, site, progression %) ;
  - choix de plateforme : WordPress / Wix / Webflow / Site personnalisé / « Je ne sais pas » ;
  - mini-assistant de détection (« Je ne sais pas ») ;
  - étapes par plateforme, entièrement data-driven (guide_content) ;
  - « Je suis bloqué » → dépannage interactif (cause → solution → test → si ça ne marche toujours pas) ;
  - FAQ en accordéons ;
  - bloc « Instructions pour mon webmaster » avec bouton copier ;
  - checklist de vérification finale ;
  - progression sauvegardée localement (localStorage) — reprise où on s'est arrêté.

Aucun secret serveur n'est embarqué : uniquement l'identifiant du client, sa clé
d'installation et son code public.
"""

import html as html_mod
import json
import os

import guide_content
import widget_code


def guides_dir() -> str:
    d = os.getenv("GUIDES_DIR", "guides")
    os.makedirs(d, exist_ok=True)
    return d


def _replace_key(data: dict) -> dict:
    """Insère la clé d'installation dans les textes des étapes (%%KEY%%)."""
    return data


def build_guide_html(client: dict, content: dict | None = None,
                     code: str | None = None, key: str | None = None,
                     webmaster: str | None = None) -> str:
    """Construit le HTML complet du guide pour un client."""
    content = content or guide_content.load_content()
    install = client.get("install") or {}
    key = key or install.get("key") or ""
    code = code or widget_code.script_snippet(client)
    webmaster = webmaster or widget_code.webmaster_block(client)
    ag = client.get("agency") or {}
    ct = client.get("contact") or {}
    app = client.get("appearance") or {}
    site = ct.get("website") or ag.get("app_url") or ""

    platforms = json.loads(json.dumps(content.get("platforms") or {}))
    for pkey, pdata in platforms.items():
        for step in pdata.get("steps", []):
            for f in ("t", "d", "help"):
                if step.get(f):
                    step[f] = step[f].replace("%%KEY%%", key)

    data = {
        "agency": {
            "id": client.get("id") or "",
            "slug": client.get("slug") or "",
            "name": ag.get("name") or "",
            "logo": ag.get("logo_url") or "",
            "site": site,
            "email": ag.get("email") or "",
            "colors": {"primary": app.get("primary_color") or "#C9A227",
                       "secondary": app.get("secondary_color") or "#9C7A14"},
        },
        "code": code,
        "key": key,
        "webmaster": webmaster,
        "platforms": platforms,
        "faq": content.get("faq") or [],
        "issues": content.get("issues") or {},
        "verify": content.get("verify") or [],
        "support": ag.get("email") or "",
    }
    data_json = json.dumps(data, ensure_ascii=False)
    data_json = data_json.replace("</", "<\\/").replace("<!--", "<\\!--")

    return _TEMPLATE \
        .replace("@@DATA@@", data_json) \
        .replace("@@AGENCY_NAME@@", html_mod.escape(ag.get("name") or "votre agence")) \
        .replace("@@PRIMARY@@", data["agency"]["colors"]["primary"]) \
        .replace("@@SECONDARY@@", data["agency"]["colors"]["secondary"])


def generate_guide_file(client: dict, content: dict | None = None) -> str:
    """Écrit guides/{client_id}_guide.html et retourne le chemin."""
    html_str = build_guide_html(client, content)
    cid = client.get("id") or client.get("slug") or "client"
    path = os.path.join(guides_dir(), f"{cid}_guide.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_str)
    return path


# ───────────────────────────────────────────────────────────────────────────────
# Template (placeholders : @@DATA@@, @@AGENCY_NAME@@, @@PRIMARY@@, @@SECONDARY@@)
# ───────────────────────────────────────────────────────────────────────────────

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Installation de votre assistant IA — @@AGENCY_NAME@@</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:wght@500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --primary: @@PRIMARY@@; --primary-dark: @@SECONDARY@@;
  --ink: #161616; --gray: #8E8E93; --soft: #FBF6E5; --bubble: #F4F4F6;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif; background:#fff; color:var(--ink); line-height:1.6; }
h1,h2,h3 { font-family:'Playfair Display',serif; letter-spacing:-.01em; }
.wrap { max-width:720px; margin:0 auto; padding:18px 18px 60px; position:relative; }
header { display:flex; align-items:center; justify-content:space-between; padding:10px 0 16px; border-bottom:1px solid #eee; margin-bottom:18px; }
.brand { display:flex; align-items:center; gap:10px; font-weight:800; font-size:15px; }
.brand .logo { width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(135deg, #fff, var(--primary)); color:var(--primary); font-size:16px; }
.brand small { display:block; font-weight:500; color:var(--gray); font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; }
.bar { height:8px; border-radius:999px; background:#ECECEF; overflow:hidden; margin:10px 0 4px; }
.bar i { display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,var(--primary),var(--primary-dark));
  width:0%; transition:width .5s ease; }
.pct { text-align:right; font-size:12px; color:var(--gray); font-weight:600; }
.card { background:linear-gradient(145deg, rgba(255,255,255,.92), rgba(255,255,255,.7));
  backdrop-filter:blur(18px); border:1px solid rgba(0,0,0,.06); border-radius:22px;
  box-shadow:0 10px 34px rgba(31,38,66,.08); padding:26px; margin:14px 0; }
.card h2 { font-size:24px; margin-bottom:6px; }
.muted { color:var(--gray); font-size:13.5px; }
.center { text-align:center; }
.hero-logo { width:76px; height:76px; margin:0 auto 14px; border-radius:22px; object-fit:cover;
  box-shadow:0 10px 26px rgba(0,0,0,.15); background:var(--soft); }
.hero-logo-fallback { width:76px; height:76px; margin:0 auto 14px; border-radius:22px; display:flex;
  align-items:center; justify-content:center; font-size:36px; background:linear-gradient(135deg,var(--soft),#fff);
  border:1px solid #eee; }
button { font-family:'Inter',sans-serif; font-weight:700; border:none; cursor:pointer; border-radius:14px;
  padding:13px 20px; font-size:14.5px; transition:transform .15s ease, box-shadow .15s ease; }
button:hover { transform:translateY(-1px); }
.btn-primary { background:linear-gradient(135deg,var(--primary),var(--primary-dark)); color:#fff;
  box-shadow:0 10px 24px rgba(0,0,0,.18); width:100%; }
.btn-ghost { background:#fff; color:var(--ink); border:1px solid rgba(0,0,0,.1); width:100%; }
.btn-soft { background:var(--soft); color:var(--primary-dark); width:100%; }
.btn-row { display:flex; gap:10px; margin-top:14px; }
.btn-row button { flex:1; }
.btn-sm { padding:9px 14px; font-size:13px; border-radius:11px; width:auto; }
.plat-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.plat { background:#fff; border:1.5px solid #eee; border-radius:18px; padding:20px 12px; text-align:center; cursor:pointer;
  font-weight:700; font-size:14.5px; transition:all .18s ease; }
.plat:hover { border-color:var(--primary); transform:translateY(-2px); box-shadow:0 10px 22px rgba(0,0,0,.08); }
.plat .ic { font-size:28px; display:block; margin-bottom:6px; }
.plat.wide { grid-column:1 / -1; }
.step { display:flex; gap:14px; align-items:flex-start; }
.step-num { flex:0 0 40px; height:40px; border-radius:13px; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(135deg,var(--primary),var(--primary-dark)); color:#fff; font-weight:800; font-size:16px; }
.step h3 { font-size:19px; margin-bottom:4px; }
.tag { display:inline-block; background:var(--soft); color:var(--primary-dark); font-size:11px; font-weight:800;
  padding:3px 10px; border-radius:999px; letter-spacing:.06em; text-transform:uppercase; margin-bottom:8px; }
.acc { border:1px solid #eee; border-radius:14px; margin:8px 0; overflow:hidden; background:#fff; }
.acc summary { padding:14px 16px; cursor:pointer; font-weight:600; font-size:14.5px; list-style:none; display:flex; justify-content:space-between; align-items:center; }
.acc summary::after { content:"+"; color:var(--primary); font-weight:800; font-size:18px; }
.acc[open] summary::after { content:"–"; }
.acc p { padding:0 16px 14px; color:#444; font-size:14px; }
code, pre { font-family:'SF Mono',Menlo,Consolas,monospace; }
pre { background:#1C1C1E; color:#E8E8E8; border-radius:14px; padding:14px; font-size:12px; overflow-x:auto;
  max-height:260px; white-space:pre-wrap; word-break:break-all; }
.copybar { display:flex; justify-content:flex-end; margin-top:8px; }
.check { display:flex; gap:12px; align-items:flex-start; padding:13px 14px; border:1.5px solid #eee;
  border-radius:14px; margin:8px 0; cursor:pointer; background:#fff; transition:border-color .15s; }
.check.checked { border-color:var(--primary); background:var(--soft); }
.check input { margin-top:4px; width:18px; height:18px; accent-color:var(--primary); }
.overlay { position:fixed; inset:0; background:rgba(20,20,24,.45); backdrop-filter:blur(4px); display:none;
  align-items:flex-start; justify-content:center; padding:30px 14px; overflow-y:auto; z-index:50; }
.overlay.open { display:flex; }
.modal { background:#fff; border-radius:22px; max-width:640px; width:100%; padding:24px; position:relative;
  box-shadow:0 30px 80px rgba(0,0,0,.25); }
.modal .close { position:absolute; top:14px; right:14px; background:#F2F2F7; border:none; border-radius:50%;
  width:34px; height:34px; font-size:15px; cursor:pointer; }
.screen { display:none; }
.screen.active { display:block; animation:fade .25s ease; }
@keyframes fade { from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:none;} }
.issue { display:block; width:100%; text-align:left; background:#fff; border:1.5px solid #eee; border-radius:14px;
  padding:14px 16px; margin:7px 0; font-weight:600; cursor:pointer; font-size:14px; }
.issue:hover { border-color:var(--primary); }
.done-icon { font-size:64px; text-align:center; margin-bottom:8px; }
.foot { margin-top:30px; text-align:center; color:var(--gray); font-size:12.5px; }
.spacer { height:10px; }
@media (max-width:520px){ .plat-grid{grid-template-columns:1fr;} }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="brand"><span class="logo">🏡</span><div>MaisonNova AI<small>Guide d'installation</small></div></div>
    <button class="btn-sm btn-ghost" onclick="goHome()">Accueil</button>
  </header>

  <!-- ═══ ACCUEIL ═══ -->
  <section id="s-home" class="screen active">
    <div class="card center">
      <div id="heroLogo"></div>
      <div class="tag">Installation de votre assistant IA</div>
      <h2>Bienvenue chez MaisonNova AI</h2>
      <p class="muted" style="margin-top:8px;">Pas besoin de connaissances techniques : suivez simplement les étapes ci-dessous, une par une. Votre progression est sauvegardée automatiquement.</p>
      <p class="muted" style="margin-top:10px;">Votre assistant pour :</p>
      <p style="font-weight:800; font-size:19px; margin:4px 0 2px;">@@AGENCY_NAME@@</p>
      <p class="muted">Site : <span id="homeSite" style="font-weight:600;color:var(--ink);"></span></p>
      <p class="muted" style="margin-top:8px;">Plateforme : <span id="homePlatform" style="font-weight:700;color:var(--primary-dark);">À sélectionner</span></p>
      <div style="margin:14px 0 0;">
        <div class="bar"><i id="homeBar"></i></div>
        <div class="pct">Progression : <b id="homePct">0 %</b></div>
      </div>
      <div class="spacer"></div>
      <button class="btn-primary" onclick="startGuide()">Commencer</button>
    </div>
    <h3 style="margin:22px 0 6px;">Questions fréquentes</h3>
    <div id="faqBox"></div>
  </section>

  <!-- ═══ CHOIX DE PLATEFORME ═══ -->
  <section id="s-platform" class="screen">
    <div class="card">
      <div class="tag">Étape 0 / Choix de la plateforme</div>
      <h2>Sur quelle plateforme est votre site ?</h2>
      <p class="muted" style="margin:6px 0 16px;">Cliquez sur votre plateforme : le guide affichera uniquement les étapes correspondantes.</p>
      <div class="plat-grid">
        <div class="plat" onclick="choosePlatform('wordpress')"><span class="ic">🔵</span>WordPress</div>
        <div class="plat" onclick="choosePlatform('wix')"><span class="ic">🟣</span>Wix</div>
        <div class="plat" onclick="choosePlatform('webflow')"><span class="ic">🔷</span>Webflow</div>
        <div class="plat" onclick="choosePlatform('custom')"><span class="ic">🛠️</span>Site personnalisé</div>
        <div class="plat wide" onclick="showDetect()"><span class="ic">🤔</span>Je ne sais pas</div>
      </div>
    </div>
  </section>

  <!-- ═══ DÉTECTION « JE NE SAIS PAS » ═══ -->
  <section id="s-detect" class="screen">
    <div class="card">
      <div class="tag">Je ne sais pas</div>
      <h2>Identifions votre plateforme</h2>
      <p class="muted" style="margin:6px 0 14px;">1. Entrez l'adresse de votre site. 2. Analysez. 3. Nous essayons de la détecter automatiquement.</p>
      <input id="detectUrl" type="text" placeholder="https://www.mon-agence.fr" style="width:100%; padding:13px 16px; border-radius:14px; border:1.5px solid #ddd; font-size:15px; margin-bottom:10px;">
      <button class="btn-primary" onclick="detectNow()">Analyser</button>
      <div id="detectResult" style="margin-top:14px;"></div>
    </div>
  </section>

  <!-- ═══ GUIDE (ÉTAPES) ═══ -->
  <section id="s-guide" class="screen">
    <div class="card">
      <div class="tag" id="gTag">—</div>
      <div class="bar"><i id="gBar"></i></div>
      <div class="pct" id="gPct">0 / 0</div>
      <div id="stepBox" style="margin-top:14px;"></div>
      <div class="btn-row">
        <button class="btn-ghost" onclick="prevStep()">← Retour</button>
        <button class="btn-soft" onclick="openTroubleshoot()">Je suis bloqué</button>
        <button class="btn-primary" id="gNext" onclick="nextStep()">Étape suivante →</button>
      </div>
      <div class="btn-row" style="margin-top:8px;">
        <button class="btn-ghost btn-sm" onclick="openWebmaster()" style="width:100%;">🤝 Je travaille avec un webmaster</button>
      </div>
    </div>
    <div class="card">
      <h3 style="margin-bottom:6px;">Questions fréquentes</h3>
      <div id="faqBox2"></div>
    </div>
  </section>

  <!-- ═══ VÉRIFICATION FINALE ═══ -->
  <section id="s-verify" class="screen">
    <div class="card">
      <div class="tag">Vérification finale</div>
      <h2>Tester mon installation</h2>
      <p class="muted" style="margin:6px 0 12px;">Cochez chaque point une fois vérifié sur votre site.</p>
      <div id="verifyBox"></div>
      <div class="btn-row" style="margin-top:16px;">
        <button class="btn-ghost" onclick="goBackToGuide()">← Revenir aux étapes</button>
        <button class="btn-primary" onclick="finish()">Installation terminée</button>
      </div>
    </div>
  </section>

  <!-- ═══ TERMINÉ ═══ -->
  <section id="s-done" class="screen">
    <div class="card center">
      <div class="done-icon">✅</div>
      <div class="tag">Installation terminée</div>
      <h2>Votre assistant est prêt.</h2>
      <p class="muted" style="margin:8px 0 16px;">Vos visiteurs peuvent désormais être qualifiés et prendre rendez-vous. Merci pour votre confiance !</p>
      <button class="btn-ghost" onclick="goHome()">Retour à l'accueil</button>
    </div>
  </section>

  <div class="foot">Propulsé par <b>MaisonNova Engine</b> · Besoin d'aide ? Contactez votre conseiller : <span id="footEmail"></span></div>
</div>

<!-- ═══ DÉPANNAGE ═══ -->
<div id="ov-trouble" class="overlay">
  <div class="modal">
    <button class="close" onclick="closeOverlay('ov-trouble')">✕</button>
    <div id="troubleList"></div>
    <div id="troubleDetail" style="display:none;"></div>
  </div>
</div>

<!-- ═══ WEBMASTER ═══ -->
<div id="ov-webmaster" class="overlay">
  <div class="modal">
    <button class="close" onclick="closeOverlay('ov-webmaster')">✕</button>
    <div class="tag">Instructions pour mon webmaster</div>
    <h2 style="margin-bottom:8px;">Bloc technique à transmettre</h2>
    <pre id="wmPre"></pre>
    <div class="copybar"><button class="btn-sm btn-primary" onclick="copyEl('wmPre', this)">COPIER LES INSTRUCTIONS POUR MON WEBMASTER</button></div>
  </div>
</div>

<script>
var MN = @@DATA@@;
var STORE_KEY = 'mn_guide_' + MN.agency.id;
function load(){ try{ return JSON.parse(localStorage.getItem(STORE_KEY))||null; }catch(e){ return null; } }
var state = load() || { platform:null, step:0, done:[], verify:{} };
function save(){ try{ localStorage.setItem(STORE_KEY, JSON.stringify(state)); }catch(e){} }

function $(id){ return document.getElementById(id); }
function esc(s){ var d=document.createElement('div'); d.textContent = (s==null?'':s); return d.innerHTML; }
function copyText(txt, btn){
  function ok(){ if(btn){ var o=btn.textContent; btn.textContent='✅ Copié !'; setTimeout(function(){btn.textContent=o;},1800);} }
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(ok, function(){ fallback(); });
  } else { fallback(); }
  function fallback(){ var ta=document.createElement('textarea'); ta.value=txt; document.body.appendChild(ta);
    ta.select(); try{ document.execCommand('copy'); }catch(e){} document.body.removeChild(ta); ok(); }
}
function copyEl(id, btn){ var pre=$(id); copyText(pre.textContent, btn); }

function show(id){ var s=document.querySelectorAll('.screen'); for(var i=0;i<s.length;i++){ s[i].classList.remove('active'); } $(id).classList.add('active'); window.scrollTo(0,0); }
function closeOverlay(id){ $(id).classList.remove('open'); }
function openOverlay(id){ $(id).classList.add('open'); }
function goHome(){ renderHome(); show('s-home'); }

function platformInfo(p){ return MN.platforms[p] || null; }
function totalSteps(){ var p=platformInfo(state.platform); return p? p.steps.length : 0; }
function doneCount(){ return state.done ? state.done.length : 0; }
function pct(){ var t=totalSteps(); return t? Math.round(doneCount()/t*100) : 0; }

function renderHome(){
  var a=MN.agency;
  var logo=a.logo ? '<img class="hero-logo" src="'+esc(a.logo)+'" onerror="this.style.display=\'none\'">' : '<div class="hero-logo-fallback">🏡</div>';
  $('heroLogo').innerHTML = logo;
  $('homeSite').textContent = a.site || '—';
  var pi = state.platform ? platformInfo(state.platform) : null;
  $('homePlatform').textContent = pi ? pi.title + ' ' + pi.icon : 'À sélectionner';
  $('homePct').textContent = pct() + ' %';
  $('homeBar').style.width = pct() + '%';
  renderFaq($('faqBox'));
}
function startGuide(){
  if(state.platform){ renderGuide(); show('s-guide'); }
  else { show('s-platform'); }
}
function choosePlatform(p){
  state.platform = p; state.step = 0; if(!state.done) state.done=[];
  save(); renderGuide(); show('s-guide');
}

/* ── détection ── */
function showDetect(){ $('detectUrl').value=''; $('detectResult').innerHTML=''; show('s-detect'); }
function detectNow(){
  var url = $('detectUrl').value.trim(); var box=$('detectResult');
  if(!url){ box.innerHTML='<p class="muted">Veuillez entrer l\'adresse de votre site.</p>'; return; }
  var u=url.toLowerCase();
  if(!/^https?:\/\//.test(u)) u='https://'+u;
  var found=null;
  if(/wixsite\.com|\.wix\.com|editor\.wix/.test(u)) found='wix';
  else if(/webflow\.io|webflow\.com/.test(u)) found='webflow';
  else if(/wordpress\.com|wp-admin|wp-content|\/wp-/.test(u)) found='wordpress';
  if(found){
    var pi=platformInfo(found);
    box.innerHTML='<p>Nous avons détecté : <b style="color:var(--primary-dark);">'+pi.icon+' '+esc(pi.title)+'</b></p>'+
      '<div class="btn-row" style="margin-top:12px;">'+
      '<button class="btn-primary" onclick="choosePlatform(\''+found+'\')">Oui, c\'est ça</button>'+
      '<button class="btn-ghost" onclick="detectFail()">Non</button></div>';
  } else {
    box.innerHTML='<p class="muted">Nous n\'avons pas pu identifier la plateforme automatiquement.</p>'+
      '<div class="btn-row" style="margin-top:12px;">'+
      '<button class="btn-soft" onclick="openWebmaster()">Mon site est géré par un webmaster</button>'+
      '<button class="btn-primary" onclick="choosePlatform(\'custom\')">Mon site est personnalisé</button></div>';
  }
}
function detectFail(){
  $('detectResult').innerHTML='<div class="btn-row" style="margin-top:12px;">'+
    '<button class="btn-soft" onclick="openWebmaster()">Mon site est géré par un webmaster</button>'+
    '<button class="btn-primary" onclick="choosePlatform(\'custom\')">Mon site est personnalisé</button></div>';
}

/* ── étapes ── */
function renderGuide(){
  var pi = platformInfo(state.platform);
  if(!pi){ show('s-platform'); return; }
  $('gTag').textContent = 'Étape ' + (state.step+1) + ' / ' + pi.steps.length + ' · ' + pi.title;
  $('gBar').style.width = (doneCount()/pi.steps.length*100) + '%';
  $('gPct').textContent = doneCount() + ' / ' + pi.steps.length + ' étapes faites';
  renderStep();
  renderFaq($('faqBox2'));
}
function renderStep(){
  var pi = platformInfo(state.platform);
  if(!pi) return;
  if(state.step >= pi.steps.length){ show('s-verify'); renderVerify(); return; }
  var s = pi.steps[state.step];
  var done = state.done.indexOf(state.step) >= 0;
  var html = '<div class="step"><div class="step-num">'+(state.step+1)+'</div><div style="flex:1;">'+
    '<h3>'+esc(s.t)+'</h3><p style="color:#444; font-size:14.5px; margin-top:4px;">'+esc(s.d)+'</p>';
  if(s.code){ html += '<div class="copybar"><button class="btn-sm btn-primary" onclick="copyText(MN.code, this)">COPIER LE CODE</button></div><pre></pre>'; }
  if(s.help){ html += '<p class="muted" style="margin-top:8px;">💡 '+esc(s.help)+'</p>'; }
  html += '</div></div>';
  $('stepBox').innerHTML = html;
  if(s.code){ var pre=$('stepBox').querySelector('pre'); if(pre) pre.textContent = MN.code; }
  $('gNext').textContent = done ? 'Étape suivante →' : (s.btn || 'J\'ai fait cette étape ✓');
}
function markStepDone(){
  if(state.done.indexOf(state.step) < 0) state.done.push(state.step);
  save();
}
function nextStep(){
  if(state.step < totalSteps()-1){ markStepDone(); state.step++; save(); renderGuide(); }
  else { markStepDone(); state.step = totalSteps(); save(); show('s-verify'); renderVerify(); }
}
function prevStep(){ if(state.step>0){ state.step--; save(); renderGuide(); } else { show('s-platform'); } }
function goBackToGuide(){ state.step = Math.min(state.step, totalSteps()-1); renderGuide(); show('s-guide'); }

/* ── vérification ── */
function renderVerify(){
  var items = MN.verify || [];
  var html='';
  for(var i=0;i<items.length;i++){
    var k='v'+i; var checked = state.verify[k] ? true : false;
    html += '<label class="check'+(checked?' checked':'')+'"><input type="checkbox" data-k="'+k+'" '+(checked?'checked':'')+'> <span>'+esc(items[i])+'</span></label>';
  }
  $('verifyBox').innerHTML = html;
  var boxes=$('verifyBox').querySelectorAll('input');
  for(var j=0;j<boxes.length;j++){ boxes[j].onchange=function(){ state.verify[this.getAttribute('data-k')] = this.checked; save();
    this.parentNode.classList.toggle('checked', this.checked); }; }
}
function finish(){ show('s-done'); }

/* ── FAQ ── */
function renderFaq(box){
  var items = MN.faq || []; var html='';
  for(var i=0;i<items.length;i++){
    html += '<details class="acc"><summary>'+esc(items[i].q)+'</summary><p>'+esc(items[i].a)+'</p></details>';
  }
  box.innerHTML = html;
}

/* ── dépannage ── */
function openTroubleshoot(issueKey){
  var list=$('troubleList'), det=$('troubleDetail');
  if(issueKey){ showIssue(issueKey); }
  else {
    det.style.display='none'; list.style.display='block';
    var html='<div class="tag">Je suis bloqué</div><h2 style="margin-bottom:8px;">Quel problème avez-vous ?</h2>';
    var keys=Object.keys(MN.issues||{});
    for(var i=0;i<keys.length;i++){ html += '<button class="issue" onclick="showIssue(\''+keys[i]+'\')">'+esc(MN.issues[keys[i]].label)+'</button>'; }
    list.innerHTML=html;
  }
  openOverlay('ov-trouble');
}
function showIssue(k){
  var it = MN.issues[k]; if(!it) return;
  var d=$('troubleDetail');
  d.innerHTML = '<div class="tag">Dépannage</div><h2 style="margin-bottom:6px;">'+esc(it.label)+'</h2>'+
    '<p style="margin:8px 0;"><b>🔎 Cause possible :</b><br>'+esc(it.cause)+'</p>'+
    '<p style="margin:8px 0;"><b>🛠️ Solution :</b><br>'+esc(it.solution)+'</p>'+
    '<p style="margin:8px 0;"><b>🧪 Test :</b><br>'+esc(it.test)+'</p>'+
    '<p style="margin:8px 0;"><b>📞 Si ça ne marche toujours pas :</b><br>'+esc(it.still)+'</p>'+
    '<div class="btn-row" style="margin-top:14px;"><button class="btn-ghost" onclick="openTroubleshoot()">← Autre problème</button>'+
    '<button class="btn-primary" onclick="closeOverlay(\'ov-trouble\')">Compris ✓</button></div>';
  $('troubleList').style.display='none'; d.style.display='block';
}

/* ── webmaster ── */
function openWebmaster(){ $('wmPre').textContent = MN.webmaster; openOverlay('ov-webmaster'); }

/* ── init ── */
(function(){
  $('footEmail').textContent = MN.agency.email || '';
  renderHome();
})();
</script>
</body>
</html>
"""
