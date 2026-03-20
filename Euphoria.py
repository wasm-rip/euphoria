"""
Euphoria  ·  UAR Gap Filler  ·  v2.0
Requires: Python 3.9+, tkinter (stdlib)
Authors: @dudeluther1232  @shxyder
"""

import tkinter as tk
from tkinter import filedialog, colorchooser
import threading, os, sys, time, json, re, hashlib, struct, uuid
from pathlib import Path

SETTINGS_PATH = Path.home() / ".unity_tools_v2.json"
DEFAULT_SETTINGS = {
    "theme": "Dark Blue", "accent_color": "", "font_size": 9,
    "ui_density": "Normal", "animations": True, "toast_duration": 3500,
    "toast_pos": "Bottom Right", "auto_scan": True, "scan_depth": 2,
    "compact_cards": False, "last_project": "", "card_style": "Default",
    "custom_fonts": {"title": "", "body": "", "mono": ""},
}

def load_settings():
    try:
        if SETTINGS_PATH.exists():
            d = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            s = dict(DEFAULT_SETTINGS); s.update(d); return s
    except Exception: pass
    return dict(DEFAULT_SETTINGS)

def save_settings(s):
    try: SETTINGS_PATH.write_text(json.dumps(s, indent=2), encoding="utf-8")
    except Exception: pass

SETTINGS = load_settings()

THEME_DEFS = {
    "Dark Blue": {
        "BG":"#05070d","SIDEBAR":"#070a11","CONTENT":"#080b13","CARD":"#0c1018",
        "CARD_HOV":"#111620","BORDER":"#151d2e","BORDER_LT":"#1e2d47",
        "ACCENT":"#1a6fff","ACCENT_DK":"#0d4adb","ACCENT_GL":"#1a3a6f",
        "TEXT":"#dde3f0","TEXT_DIM":"#4a5570","TEXT_MID":"#8892aa",
        "SUCCESS":"#0ec97a","ERROR_C":"#ff4a6e","WARN":"#f0a030",
    },
    "Midnight": {
        "BG":"#000000","SIDEBAR":"#080808","CONTENT":"#0a0a0a","CARD":"#111111",
        "CARD_HOV":"#1a1a1a","BORDER":"#1f1f1f","BORDER_LT":"#2e2e2e",
        "ACCENT":"#e0e0e0","ACCENT_DK":"#aaaaaa","ACCENT_GL":"#444444",
        "TEXT":"#ffffff","TEXT_DIM":"#555555","TEXT_MID":"#999999",
        "SUCCESS":"#00e676","ERROR_C":"#ff1744","WARN":"#ffa726",
    },
    "Cyberpunk": {
        "BG":"#08000f","SIDEBAR":"#0b0013","CONTENT":"#0d0016","CARD":"#130019",
        "CARD_HOV":"#190020","BORDER":"#290038","BORDER_LT":"#420058",
        "ACCENT":"#00ff88","ACCENT_DK":"#00bb66","ACCENT_GL":"#003322",
        "TEXT":"#d4ffea","TEXT_DIM":"#2a5a40","TEXT_MID":"#55aa77",
        "SUCCESS":"#00ff88","ERROR_C":"#ff0055","WARN":"#ffff00",
    },
    "Blood Red": {
        "BG":"#0d0000","SIDEBAR":"#110000","CONTENT":"#130000","CARD":"#1a0000",
        "CARD_HOV":"#220000","BORDER":"#2e0505","BORDER_LT":"#4a0808",
        "ACCENT":"#ff3333","ACCENT_DK":"#cc0000","ACCENT_GL":"#3a0000",
        "TEXT":"#ffe8e8","TEXT_DIM":"#5a2222","TEXT_MID":"#aa5555",
        "SUCCESS":"#ff8c00","ERROR_C":"#ff4444","WARN":"#ff6600",
    },
    "Deep Purple": {
        "BG":"#07040d","SIDEBAR":"#0a0611","CONTENT":"#0c0813","CARD":"#100c1a",
        "CARD_HOV":"#161220","BORDER":"#1e1630","BORDER_LT":"#30204a",
        "ACCENT":"#9933ff","ACCENT_DK":"#6600cc","ACCENT_GL":"#2a0044",
        "TEXT":"#e8d8ff","TEXT_DIM":"#4a3a5a","TEXT_MID":"#8a6aaa",
        "SUCCESS":"#33ff99","ERROR_C":"#ff3377","WARN":"#ffaa00",
    },
    "Hacker Green": {
        "BG":"#000a00","SIDEBAR":"#000e00","CONTENT":"#001100","CARD":"#001500",
        "CARD_HOV":"#001c00","BORDER":"#002500","BORDER_LT":"#003500",
        "ACCENT":"#00ff00","ACCENT_DK":"#00bb00","ACCENT_GL":"#003300",
        "TEXT":"#c8ffc8","TEXT_DIM":"#285a28","TEXT_MID":"#50aa50",
        "SUCCESS":"#00ff88","ERROR_C":"#ff4400","WARN":"#aaff00",
    },
    "Ocean": {
        "BG":"#020d12","SIDEBAR":"#031015","CONTENT":"#041318","CARD":"#061820",
        "CARD_HOV":"#0a2030","BORDER":"#0e2a3a","BORDER_LT":"#163a50",
        "ACCENT":"#00d4ff","ACCENT_DK":"#009acc","ACCENT_GL":"#003344",
        "TEXT":"#d0f0ff","TEXT_DIM":"#2a5060","TEXT_MID":"#508090",
        "SUCCESS":"#00ff88","ERROR_C":"#ff4a6e","WARN":"#ffd700",
    },
    "Amber": {
        "BG":"#0d0800","SIDEBAR":"#110a00","CONTENT":"#130c00","CARD":"#1a1100",
        "CARD_HOV":"#221600","BORDER":"#2e1f00","BORDER_LT":"#4a3300",
        "ACCENT":"#ffaa00","ACCENT_DK":"#cc8800","ACCENT_GL":"#3a2200",
        "TEXT":"#fff0cc","TEXT_DIM":"#5a4020","TEXT_MID":"#aa8844",
        "SUCCESS":"#88ff44","ERROR_C":"#ff4400","WARN":"#ffcc00",
    },
}

BG=SIDEBAR=CONTENT=CARD=CARD_HOV=BORDER=BORDER_LT=""
ACCENT=ACCENT_DK=ACCENT_GL=GLOW_LINE=""
TEXT=TEXT_DIM=TEXT_MID=SUCCESS=ERROR_C=WARN=""

def apply_theme(name=None, accent_override=None, rebuild_cb=None):
    global BG,SIDEBAR,CONTENT,CARD,CARD_HOV,BORDER,BORDER_LT
    global ACCENT,ACCENT_DK,ACCENT_GL,GLOW_LINE,TEXT,TEXT_DIM,TEXT_MID,SUCCESS,ERROR_C,WARN
    if name: SETTINGS["theme"] = name
    if accent_override is not None: SETTINGS["accent_color"] = accent_override
    t = dict(THEME_DEFS.get(SETTINGS["theme"], THEME_DEFS["Dark Blue"]))
    c = SETTINGS.get("accent_color","")
    if c:
        try:
            r,g,b = int(c[1:3],16),int(c[3:5],16),int(c[5:7],16)
            t["ACCENT"]    = c
            t["ACCENT_DK"] = f"#{max(0,r-35):02x}{max(0,g-35):02x}{max(0,b-35):02x}"
            t["ACCENT_GL"] = f"#{max(0,r-120):02x}{max(0,g-120):02x}{max(0,b-120):02x}"
        except Exception: pass
    BG=t["BG"]; SIDEBAR=t["SIDEBAR"]; CONTENT=t["CONTENT"]
    CARD=t["CARD"]; CARD_HOV=t["CARD_HOV"]; BORDER=t["BORDER"]; BORDER_LT=t["BORDER_LT"]
    ACCENT=t["ACCENT"]; ACCENT_DK=t["ACCENT_DK"]; ACCENT_GL=t["ACCENT_GL"]; GLOW_LINE=t["ACCENT"]
    TEXT=t["TEXT"]; TEXT_DIM=t["TEXT_DIM"]; TEXT_MID=t["TEXT_MID"]
    SUCCESS=t["SUCCESS"]; ERROR_C=t["ERROR_C"]; WARN=t["WARN"]
    save_settings(SETTINGS)
    if rebuild_cb: rebuild_cb()

apply_theme()

IS_WIN = sys.platform=="win32"; IS_MAC = sys.platform=="darwin"

def _ff(key, default):
    c = SETTINGS.get("custom_fonts",{}).get(key,"")
    return c if c else default

def FF_TITLE(): return _ff("title","Trebuchet MS" if IS_WIN else "Helvetica Neue")
def FF_BODY():  return _ff("body","Segoe UI"     if IS_WIN else "Helvetica Neue")
def FF_MONO():  return _ff("mono","Consolas"     if IS_WIN else "Menlo")

def fs(base): return max(7, base + (SETTINGS.get("font_size",9)-9))
def dp(v):
    m={"Compact":0.6,"Normal":1.0,"Comfortable":1.45}
    return max(1, int(v * m.get(SETTINGS.get("ui_density","Normal"),1.0)))

SHADER_NAME = "Wasmcomfix.shader"
SHADER_DIR  = "WASMCOM"   # sub-folder under Assets/Shaders/
SHADER_CONTENT = r'''Shader "WASMCOM/WASMCOMFIX"
{
    Properties
    {
        _MainTex("Font Atlas (SDF)", 2D) = "white" {}
        _FaceColor("Face Color", Color) = (1,1,1,1)
        _OutlineColor("Outline Color", Color) = (0,0,0,1)
        _OutlineWidth("Outline Thickness", Range(0,1)) = 0
        _OutlineSoftness("Outline Softness", Range(0,1)) = 0
        _GradientScale("Gradient Scale", float) = 5.0
        _Sharpness("Sharpness", Range(-1,1)) = 1
        _Weight("Text Weight", Range(-0.5,0.5)) = 0.5
    }

    SubShader
    {
        Tags { "Queue"="Transparent" "IgnoreProjector"="True" "RenderType"="Transparent" }
        ZWrite Off
        Lighting Off
        Cull Off
        Blend One OneMinusSrcAlpha

        Pass
        {
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            float4 _MainTex_ST;

            float4 _FaceColor;
            float4 _OutlineColor;
            float _OutlineWidth;
            float _OutlineSoftness;
            float _GradientScale;
            float _Sharpness;
            float _Weight;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv     : TEXCOORD0;
                float4 color  : COLOR;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv  : TEXCOORD0;
                float4 col : COLOR;
            };

            v2f vert(appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = TRANSFORM_TEX(v.uv, _MainTex);
                o.col = v.color;
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                float sdf = tex2D(_MainTex, i.uv).a;
                float scale = _GradientScale * (_Sharpness + 1);
                float dist = (sdf * scale - 0.5) - (_Weight * scale);
                float aa = fwidth(dist);
                float outline = _OutlineWidth * scale;
                float softness = _OutlineSoftness * scale + 1e-4;
                float effectiveSoftness = max(softness, aa);
                float alpha = smoothstep(-effectiveSoftness, effectiveSoftness, dist);
                float outlineAlpha = smoothstep(-effectiveSoftness - outline, effectiveSoftness - outline, dist);
                fixed4 col = lerp(_OutlineColor, _FaceColor, alpha);
                col.a = max(alpha, outlineAlpha);
                return col * i.col;
            }
            ENDCG
        }
    }
}
'''

def find_unity_projects():
    candidates=[]; home=Path.home()
    roots=[home/"Documents"/"Unity",home/"Unity",home/"Desktop",
           home/"dev",home/"projects",home/"Projects"]
    if IS_WIN: roots.append(Path("C:/Users"))
    depth = SETTINGS.get("scan_depth",2)
    def _scan(root, d):
        if d<0 or not root.exists(): return
        try:
            for item in root.iterdir():
                if item.is_dir():
                    if (item/"Assets").exists(): candidates.append(item)
                    elif d>0: _scan(item,d-1)
        except PermissionError: pass
    for r in roots: _scan(r, depth)
    seen=set(); out=[]
    for p in candidates:
        if p not in seen: seen.add(p); out.append(p)
    return out[:25]

def inject_shader(project_path: Path):
    try:
        d=project_path/"Assets"/"Shaders"/SHADER_DIR; d.mkdir(parents=True,exist_ok=True)
        dest=d/SHADER_NAME; dest.write_text(SHADER_CONTENT,encoding="utf-8")
        meta=dest.with_suffix(dest.suffix+".meta")
        if not meta.exists():
            g=uuid.uuid4().hex
            meta.write_text(f"fileFormatVersion: 2\nguid: {g}\nShaderImporter:\n"
                            f"  externalObjects: {{}}\n  defaultTextures: []\n"
                            f"  nonModifiableTextures: []\n  preprocessorOverride: 0\n"
                            f"  userData: \n  assetBundleName: \n  assetBundleVariant: \n",
                            encoding="utf-8")
        return True, f"Injected to {dest}"
    except Exception as e: return False, str(e)

_WASM_FLOAT_DEFAULTS = {
    "_GradientScale":5.0,"_Sharpness":1.0,
    "_Weight":0.5,"_OutlineWidth":0,"_OutlineSoftness":0,
}
_WASM_COLOR_DEFAULTS = {
    "_FaceColor":(1,1,1,1),"_OutlineColor":(0,0,0,1),
}
_WASM_TEX_DEFAULTS = ["_MainTex"]

def apply_wasm_shader_to_tmp_materials(project_path: Path, log_cb=None):
    shader_meta = project_path/"Assets"/"Shaders"/SHADER_DIR/(SHADER_NAME+".meta")
    shader_guid = None
    if shader_meta.exists():
        m = re.search(r'guid:\s*([0-9a-f]{32})', shader_meta.read_text(encoding="utf-8"))
        if m: shader_guid = m.group(1)
    if not shader_guid:
        if log_cb: log_cb("  ERROR: shader .meta not found – run inject first")
        return 0, ["Shader .meta missing"]

    TMP_MARKERS = ["_FaceColor","_GradientScale","_FaceDilate","_WeightNormal","_OutlineColor"]
    patched=0; errors=[]
    mat_files=list((project_path/"Assets").rglob("*.mat"))
    if log_cb: log_cb(f"  Checking {len(mat_files)} .mat file(s) for TMP materials...")

    for mat_path in mat_files:
        try:
            src=mat_path.read_text(encoding="utf-8",errors="replace")
            if not any(mk in src for mk in TMP_MARKERS): continue

            changed=False; txt=src

            txt2=re.sub(
                r'm_Shader:\s*\{[^}]*\}',
                f'm_Shader: {{fileID: 4800000, guid: {shader_guid}, type: 3}}',
                txt)
            if txt2!=txt: txt=txt2; changed=True

            for prop,val in _WASM_FLOAT_DEFAULTS.items():
                if prop not in txt:
                    v=int(val) if float(val)==int(val) else val
                    txt=re.sub(r'(    m_Floats:\n)',
                               f'\\1    - {prop}: [{v}]\n', txt, count=1)
                    changed=True

            for prop,(r,g,b,a) in _WASM_COLOR_DEFAULTS.items():
                if prop not in txt:
                    txt=re.sub(r'(    m_Colors:\n)',
                               f'\\1    - {prop}: {{r: {r}, g: {g}, b: {b}, a: {a}}}\n',
                               txt, count=1)
                    changed=True

            for tex in _WASM_TEX_DEFAULTS:
                if tex not in txt:
                    txt=re.sub(r'(    m_TexEnvs:\n)',
                               f'\\1    - {tex}:\n        m_Texture: {{fileID: 0}}\n'
                               f'        m_Scale: {{x: 1, y: 1}}\n'
                               f'        m_Offset: {{x: 0, y: 0}}\n',
                               txt, count=1)
                    changed=True

            if changed:
                mat_path.write_text(txt,encoding="utf-8")
                patched+=1
                if log_cb: log_cb(f"  ✓  {mat_path.name}")
        except Exception as e:
            errors.append(f"{mat_path.name}: {e}")
            if log_cb: log_cb(f"  ERROR {mat_path.name}: {e}")

    if log_cb:
        log_cb(f"\n  ── Material Patch Summary ──")
        log_cb(f"  Patched {patched} TMP material(s)")
        if errors: log_cb(f"  {len(errors)} error(s) encountered")
    return patched, errors

def fix_script_guids(project_path: Path, log_cb=None):
    fixed=0; skipped=0; errors=[]
    assets=project_path/"Assets"
    for cs in assets.rglob("*.cs"):
        try:
            content=cs.read_text(encoding="utf-8",errors="replace")
            ns_m=re.search(r'namespace\s+([\w.]+)',content)
            ns=ns_m.group(1) if ns_m else ""
            cl_m=re.search(r'(?:class|struct|interface)\s+(\w+)',content)
            cl=cl_m.group(1) if cl_m else cs.stem
            key=f"{ns}.{cl}" if ns else cl
            guid=hashlib.md5(key.encode()).hexdigest()
            meta=cs.with_suffix(cs.suffix+".meta")
            if meta.exists():
                old=meta.read_text(encoding="utf-8")
                new=re.sub(r'guid: [0-9a-f]{32}',f'guid: {guid}',old)
                if new!=old:
                    meta.write_text(new,encoding="utf-8")
                    if log_cb: log_cb(f"  Updated {cs.name}  →  {guid}")
                    fixed+=1
                else: skipped+=1
            else:
                meta.write_text(
                    f"fileFormatVersion: 2\nguid: {guid}\nMonoImporter:\n"
                    f"  externalObjects: {{}}\n  serializedVersion: 2\n"
                    f"  defaultReferences: []\n  executionOrder: 0\n"
                    f"  icon: {{instanceID: 0}}\n  userData: \n"
                    f"  assetBundleName: \n  assetBundleVariant: \n",encoding="utf-8")
                if log_cb: log_cb(f"  Created .meta for {cs.name}  →  {guid}")
                fixed+=1
        except Exception as e:
            errors.append(f"{cs.name}: {e}")
            if log_cb: log_cb(f"  ERROR {cs.name}: {e}")
    return fixed, skipped, errors

# ── Unity Reference Fixer ─────────────────────────────────────────────────────
# Scans .prefab / .unity / .asset files for MonoBehaviour blocks whose
# m_Script GUID is missing (all-zeros or fileID:0) and attempts to
# re-link them by matching serialised field names against every .cs script
# in the project.

def _build_script_index(project_path: Path, log_cb=None):
    """
    Returns:
        guid_map  : {guid: {"class": str, "fields": set[str], "path": Path}}
        class_map : {class_name_lower: guid}
    """
    assets = project_path / "Assets"
    guid_map   = {}
    class_map  = {}

    for cs_path in assets.rglob("*.cs"):
        meta = cs_path.with_suffix(cs_path.suffix + ".meta")
        if not meta.exists():
            continue
        m = re.search(r'guid:\s*([0-9a-f]{32})', meta.read_text(encoding="utf-8", errors="replace"))
        if not m:
            continue
        guid = m.group(1)
        try:
            src = cs_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # extract class name
        cl_m = re.search(r'(?:class|struct)\s+(\w+)', src)
        class_name = cl_m.group(1) if cl_m else cs_path.stem

        # extract serialised field names (public or [SerializeField])
        fields: set[str] = set()
        for ln in src.splitlines():
            # public Type fieldName  or  [SerializeField] ... Type fieldName
            fm = re.search(r'(?:public|protected|private)\s+\S+\s+(\w+)\s*[;=\[]', ln)
            if fm:
                fields.add(fm.group(1))
            sfm = re.search(r'\[SerializeField\].*?(\w+)\s*[;=\[]', ln)
            if sfm:
                fields.add(sfm.group(1))

        guid_map[guid]  = {"class": class_name, "fields": fields, "path": cs_path}
        class_map[class_name.lower()] = guid

    if log_cb:
        log_cb(f"  Script index: {len(guid_map)} scripts catalogued")
    return guid_map, class_map


_MISSING_GUID_PATTERN = re.compile(
    r'm_Script:\s*\{fileID:\s*(\d+),\s*guid:\s*(0{32}|),\s*type:\s*\d+\}|'
    r'm_Script:\s*\{fileID:\s*0[^}]*\}'
)

def fix_missing_script_refs(project_path: Path, log_cb=None):
    """
    Re-links MonoBehaviour components whose m_Script reference is missing
    (all-zero GUID / fileID:0) back to the best-matching .cs script found
    in the project.

    Matching strategy (highest score wins):
      1. Class name appears literally in the block (e.g. a comment or type field) +5
      2. Serialised field overlap between the YAML block and the script        +n
    Returns (fixed, skipped, errors).
    """
    if log_cb: log_cb("  Building script index...")
    guid_map, class_map = _build_script_index(project_path, log_cb)
    if not guid_map:
        if log_cb: log_cb("  No .cs scripts found in project – nothing to do")
        return 0, 0, []

    exts   = ["*.unity", "*.prefab", "*.asset"]
    files  = []
    for ext in exts:
        files.extend((project_path / "Assets").rglob(ext))

    if log_cb: log_cb(f"  Scanning {len(files)} scene/prefab/asset file(s)...")

    fixed = 0; skipped = 0; errors = []

    # pre-compile per-script field matchers once
    script_field_sets = {g: info["fields"] for g, info in guid_map.items()}

    for f in files:
        try:
            src  = f.read_text(encoding="utf-8", errors="replace")
            out  = src
            hits = 0

            # split into YAML documents (--- blocks)
            raw_blocks = re.split(r'(\n---\s+)', src)

            for block in raw_blocks:
                if "MonoBehaviour:" not in block:
                    continue

                # check if m_Script is already valid (non-zero guid pointing at
                # a known project script)
                existing = re.search(
                    r'm_Script:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-f]{32}),\s*type:\s*\d+\}',
                    block)
                if existing:
                    eg = existing.group(1)
                    if eg != "0" * 32 and eg in guid_map:
                        skipped += 1
                        continue
                    # GUID exists but points nowhere in our index — treat as missing
                    if eg not in guid_map and eg != "0" * 32:
                        # unknown external package ref; skip it
                        skipped += 1
                        continue

                # --- missing reference path ---
                # extract YAML field keys from this block
                block_keys: set[str] = set(re.findall(r'^\s{2,}(\w+):', block, re.MULTILINE))

                best_guid  = None
                best_score = 0

                for g, info in guid_map.items():
                    score = 0
                    # class-name hint in the block
                    if info["class"].lower() in block.lower():
                        score += 5
                    # field overlap
                    overlap = len(block_keys & info["fields"])
                    score  += overlap

                    if score > best_score:
                        best_score = score
                        best_guid  = g

                if not best_guid or best_score < 1:
                    if log_cb:
                        log_cb(f"  ⚠  {f.name}: MonoBehaviour with no match (score=0) — skipped")
                    skipped += 1
                    continue

                info = guid_map[best_guid]
                new_ref = f'm_Script: {{fileID: 11500000, guid: {best_guid}, type: 3}}'

                # replace only the broken m_Script line in this block
                patched_block = re.sub(
                    r'm_Script:\s*\{[^}]*\}',
                    new_ref,
                    block,
                    count=1
                )
                if patched_block != block:
                    out = out.replace(block, patched_block, 1)
                    hits += 1
                    if log_cb:
                        log_cb(f"  ✓  {f.name}  →  {info['class']}  (score {best_score})")

            if hits:
                f.write_text(out, encoding="utf-8")
                fixed += hits

        except Exception as e:
            errors.append(f"{f.name}: {e}")
            if log_cb: log_cb(f"  ERROR {f.name}: {e}")

    if log_cb:
        log_cb(f"\n  ── Reference Fix Summary ──")
        log_cb(f"  Re-linked {fixed} missing script reference(s)")
        log_cb(f"  Skipped   {skipped} (already valid or unresolvable)")
        if errors: log_cb(f"  {len(errors)} error(s)")
    return fixed, skipped, errors

_BUILTIN_SHADER_REMAP = {
    "standard":              (46,     "0000000000000000f000000000000000", 0),
    "unlit/color":           (10753,  "0000000000000000f000000000000000", 0),
    "unlit/texture":         (10752,  "0000000000000000f000000000000000", 0),
    "unlit/transparent":     (10754,  "0000000000000000f000000000000000", 0),
    "unlit/transparent cutout": (10755, "0000000000000000f000000000000000", 0),
    "sprites/default":       (10754,  "0000000000000000f000000000000000", 0),
    "mobile/diffuse":        (10120,  "0000000000000000f000000000000000", 0),
    "legacy shaders/diffuse":(10120,  "0000000000000000f000000000000000", 0),
}

def fix_broken_shaders(project_path: Path, log_cb=None):
    assets = project_path / "Assets"

    project_shaders: dict[str, Path] = {}
    name_to_guid: dict[str, str] = {}
    for shader_file in assets.rglob("*.shader"):
        meta = shader_file.with_suffix(shader_file.suffix + ".meta")
        if meta.exists():
            m = re.search(r'guid:\s*([0-9a-f]{32})', meta.read_text(encoding="utf-8", errors="replace"))
            if m:
                g = m.group(1)
                project_shaders[g] = shader_file
                try:
                    first_line = shader_file.read_text(encoding="utf-8", errors="replace").split('\n')[0]
                    name_m = re.match(r'\s*Shader\s+"([^"]+)"', first_line)
                    if name_m:
                        name_to_guid[name_m.group(1).lower()] = g
                except Exception:
                    pass

    if log_cb:
        log_cb(f"  Found {len(project_shaders)} shader(s) in project")
        log_cb(f"  Known shader names: {list(name_to_guid.keys())[:6]}")

    mat_files = list(assets.rglob("*.mat"))
    if log_cb: log_cb(f"  Checking {len(mat_files)} material(s)...")

    fixed = 0; skipped = 0; errors = []

    for mat_path in mat_files:
        try:
            src = mat_path.read_text(encoding="utf-8", errors="replace")
            shader_m = re.search(r'm_Shader:\s*\{fileID:\s*(\d+),\s*guid:\s*([0-9a-f]{32}),\s*type:\s*(\d+)\}', src)
            if not shader_m:
                skipped += 1
                continue

            cur_file_id, cur_guid, cur_type = shader_m.group(1), shader_m.group(2), shader_m.group(3)

            if cur_guid in project_shaders:
                skipped += 1
                continue

            if cur_guid == "0000000000000000f000000000000000":
                skipped += 1
                continue

            new_file_id = new_guid = new_type = None

            mat_name_m = re.search(r'm_Name:\s*(.+)', src)
            mat_name = mat_name_m.group(1).strip().lower() if mat_name_m else ""

            for shader_name_lower, guid in name_to_guid.items():
                if shader_name_lower in mat_name or mat_name in shader_name_lower:
                    new_file_id, new_guid, new_type = "4800000", guid, "3"
                    if log_cb: log_cb(f"  ✓  {mat_path.name}  →  matched project shader '{shader_name_lower}'")
                    break

            if not new_guid:
                for shader_name_lower, guid in name_to_guid.items():
                    if any(kw in src for kw in ("_Color", "_MainTex", "_Glossiness", "_Metallic")):
                        if "standard" in shader_name_lower:
                            new_file_id, new_guid, new_type = "4800000", guid, "3"
                            if log_cb: log_cb(f"  ✓  {mat_path.name}  →  matched Standard-like shader in project")
                            break

            if not new_guid:
                mat_props = set(re.findall(r'- (\w+):', src))
                best_name = None; best_score = 0
                for sname_lower, guid in name_to_guid.items():
                    shader_file = project_shaders[guid]
                    try:
                        scontent = shader_file.read_text(encoding="utf-8", errors="replace")
                        shader_props = set(re.findall(r'(\w+)\s*\(', scontent))
                        score = len(mat_props & shader_props)
                        if score > best_score:
                            best_score = score; best_name = sname_lower; new_file_id, new_guid, new_type = "4800000", guid, "3"
                    except Exception:
                        pass
                if new_guid and log_cb:
                    log_cb(f"  ✓  {mat_path.name}  →  best-match shader '{best_name}' ({best_score} props)")

            if not new_guid:
                if log_cb: log_cb(f"  ⬡  {mat_path.name}  →  no project shader found, using built-in Standard")
                fid, g, tp = _BUILTIN_SHADER_REMAP["standard"]
                new_file_id, new_guid, new_type = str(fid), g, str(tp)

            patched_src = re.sub(
                r'm_Shader:\s*\{fileID:\s*\d+,\s*guid:\s*[0-9a-f]{32},\s*type:\s*\d+\}',
                f'm_Shader: {{fileID: {new_file_id}, guid: {new_guid}, type: {new_type}}}',
                src, count=1)
            mat_path.write_text(patched_src, encoding="utf-8")
            fixed += 1

        except Exception as e:
            errors.append(f"{mat_path.name}: {e}")
            if log_cb: log_cb(f"  ERROR {mat_path.name}: {e}")

    if log_cb:
        log_cb(f"\n  ── Shader Fix Summary ──")
        log_cb(f"  Fixed {fixed} material(s), skipped {skipped} (already valid)")
        if errors: log_cb(f"  {len(errors)} error(s)")
    return fixed, skipped, errors


_TMP_SIGNATURES = [
    ("TextMeshPro",     ["m_text:",    "m_fontAsset:",  "m_sharedMaterial:",
                         "m_isOrthographic:"]),
    ("TextMeshProUGUI", ["m_text:",    "m_fontAsset:",  "m_sharedMaterial:",
                         "m_raycastTarget:"]),
    ("TMP_InputField",  ["m_TextComponent:", "m_Placeholder:", "m_CaretBlinkRate:"]),
    ("TMP_Dropdown",    ["m_Template:", "m_CaptionText:", "m_ItemText:"]),
    ("TMP_SubMesh",     ["m_TextComponent:", "m_sharedMaterial:", "m_fontAsset:",
                         "m_isOrthographic:"]),
    ("TMP_SubMeshUI",   ["m_TextComponent:", "m_sharedMaterial:", "m_fontAsset:",
                         "m_raycastTarget:"]),
    ("TMP_FontAsset",   ["m_AtlasTextures:", "m_AtlasWidth:", "m_GlyphTable:",
                         "m_CharacterTable:"]),
    ("TMP_SpriteAsset", ["m_SpriteCharacterTable:", "m_SpriteGlyphTable:",
                         "m_spriteSheet:"]),
    ("TMP_Text",        ["m_text:", "m_fontAsset:"]),
]

_TMP_GUIDS = {
    "9541d86e2fd84c1d9990d2468cda992d": "TextMeshPro",
    "f4db1ef99e1c24d6bd28b3f9f9f2ebc5": "TextMeshProUGUI",
    "2da0c512f12947e489f739169773d7ca": "TMP_InputField",
    "d8b9819e293247e3b6bcfcbf4f6b3a5f": "TMP_Dropdown",
    "76b88bcd2fa3c4b5d8b25c55d9c77ea2": "TMP_FontAsset",
    "54ab2e9cbcc74baa9851196bb7c27b98": "TMP_SpriteAsset",
    "1f5fda8d07294a5cb8e67c4f72e7e96b": "TMP_SubMesh",
    "306cc8c2b49d7114eaa3623786fc2126": "TMP_SubMeshUI",
}

def _classify_monobehaviour(block: str):
    guid_m = re.search(r'm_Script:.*?guid:\s*([0-9a-f]{32})', block)
    if guid_m:
        g = guid_m.group(1).lower()
        if g in _TMP_GUIDS:
            return _TMP_GUIDS[g]

    best_type = None; best_score = 0
    for comp_type, sigs in _TMP_SIGNATURES:
        score = sum(1 for s in sigs if s in block)
        min_required = max(2, len(sigs) // 2)
        if score >= min_required and score > best_score:
            best_score = score; best_type = comp_type

    return best_type

def scan_tmp_components(project_path: Path, log_cb=None):
    results = []
    errors  = []
    total_files = 0

    exts = ["*.unity", "*.prefab", "*.asset"]
    files = []
    for ext in exts:
        files.extend((project_path / "Assets").rglob(ext))

    if not files:
        if log_cb: log_cb("  No .unity / .prefab / .asset files found in Assets/")
        return results, errors

    for f in files:
        total_files += 1
        try:
            src = f.read_text(encoding="utf-8", errors="replace")

            blocks = re.split(r'\n---\s+', src)

            go_names: dict[str, str] = {}
            for block in blocks:
                if "m_Name:" in block and "GameObject:" in block:
                    fid_m = re.search(r'&(\d+)', block)
                    name_m = re.search(r'm_Name:\s*(.+)', block)
                    if fid_m and name_m:
                        go_names[fid_m.group(1)] = name_m.group(1).strip()

            for block in blocks:
                if "MonoBehaviour:" not in block:
                    continue
                comp_type = _classify_monobehaviour(block)
                if not comp_type:
                    continue

                go_ref_m = re.search(r'm_GameObject:\s*\{fileID:\s*(\d+)', block)
                go_name = "?"
                if go_ref_m:
                    go_name = go_names.get(go_ref_m.group(1), f"fileID:{go_ref_m.group(1)}")

                char_pos = src.find(block[:60]) if len(block) > 60 else 0
                line_no  = src[:char_pos].count("\n") + 1 if char_pos > 0 else 0

                results.append({
                    "file":      f.name,
                    "path":      str(f.relative_to(project_path)),
                    "go_name":   go_name,
                    "component": comp_type,
                    "line":      line_no,
                })
                if log_cb:
                    log_cb(f"  [{comp_type}]  {go_name}  ←  {f.name}:{line_no}")

        except Exception as e:
            errors.append(f"{f.name}: {e}")
            if log_cb: log_cb(f"  ERROR {f.name}: {e}")

    if log_cb:
        from collections import Counter
        counts = Counter(r["component"] for r in results)
        log_cb(f"\n  ── Summary ({total_files} files scanned) ──")
        for comp, n in sorted(counts.items()):
            log_cb(f"  {comp:<22} {n} instance(s)")
        log_cb(f"\n  Total TMP objects found: {len(results)}")

    return results, errors

class RoundRect:
    @staticmethod
    def draw(canvas, x1,y1,x2,y2,r=8,**kw):
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,
             x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1,x1+r,y1]
        return canvas.create_polygon(pts,smooth=True,**kw)

class GlowButton(tk.Canvas):
    def __init__(self,parent,text,command,width=160,height=38,**kw):
        bg_color=kw.pop("bg",CONTENT)
        super().__init__(parent,width=width,height=height,
                         bg=bg_color,highlightthickness=0,cursor="hand2")
        self._text=text; self._cmd=command
        self._width=width; self._height=height
        self._pressed=False; self._hover=False
        self._draw()
        self.bind("<Enter>",self._on_enter); self.bind("<Leave>",self._on_leave)
        self.bind("<ButtonPress-1>",self._on_press)
        self.bind("<ButtonRelease-1>",self._on_release)

    def _draw(self):
        self.delete("all")
        w,h=self._width,self._height
        bg=ACCENT_DK if self._pressed else ("#2276ff" if self._hover else ACCENT)
        if self._hover and not self._pressed:
            for i in range(3,0,-1):
                RoundRect.draw(self,i,i,w-i,h-i,r=9,fill="",outline=ACCENT,width=1)
        RoundRect.draw(self,2,2,w-2,h-2,r=7,fill=bg,outline="")
        self.create_line(6,3,w-6,3,fill=ACCENT_GL,width=1)
        self.create_text(w//2,h//2,text=self._text,fill=TEXT,
                         font=(FF_BODY(),fs(10),"bold"))

    def _on_enter(self,_): self._hover=True; self._draw()
    def _on_leave(self,_): self._hover=False; self._pressed=False; self._draw()
    def _on_press(self,_): self._pressed=True; self._draw()
    def _on_release(self,_):
        self._pressed=False; self._hover=True; self._draw()
        if self._cmd: self._cmd()

    def set_text(self,t): self._text=t; self._draw()

class OutlineButton(tk.Canvas):
    def __init__(self,parent,text,command,width=130,height=32,**kw):
        bg_c=kw.pop("bg",CARD)
        super().__init__(parent,width=width,height=height,
                         bg=bg_c,highlightthickness=0,cursor="hand2")
        self._text=text; self._cmd=command
        self._width=width; self._height=height
        self._hover=False; self._draw()
        self.bind("<Enter>",lambda _:self._set(True))
        self.bind("<Leave>",lambda _:self._set(False))
        self.bind("<ButtonRelease-1>",lambda _:self._cmd() if self._cmd else None)

    def _set(self,h): self._hover=h; self._draw()

    def _draw(self):
        self.delete("all")
        w,h=self._width,self._height
        col=BORDER_LT if self._hover else BORDER
        RoundRect.draw(self,1,1,w-1,h-1,r=6,
                       fill=CARD_HOV if self._hover else "",outline=col,width=1)
        self.create_text(w//2,h//2,text=self._text,
                         fill=TEXT if self._hover else TEXT_MID,
                         font=(FF_BODY(),fs(9)))

class ToggleSwitch(tk.Canvas):
    def __init__(self,parent,value=True,on_change=None,**kw):
        super().__init__(parent,width=46,height=24,
                         highlightthickness=0,**kw)
        self._val=value; self._cb=on_change
        self._draw()
        self.bind("<ButtonRelease-1>",self._toggle)
        self.bind("<Enter>",lambda _:self._draw(hover=True))
        self.bind("<Leave>",lambda _:self._draw(hover=False))

    def _draw(self,hover=False):
        self.delete("all")
        w,h=46,24
        track=ACCENT if self._val else BORDER
        RoundRect.draw(self,1,1,w-1,h-1,r=11,fill=track,outline="")
        x=w-14 if self._val else 14
        self.create_oval(x-9,3,x+9,h-3,fill=TEXT if self._val else TEXT_DIM,outline="")
        self.configure(cursor="hand2" if hover else "")

    def _toggle(self,_):
        self._val=not self._val; self._draw()
        if self._cb: self._cb(self._val)

    @property
    def value(self): return self._val
    def set(self,v): self._val=v; self._draw()

class SliderWidget(tk.Canvas):
    def __init__(self,parent,min_val,max_val,value,on_change=None,
                 width=200,label_fmt="{:.0f}",**kw):
        super().__init__(parent,width=width,height=28,highlightthickness=0,**kw)
        self._min=min_val; self._max=max_val; self._val=value
        self._cb=on_change; self._fmt=label_fmt; self._sw=width
        self._dragging=False
        self._draw()
        self.bind("<ButtonPress-1>",self._press)
        self.bind("<B1-Motion>",self._drag)
        self.bind("<ButtonRelease-1>",self._release)

    def _frac(self): return (self._val-self._min)/(self._max-self._min) if self._max!=self._min else 0

    def _draw(self):
        self.delete("all")
        w=self._sw; cx=int(8+(w-16)*self._frac())
        self.create_rectangle(8,12,w-8,16,fill=BORDER,outline="")
        self.create_rectangle(8,12,cx,16,fill=ACCENT,outline="")
        self.create_oval(cx-7,4,cx+7,20,fill=ACCENT,outline=ACCENT_DK)
        lbl=self._fmt.format(self._val)
        self.create_text(w//2,24,text=lbl,fill=TEXT_DIM,font=(FF_BODY(),fs(7)))

    def _x_to_val(self,x):
        w=self._sw; frac=max(0,min(1,(x-8)/(w-16)))
        raw=self._min+frac*(self._max-self._min)
        if isinstance(self._min,int) and isinstance(self._max,int):
            return int(round(raw))
        return round(raw,2)

    def _press(self,e): self._dragging=True; self._set(e.x)
    def _drag(self,e):
        if self._dragging: self._set(e.x)
    def _release(self,e): self._dragging=False

    def _set(self,x):
        v=self._x_to_val(x)
        if v!=self._val:
            self._val=v; self._draw()
            if self._cb: self._cb(v)

    @property
    def value(self): return self._val
    def set(self,v): self._val=v; self._draw()

class ProgressBar(tk.Canvas):
    def __init__(self,parent,width=400,**kw):
        super().__init__(parent,width=width,height=6,highlightthickness=0,**kw)
        self._width=width; self._pct=0; self._draw()

    def _draw(self):
        self.delete("all")
        w=self._width
        self.create_rectangle(0,0,w,6,fill=BORDER,outline="")
        fill_w=int(w*self._pct)
        if fill_w>0:
            self.create_rectangle(0,0,fill_w,6,fill=ACCENT,outline="")

    def set(self,pct):
        self._pct=max(0,min(1,pct)); self._draw()

class LogBox(tk.Frame):
    def __init__(self,parent,height=120,**kw):
        super().__init__(parent,bg=CARD,**kw)
        self._txt=tk.Text(self,height=6,bg="#060c18",fg=TEXT_MID,
                          font=(FF_MONO(),fs(8)),wrap="word",
                          state="disabled",relief="flat",bd=0,
                          highlightthickness=1,highlightbackground=BORDER,
                          insertbackground=ACCENT)
        sb=tk.Scrollbar(self,command=self._txt.yview,bg=BORDER)
        self._txt.configure(yscrollcommand=sb.set)
        self._txt.pack(side="left",fill="both",expand=True)
        sb.pack(side="right",fill="y")

    def append(self,line):
        self._txt.configure(state="normal")
        self._txt.insert("end",line+"\n")
        self._txt.see("end")
        self._txt.configure(state="disabled")

    def clear(self):
        self._txt.configure(state="normal")
        self._txt.delete("1.0","end")
        self._txt.configure(state="disabled")

class Toast:
    W,H=320,72; PAD=18; SPEED=14

    def __init__(self,root):
        self._root=root; self._win=None; self._after=None
        self._alpha=1.0; self._cur_y=0.0; self._tgt_y=0.0; self._tx=0

    def show(self,title,body,success=True):
        self._cancel()
        w=self._root.winfo_width(); h=self._root.winfo_height()
        rx=self._root.winfo_rootx(); ry=self._root.winfo_rooty()
        tw=self.W; th=self.H
        pos=SETTINGS.get("toast_pos","Bottom Right")
        if pos=="Bottom Right":   tx=rx+w-tw-self.PAD; ty=ry+h-th-self.PAD; sy=ry+h+10
        elif pos=="Bottom Left":  tx=rx+self.PAD;      ty=ry+h-th-self.PAD; sy=ry+h+10
        elif pos=="Top Right":    tx=rx+w-tw-self.PAD; ty=ry+self.PAD;      sy=ry-th-10
        else:                     tx=rx+self.PAD;      ty=ry+self.PAD;      sy=ry-th-10

        self._win=tk.Toplevel(self._root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost",True)
        self._win.configure(bg=BG)
        try: self._win.attributes("-alpha",0.0)
        except Exception: pass

        cv=tk.Canvas(self._win,width=tw,height=th,bg=BG,highlightthickness=0)
        cv.pack()
        RoundRect.draw(cv,1,1,tw-1,th-1,r=10,fill=CARD,outline=BORDER_LT,width=1)
        RoundRect.draw(cv,2,10,5,th-10,r=2,fill=SUCCESS if success else ERROR_C,outline="")
        cv.create_text(22,th//2,text="✓" if success else "✕",
                       fill=SUCCESS if success else ERROR_C,font=(FF_BODY(),fs(14),"bold"))
        cv.create_text(38,th//2-9,text=title,anchor="w",fill=TEXT,font=(FF_BODY(),fs(10),"bold"))
        cv.create_text(38,th//2+9,text=body,anchor="w",fill=TEXT_MID,font=(FF_BODY(),fs(8)))

        self._win.geometry(f"{tw}x{th}+{tx}+{sy}")
        self._cur_y=float(sy); self._tgt_y=float(ty); self._tx=tx
        self._alpha=0.0
        if SETTINGS.get("animations",True): self._slide_in()
        else:
            self._alpha=1.0
            try: self._win.attributes("-alpha",1.0); self._win.geometry(f"{tw}x{th}+{tx}+{ty}")
            except Exception: pass
            self._after=self._root.after(SETTINGS.get("toast_duration",3500),self._cancel)

    def _slide_in(self):
        if not self._win: return
        going_down=self._tgt_y>float(self._root.winfo_rooty())
        if going_down: moved=self._cur_y<=self._tgt_y
        else: moved=self._cur_y>=self._tgt_y
        if not moved:
            self._cur_y+=(self.SPEED if going_down else -self.SPEED)
        else:
            self._cur_y=self._tgt_y
        self._alpha=min(1.0,self._alpha+0.12)
        try:
            self._win.geometry(f"{self.W}x{self.H}+{self._tx}+{int(self._cur_y)}")
            self._win.attributes("-alpha",self._alpha)
        except Exception: return
        if not moved:
            self._after=self._root.after(12,self._slide_in)
        else:
            self._after=self._root.after(SETTINGS.get("toast_duration",3500),self._start_fade)

    def _start_fade(self): self._fade()
    def _fade(self):
        if not self._win: return
        self._alpha-=0.08
        if self._alpha<=0: self._cancel(); return
        try: self._win.attributes("-alpha",max(0.0,self._alpha))
        except Exception: return
        self._after=self._root.after(20,self._fade)

    def _cancel(self):
        if self._after:
            try: self._root.after_cancel(self._after)
            except Exception: pass
            self._after=None
        if self._win:
            try: self._win.destroy()
            except Exception: pass
            self._win=None

class TutorialOverlay(tk.Frame):
    def __init__(self,parent,on_close):
        super().__init__(parent,bg="#0d1520")
        self.place(relx=0,rely=0,relwidth=1,relheight=1)
        self._on_close=on_close
        self.bind("<Button-1>",self._maybe_close)
        card=tk.Frame(self,bg=CARD,highlightthickness=1,highlightbackground=BORDER_LT)
        card.place(relx=0.5,rely=0.5,anchor="center",width=500)
        card.bind("<Button-1>",lambda e:"break")
        self._build_card(card)

    def _build_card(self,card):
        top=tk.Canvas(card,height=50,bg=CARD,highlightthickness=0)
        top.pack(fill="x")
        top.create_rectangle(0,0,500,50,fill="#0d1620",outline="")
        top.create_line(0,49,500,49,fill=BORDER,width=1)
        top.create_text(20,25,text="Shader Injected  ✓",anchor="w",
                        fill=SUCCESS,font=(FF_TITLE(),fs(11),"bold"))
        cb=tk.Label(top,text="✕",fg=TEXT_DIM,bg="#0d1620",font=(FF_BODY(),11),cursor="hand2")
        cb.place(relx=1.0,x=-14,rely=0.5,anchor="e")
        cb.bind("<Button-1>",lambda _:self._close())
        cb.bind("<Enter>",lambda _:cb.configure(fg=TEXT))
        cb.bind("<Leave>",lambda _:cb.configure(fg=TEXT_DIM))
        body=tk.Frame(card,bg=CARD); body.pack(fill="x",padx=24,pady=(18,24))
        tk.Label(body,text="Shader injected successfully into your Unity project.",
                 fg=TEXT,bg=CARD,font=(FF_BODY(),fs(9)),wraplength=450,justify="left").pack(anchor="w",pady=(0,16))
        for num,title,desc in [
            ("1","Find a TextMeshPro GameObject","In your Hierarchy, find any GameObject with a TextMeshPro component."),
            ("2","Select it","Click the object to open the Inspector."),
            ("3","Change Shader","In the TMP material, set Shader to: NPA → NPA Text Fix"),
            ("4","Apply to all","Repeat for every TMP object, or create a shared material."),
        ]:
            row=tk.Frame(body,bg=CARD); row.pack(fill="x",pady=5)
            bub=tk.Canvas(row,width=26,height=26,bg=CARD,highlightthickness=0); bub.pack(side="left",anchor="n",pady=2)
            RoundRect.draw(bub,1,1,25,25,r=13,fill=ACCENT_DK,outline="")
            bub.create_text(13,13,text=num,fill=TEXT,font=(FF_BODY(),fs(8),"bold"))
            tf=tk.Frame(row,bg=CARD); tf.pack(side="left",fill="x",expand=True,padx=(10,0))
            tk.Label(tf,text=title,fg=TEXT,bg=CARD,font=(FF_BODY(),fs(9),"bold"),anchor="w").pack(anchor="w")
            tk.Label(tf,text=desc,fg=TEXT_MID,bg=CARD,font=(FF_BODY(),fs(8)),wraplength=400,justify="left").pack(anchor="w")
        br=tk.Frame(card,bg=CARD); br.pack(fill="x",padx=24,pady=(0,20))
        GlowButton(br,"Got it",self._close,width=120,height=36,bg=CARD).pack(side="right")

    def _maybe_close(self,e):
        if e.widget is self: self._close()
    def _close(self):
        self.destroy()
        if self._on_close: self._on_close()

class ProjectPicker(tk.Frame):
    def __init__(self,parent,projects,on_pick,on_cancel):
        super().__init__(parent,bg="#080e18")
        self.place(relx=0,rely=0,relwidth=1,relheight=1)
        self._on_pick=on_pick; self._on_cancel=on_cancel
        card=tk.Frame(self,bg=CARD,highlightthickness=1,highlightbackground=BORDER_LT)
        card.place(relx=0.5,rely=0.5,anchor="center",width=480)
        hdr=tk.Canvas(card,height=46,bg=CARD,highlightthickness=0); hdr.pack(fill="x")
        hdr.create_rectangle(0,0,480,46,fill=SIDEBAR,outline="")
        hdr.create_line(0,45,480,45,fill=BORDER,width=1)
        hdr.create_text(18,23,text="Select Unity Project",anchor="w",fill=TEXT,font=(FF_TITLE(),fs(11),"bold"))
        body=tk.Frame(card,bg=CARD); body.pack(fill="x",padx=20,pady=(14,0))
        if projects:
            tk.Label(body,text="Detected projects:",fg=TEXT_MID,bg=CARD,font=(FF_BODY(),fs(8))).pack(anchor="w",pady=(0,6))
            lf=tk.Frame(body,bg=BORDER); lf.pack(fill="x")
            for p in projects[:8]:
                item=tk.Frame(lf,bg=CARD,cursor="hand2"); item.pack(fill="x",pady=1)
                lbl=tk.Label(item,text=p.name,fg=TEXT,bg=CARD,font=(FF_BODY(),fs(9),"bold"),padx=14,pady=8,anchor="w"); lbl.pack(side="left")
                sub=tk.Label(item,text=str(p.parent)[:50],fg=TEXT_DIM,bg=CARD,font=(FF_MONO(),fs(7)),padx=14,anchor="w"); sub.pack(side="left",fill="x",expand=True)
                def _pick(path=p):
                    self.destroy(); on_pick(path)
                for w in (item,lbl,sub):
                    w.bind("<Button-1>",lambda _,fn=_pick:fn())
                    w.bind("<Enter>",lambda _,f=item:f.configure(bg=CARD_HOV) or [c.configure(bg=CARD_HOV) for c in f.winfo_children()])
                    w.bind("<Leave>",lambda _,f=item:f.configure(bg=CARD) or [c.configure(bg=CARD) for c in f.winfo_children()])
            tk.Frame(body,bg=BORDER,height=1).pack(fill="x",pady=10)
        br=tk.Frame(body,bg=CARD); br.pack(fill="x",pady=(0,4))
        tk.Label(br,text="Or browse manually:",fg=TEXT_MID,bg=CARD,font=(FF_BODY(),fs(8))).pack(side="left")
        def _browse():
            p=filedialog.askdirectory(title="Select Unity project root")
            if p: self.destroy(); on_pick(Path(p))
        OutlineButton(br,"Browse...",_browse,width=100,height=28,bg=CARD).pack(side="right")
        ft=tk.Frame(card,bg=CARD); ft.pack(fill="x",padx=20,pady=(8,18))
        OutlineButton(ft,"Cancel",lambda:(self.destroy(),on_cancel()),width=80,height=30,bg=CARD).pack(side="right")

class Sidebar(tk.Canvas):
    ITEM_H=46; W=210

    def __init__(self,parent,items,on_select,**kw):
        super().__init__(parent,width=self.W,bg=SIDEBAR,highlightthickness=0,**kw)
        self._items=items; self._on_select=on_select
        self._active=items[0][0] if items else None; self._hover=None
        self._draw_logo(); self._draw_items()
        self.bind("<Motion>",self._on_motion)
        self.bind("<Leave>",self._on_leave)
        self.bind("<Button-1>",self._on_click)

    def _draw_logo(self):
        self.create_rectangle(0,0,self.W,64,fill=SIDEBAR,outline="")
        cx,cy=26,32
        self.create_polygon(cx,cy-10,cx+10,cy,cx,cy+10,cx-10,cy,fill=ACCENT,outline="")
        self.create_polygon(cx+1,cy-6,cx+6,cy,cx+1,cy+6,cx-4,cy,fill=ACCENT_DK,outline="")
        self.create_text(44,27,text="Euphoria",anchor="w",fill=TEXT,font=(FF_TITLE(),fs(11),"bold"))
        self.create_text(44,43,text="UAR Gap Filler",anchor="w",fill=TEXT_DIM,font=(FF_BODY(),fs(8)))
        self.create_line(16,64,self.W-16,64,fill=BORDER,width=1)
        self.create_text(16,82,text="MODULES",anchor="w",fill=TEXT_DIM,font=(FF_BODY(),fs(7)))

    def _item_y(self,idx): return 95+idx*self.ITEM_H

    def _draw_items(self):
        for t in [t for t in self.find_all() if "navitem" in (self.gettags(t) or [])]:
            self.delete(t)
        for i,(key,icon,label) in enumerate(self._items):
            y=self._item_y(i); active=(key==self._active); hovered=(key==self._hover)
            if active:
                self.create_rectangle(4,y,self.W-4,y+self.ITEM_H-2,fill="#111d35",outline="",tags="navitem")
                self.create_rectangle(4,y+4,6,y+self.ITEM_H-6,fill=ACCENT,outline="",tags="navitem")
            elif hovered:
                self.create_rectangle(4,y,self.W-4,y+self.ITEM_H-2,fill=CARD_HOV,outline="",tags="navitem")
            ic_col=ACCENT if active else (TEXT_MID if hovered else TEXT_DIM)
            lbl_col=TEXT if active else (TEXT_MID if hovered else TEXT_DIM)
            self.create_text(28,y+self.ITEM_H//2,text=icon,fill=ic_col,font=(FF_BODY(),fs(13)),tags="navitem")
            self.create_text(48,y+self.ITEM_H//2,text=label,anchor="w",fill=lbl_col,
                             font=(FF_BODY(),fs(9),"bold" if active else "normal"),tags="navitem")
        wh=self.winfo_reqheight() or 600
        self.create_text(self.W//2,wh-20,text="v2.0",fill=TEXT_DIM,font=(FF_BODY(),fs(8)))

    def _idx_at(self,y):
        for i in range(len(self._items)):
            iy=self._item_y(i)
            if iy<=y<iy+self.ITEM_H: return i
        return None

    def _on_motion(self,e):
        idx=self._idx_at(e.y)
        hk=self._items[idx][0] if idx is not None else None
        if hk!=self._hover:
            self._hover=hk; self.configure(cursor="hand2" if hk else ""); self._draw_items()

    def _on_leave(self,_):
        if self._hover: self._hover=None; self._draw_items()

    def _on_click(self,e):
        idx=self._idx_at(e.y)
        if idx is not None:
            key=self._items[idx][0]
            if key!=self._active:
                self._active=key; self._draw_items(); self._on_select(key)

    def set_active(self,key): self._active=key; self._draw_items()

class FixCard(tk.Frame):
    def __init__(self,parent,icon,title,subtitle,btn_label,on_execute,**kw):
        super().__init__(parent,bg=CARD,highlightthickness=1,
                         highlightbackground=BORDER,**kw)
        self._on_execute=on_execute; self._expanded=False

        hdr=tk.Frame(self,bg=CARD); hdr.pack(fill="x",padx=dp(18),pady=(dp(14),dp(14)))
        tf=tk.Frame(hdr,bg=CARD); tf.pack(side="left",fill="x",expand=True)
        tk.Label(tf,text=title,fg=TEXT,bg=CARD,font=(FF_BODY(),fs(10),"bold"),anchor="w").pack(anchor="w")
        tk.Label(tf,text=subtitle,fg=TEXT_DIM,bg=CARD,font=(FF_BODY(),fs(8)),anchor="w").pack(anchor="w",pady=(1,0))

        btn_frame=tk.Frame(hdr,bg=CARD); btn_frame.pack(side="right",anchor="center")
        self._status_lbl=tk.Label(btn_frame,text="",fg=TEXT_DIM,bg=CARD,font=(FF_BODY(),fs(7),"bold"))
        self._status_lbl.pack(anchor="e",pady=(0,2))
        self._btn=GlowButton(btn_frame,btn_label,self._run,width=110,height=30,bg=CARD)
        self._btn.pack()

        self._progress=ProgressBar(self,width=400)
        self._log=LogBox(self)

        self._expand_btn=tk.Label(self,text="▸ log",fg=TEXT_DIM,bg=CARD,
                                  font=(FF_BODY(),fs(7)),cursor="hand2")
        self._expand_btn.pack(anchor="w",padx=dp(18),pady=(0,6))
        self._expand_btn.bind("<Button-1>",self._toggle_log)

        self._running=False

    def _toggle_log(self,_=None):
        self._expanded=not self._expanded
        if self._expanded:
            self._progress.pack(fill="x",padx=dp(18),pady=(0,4))
            self._log.pack(fill="x",padx=dp(18),pady=(0,dp(8)))
            self._expand_btn.configure(text="▾ log")
        else:
            self._progress.pack_forget(); self._log.pack_forget()
            self._expand_btn.configure(text="▸ log")

    def _run(self):
        if self._running: return
        self._running=True; self._btn.set_text("Running...")
        self._status_lbl.configure(text="RUNNING",fg=WARN)
        if not self._expanded: self._toggle_log()
        self._log.clear(); self._progress.set(0)
        self._on_execute(self._log_line, self._done)

    def _log_line(self,msg):
        self.after(0,lambda:self._log.append(msg))

    def _done(self,success,summary):
        self._running=False
        self.after(0,lambda:(
            self._btn.set_text("⚡  Execute"),
            self._progress.set(1.0 if success else 0.3),
            self._status_lbl.configure(
                text="done" if success else "error",
                fg=SUCCESS if success else ERROR_C),
            self._log.append(f"\n{'✓' if success else '✕'} {summary}"),
        ))

    def set_target(self,s): pass
    def set_btn_text(self,t): self._btn.set_text(t)

class TMPFixCard(FixCard):
    def __init__(self,parent,icon,title,subtitle,btn_label,on_execute,
                 on_scan=None,**kw):
        super().__init__(parent,icon,title,subtitle,btn_label,on_execute,**kw)
        self._on_scan=on_scan

    def _done(self,success,summary):
        self._log_line(f"\n{'✓' if success else '✕'} {summary}")
        self._progress.set(0.5)
        if success and self._on_scan:
            self._log_line("\n  Scanning project for TMP GameObjects...")
            self._on_scan(self._log_line, self._scan_done)
        else:
            self._finish(success, summary)

    def _scan_done(self,success,summary):
        self._finish(success, summary)

    def _finish(self,success,summary):
        self._running=False
        self.after(0,lambda:(
            self._btn.set_text("⚡  Execute"),
            self._progress.set(1.0 if success else 0.3),
            self._status_lbl.configure(
                text="done" if success else "error",
                fg=SUCCESS if success else ERROR_C),
            self._log.append(f"\n{'✓' if success else '✕'} {summary}"),
        ))

class UnityFixesPanel(tk.Frame):
    def __init__(self,parent,toast,**kw):
        super().__init__(parent,bg=CONTENT,**kw)
        self._toast=toast; self._project=None; self._overlay=None

        hdr=tk.Frame(self,bg=CONTENT); hdr.pack(fill="x",padx=dp(28),pady=(dp(24),0))
        tk.Label(hdr,text="Unity Fixes",fg=TEXT,bg=CONTENT,font=(FF_TITLE(),fs(18),"bold")).pack(side="left",anchor="w")
        proj_row=tk.Frame(hdr,bg=CONTENT); proj_row.pack(side="right",anchor="e")
        tk.Label(proj_row,text="Project:",fg=TEXT_DIM,bg=CONTENT,font=(FF_BODY(),fs(8))).pack(side="left")
        self._proj_var=tk.StringVar(value="None selected")
        tk.Label(proj_row,textvariable=self._proj_var,fg=TEXT_MID,bg=CONTENT,font=(FF_BODY(),fs(8))).pack(side="left",padx=(4,10))
        OutlineButton(proj_row,"Change Project",self._pick_project,width=130,height=28,bg=CONTENT).pack(side="left")

        tk.Label(self,text="Apply patches and fixes to your UAR-extracted Unity project",
                 fg=TEXT_DIM,bg=CONTENT,font=(FF_BODY(),fs(9))).pack(anchor="w",padx=dp(28),pady=(4,0))
        tk.Frame(self,bg=BORDER,height=1).pack(fill="x",padx=dp(28),pady=(dp(14),0))

        outer=tk.Frame(self,bg=CONTENT); outer.pack(fill="both",expand=True,padx=dp(28),pady=(dp(14),dp(14)))
        cv=tk.Canvas(outer,bg=CONTENT,highlightthickness=0)
        sb=tk.Scrollbar(outer,orient="vertical",command=cv.yview,bg=BORDER)
        self._scroll_frame=tk.Frame(cv,bg=CONTENT)
        self._scroll_frame.bind("<Configure>",lambda e:cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0,0),window=self._scroll_frame,anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        cv.bind_all("<MouseWheel>",lambda e:cv.yview_scroll(int(-1*(e.delta/120)),"units"))

        self._cards={}
        self._build_cards()

    def _build_cards(self):
        fixes=[
            ("shader",   "◈","TMP Shader Fix",
             "Injects NPA/NPA Text Fix shader, then scans for TMP objects",
             "⚡  Execute", self._exec_shader),
            ("broken_shaders", "◉", "Broken Shader Auto-Fix",
             "Remaps pink/missing shaders in .mat files to matching project or built-in shaders",
             "⚡  Execute", self._exec_broken_shaders),
            ("guid",     "⬡","Script GUID Stability",
             "Deterministic .meta GUIDs from assembly+class name",
             "⚡  Execute", self._exec_guid),
            ("ref_fix",  "⬡","Missing Reference Fixer",
             "Re-links GameObjects with 'No reference found' scripts back to their .cs files",
             "⚡  Execute", self._exec_ref_fix),
        ]
        for i,(key,icon,title,sub,btn,fn) in enumerate(fixes):
            pad_top=0 if i==0 else dp(8)
            if key=="shader":
                card=TMPFixCard(self._scroll_frame,icon,title,sub,btn,fn,
                                on_scan=self._exec_tmp_scan)
            else:
                card=FixCard(self._scroll_frame,icon,title,sub,btn,fn)
            card.pack(fill="x",pady=(pad_top,0))
            self._cards[key]=card

    def _pick_project(self):
        if self._overlay: return
        projects=find_unity_projects()
        def on_pick(p): self._overlay=None; self._set_project(p)
        def on_cancel(): self._overlay=None
        self._overlay=ProjectPicker(self,projects,on_pick,on_cancel)

    def _set_project(self,path:Path):
        self._project=path
        self._proj_var.set(path.name)
        SETTINGS["last_project"]=str(path); save_settings(SETTINGS)
        for card in self._cards.values():
            card.set_target(str(path))

    def _require_project(self):
        if self._project: return True
        projects=find_unity_projects()
        if len(projects)==1: self._set_project(projects[0]); return True
        self._pick_project(); return False

    def _run_fix(self,fn,log_cb,done_cb):
        if not self._require_project(): return
        def worker():
            try:
                result=fn(self._project,log_cb)
                done_cb(True,result)
            except Exception as e:
                done_cb(False,str(e))
        threading.Thread(target=worker,daemon=True).start()

    def _exec_tmp_scan(self,log,done):
        if not self._require_project(): return
        def _w():
            log("  -- Step 1: Applying WASM/Wasmcomfix to TMP materials --")
            patched, mat_errors = apply_wasm_shader_to_tmp_materials(self._project, log)
            log("\n  -- Step 2: Scanning for TMP GameObjects --")
            log("  Detecting: TextMeshPro  TextMeshProUGUI  TMP_Text")
            log("             TMP_InputField  TMP_Dropdown  TMP_FontAsset")
            log("             TMP_SpriteAsset  TMP_SubMesh  TMP_SubMeshUI\n")
            results, scan_errors = scan_tmp_components(self._project, log)
            all_errors = mat_errors + scan_errors
            summary = (f"Patched {patched} material(s)  ·  "
                       f"Found {len(results)} TMP object(s)")
            if all_errors: summary += f"  ·  {len(all_errors)} error(s)"
            done(True, summary)
        threading.Thread(target=_w, daemon=True).start()

    def _exec_broken_shaders(self, log, done):
        if not self._require_project(): return
        def _w():
            log("  Scanning for broken / pink-shader materials...")
            log("  Step 1: Indexing .shader files in project...")
            log("  Step 2: Checking .mat shader GUIDs against project index...")
            log("  Step 3: Remapping broken refs (project match → built-in fallback)...")
            fixed, skipped, errors = fix_broken_shaders(self._project, log)
            summary = f"Fixed {fixed} material(s)  ·  {skipped} already OK"
            if errors: summary += f"  ·  {len(errors)} error(s)"
            if fixed > 0:
                log("\n  Reimport Assets in Unity to apply shader changes.")
            done(fixed > 0 or not errors, summary)
        threading.Thread(target=_w, daemon=True).start()

    def _exec_shader(self,log,done):
        def _w():
            log("  Injecting full TMP-compatible shader...")
            ok,msg=inject_shader(self._project)
            if ok:
                self.after(600,self._show_tutorial)
                done(True,msg)
            else: done(False,msg)
        if not self._require_project(): return
        threading.Thread(target=_w,daemon=True).start()

    def _show_tutorial(self):
        if self._overlay: return
        self._overlay=TutorialOverlay(self,on_close=lambda:setattr(self,"_overlay",None))

    def _make_exec(self,fn,summary_fn):
        def _exec(log,done):
            if not self._require_project(): return
            def _w():
                result=fn(self._project,log)
                done(True,summary_fn(result))
            threading.Thread(target=_w,daemon=True).start()
        return _exec

    def _exec_guid(self,log,done):
        self._make_exec(fix_script_guids,
            lambda r:f"Updated {r[0]} GUIDs, skipped {r[1]}, {len(r[2])} error(s)")(log,done)

    def _exec_ref_fix(self, log, done):
        if not self._require_project(): return
        def _w():
            log("  Scanning scripts and building field index...")
            log("  Looking for MonoBehaviours with missing m_Script references...")
            fixed, skipped, errors = fix_missing_script_refs(self._project, log)
            summary = f"Re-linked {fixed} reference(s)  ·  {skipped} skipped"
            if errors: summary += f"  ·  {len(errors)} error(s)"
            if fixed > 0:
                log("\n  Reimport Scripts in Unity to apply changes.")
            done(fixed > 0 or not errors, summary)
        threading.Thread(target=_w, daemon=True).start()

class SettingsPanel(tk.Frame):
    def __init__(self,parent,rebuild_cb,**kw):
        super().__init__(parent,bg=CONTENT,**kw)
        self._rebuild=rebuild_cb

        hdr=tk.Frame(self,bg=CONTENT); hdr.pack(fill="x",padx=dp(28),pady=(dp(24),0))
        tk.Label(hdr,text="Settings",fg=TEXT,bg=CONTENT,font=(FF_TITLE(),fs(18),"bold")).pack(side="left")
        OutlineButton(hdr,"Reset Defaults",self._reset_defaults,width=120,height=28,bg=CONTENT).pack(side="right")

        tk.Label(self,text="Customize the look, feel and behaviour of Euphoria",
                 fg=TEXT_DIM,bg=CONTENT,font=(FF_BODY(),fs(9))).pack(anchor="w",padx=dp(28),pady=(4,0))
        tk.Frame(self,bg=BORDER,height=1).pack(fill="x",padx=dp(28),pady=(dp(14),0))

        outer=tk.Frame(self,bg=CONTENT); outer.pack(fill="both",expand=True,padx=dp(28),pady=(dp(14),dp(14)))
        cv=tk.Canvas(outer,bg=CONTENT,highlightthickness=0)
        sb=tk.Scrollbar(outer,orient="vertical",command=cv.yview,bg=BORDER)
        self._sf=tk.Frame(cv,bg=CONTENT)
        self._sf.bind("<Configure>",lambda e:cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0,0),window=self._sf,anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        cv.bind_all("<MouseWheel>",lambda e:cv.yview_scroll(int(-1*(e.delta/120)),"units"))

        self._build_appearance()
        self._build_behaviour()
        self._build_project()

    def _section(self,label):
        f=tk.Frame(self._sf,bg=CONTENT); f.pack(fill="x",pady=(dp(20),dp(10)))
        tk.Canvas(f,width=3,height=14,bg=ACCENT,highlightthickness=0).pack(side="left",anchor="center")
        tk.Label(f,text=label,fg=ACCENT,bg=CONTENT,font=(FF_BODY(),fs(8),"bold"),padx=6).pack(side="left")
        return f

    def _card(self):
        c=tk.Frame(self._sf,bg=CARD,highlightthickness=1,highlightbackground=BORDER)
        c.pack(fill="x",pady=(0,dp(8)))
        return c

    def _row(self,card,label,hint=""):
        r=tk.Frame(card,bg=CARD); r.pack(fill="x",padx=dp(20),pady=(dp(10),dp(10)))
        lf=tk.Frame(r,bg=CARD); lf.pack(side="left",fill="y",anchor="w")
        tk.Label(lf,text=label,fg=TEXT,bg=CARD,font=(FF_BODY(),fs(9)),anchor="w").pack(anchor="w")
        if hint: tk.Label(lf,text=hint,fg=TEXT_DIM,bg=CARD,font=(FF_BODY(),fs(8)),anchor="w").pack(anchor="w")
        ctrl=tk.Frame(r,bg=CARD); ctrl.pack(side="right",anchor="e")
        return ctrl

    def _divider(self,card):
        tk.Frame(card,bg=BORDER,height=1).pack(fill="x",padx=dp(20))

    def _build_appearance(self):
        self._section("APPEARANCE")

        tc=self._card()
        tk.Label(tc,text="Color Theme",fg=TEXT,bg=CARD,font=(FF_BODY(),fs(9),"bold"),
                 padx=dp(20),pady=dp(10)).pack(anchor="w")
        sw=tk.Frame(tc,bg=CARD); sw.pack(fill="x",padx=dp(20),pady=(0,dp(14)))
        for name,colors in THEME_DEFS.items():
            col=tk.Frame(sw,bg=CARD,cursor="hand2")
            col.pack(side="left",padx=(0,dp(10)))
            swatch=tk.Canvas(col,width=52,height=36,highlightthickness=2,
                             highlightbackground=ACCENT if name==SETTINGS.get("theme") else BORDER)
            swatch.pack()
            swatch.create_rectangle(0,0,52,36,fill=colors["ACCENT"],outline="")
            def _pick_theme(n=name,s=swatch):
                apply_theme(n); self._rebuild()
            swatch.bind("<Button-1>",lambda _,fn=_pick_theme:fn())
            col.bind("<Button-1>",lambda _,fn=_pick_theme:fn())
            tk.Label(col,text=name,fg=TEXT_DIM,bg=CARD,font=(FF_BODY(),fs(7))).pack()

        self._divider(tc)

        ac=self._row(tc,"Accent Color","Override the theme's accent color")
        self._accent_preview=tk.Canvas(ac,width=48,height=28,highlightthickness=1,
                                       highlightbackground=BORDER,cursor="hand2")
        c=SETTINGS.get("accent_color","") or ACCENT
        self._accent_preview.create_rectangle(0,0,48,28,fill=c,outline="")
        self._accent_preview.pack(side="left",padx=(0,6))
        self._accent_preview.bind("<Button-1>",lambda _:self._pick_accent())
        self._accent_preview.bind("<Enter>",lambda _:self._accent_preview.configure(highlightbackground=TEXT_MID))
        self._accent_preview.bind("<Leave>",lambda _:self._accent_preview.configure(highlightbackground=BORDER))
        OutlineButton(ac,"Reset",self._reset_accent,width=60,height=28,bg=CARD).pack(side="left",padx=(4,0))

        self._divider(tc)

        fs_ctrl=self._row(tc,"Font Size",f"Currently: {SETTINGS.get('font_size',9)}pt")
        self._fs_lbl=fs_ctrl.winfo_children()[-1] if fs_ctrl.winfo_children() else None
        self._fs_slider=SliderWidget(fs_ctrl,8,16,SETTINGS.get("font_size",9),
                                     on_change=self._on_font_size,width=180,label_fmt="{:.0f}pt",bg=CARD)
        self._fs_slider.pack()

        self._divider(tc)

        dn=self._row(tc,"UI Density","Controls spacing and padding throughout the app")
        for opt in ("Compact","Normal","Comfortable"):
            sel=SETTINGS.get("ui_density","Normal")==opt
            btn=tk.Frame(dn,bg=ACCENT if sel else BORDER,cursor="hand2",
                         highlightthickness=1,
                         highlightbackground=ACCENT if sel else BORDER)
            btn.pack(side="left",padx=(0,4))
            lbl=tk.Label(btn,text=opt,fg=TEXT if sel else TEXT_DIM,bg=ACCENT if sel else BORDER,
                         font=(FF_BODY(),fs(8)),padx=8,pady=4)
            lbl.pack()
            def _set_density(o=opt,b=btn,l=lbl):
                SETTINGS["ui_density"]=o; save_settings(SETTINGS); self._rebuild()
            btn.bind("<Button-1>",lambda _,fn=_set_density:fn())
            lbl.bind("<Button-1>",lambda _,fn=_set_density:fn())

        self._divider(tc)

        cs=self._row(tc,"Card Style","Visual style of fix cards")
        for opt in ("Default","Minimal","Outlined"):
            sel=SETTINGS.get("card_style","Default")==opt
            btn=tk.Frame(cs,bg=ACCENT if sel else BORDER,cursor="hand2",
                         highlightthickness=1,highlightbackground=ACCENT if sel else BORDER)
            btn.pack(side="left",padx=(0,4))
            lbl=tk.Label(btn,text=opt,fg=TEXT if sel else TEXT_DIM,bg=ACCENT if sel else BORDER,
                         font=(FF_BODY(),fs(8)),padx=8,pady=4)
            lbl.pack()
            def _set_style(o=opt):
                SETTINGS["card_style"]=o; save_settings(SETTINGS); self._rebuild()
            btn.bind("<Button-1>",lambda _,fn=_set_style:fn())
            lbl.bind("<Button-1>",lambda _,fn=_set_style:fn())

        self._divider(tc)

        font_card=self._card()
        tk.Label(font_card,text="Custom Fonts",fg=TEXT,bg=CARD,font=(FF_BODY(),fs(9),"bold"),
                 padx=dp(20),pady=dp(10)).pack(anchor="w")
        cf=SETTINGS.get("custom_fonts",{})
        for key,label,default in [
            ("title","Title Font","Trebuchet MS"),
            ("body","Body Font","Segoe UI"),
            ("mono","Mono Font","Consolas"),
        ]:
            row=tk.Frame(font_card,bg=CARD); row.pack(fill="x",padx=dp(20),pady=(0,dp(8)))
            tk.Label(row,text=f"{label}:",fg=TEXT_MID,bg=CARD,
                     font=(FF_BODY(),fs(8)),width=12,anchor="w").pack(side="left")
            var=tk.StringVar(value=cf.get(key,""))
            entry=tk.Entry(row,textvariable=var,bg="#0b1020",fg=TEXT,
                           insertbackground=ACCENT,relief="flat",bd=0,
                           highlightthickness=1,highlightbackground=BORDER,
                           font=(FF_MONO(),fs(8)),width=22)
            entry.pack(side="left",padx=(0,6),ipady=4,ipadx=6)
            ph=tk.Label(row,text=f"default: {default}",fg=TEXT_DIM,bg=CARD,font=(FF_BODY(),fs(7)))
            ph.pack(side="left")
            def _save_font(v,k=key):
                SETTINGS.setdefault("custom_fonts",{})[k]=v; save_settings(SETTINGS)
            var.trace_add("write",lambda *a,v=var,k=key:_save_font(v.get(),k))
        tk.Label(font_card,text="Restart / rebuild after changing fonts",
                 fg=TEXT_DIM,bg=CARD,font=(FF_BODY(),fs(7)),padx=dp(20)).pack(anchor="w",pady=(0,dp(10)))
        OutlineButton(font_card,"Apply Fonts & Rebuild",self._rebuild,width=180,height=28,bg=CARD).pack(anchor="w",padx=dp(20),pady=(0,dp(12)))

    def _pick_accent(self):
        current=SETTINGS.get("accent_color","") or ACCENT
        col=colorchooser.askcolor(color=current,title="Pick Accent Color")
        if col and col[1]:
            hex_c=col[1]
            self._accent_preview.delete("all")
            self._accent_preview.create_rectangle(0,0,28,28,fill=hex_c,outline="")
            apply_theme(accent_override=hex_c)
            self._rebuild()

    def _reset_accent(self):
        SETTINGS["accent_color"]=""
        apply_theme()
        self._rebuild()

    def _on_font_size(self,v):
        SETTINGS["font_size"]=int(v); save_settings(SETTINGS)

    def _build_behaviour(self):
        self._section("BEHAVIOUR")
        bc=self._card()

        ar=self._row(bc,"Animations","Enable toast slide + fade animations")
        at=ToggleSwitch(ar,SETTINGS.get("animations",True),bg=CARD,
                        on_change=lambda v:(SETTINGS.update({"animations":v}),save_settings(SETTINGS)))
        at.pack()

        self._divider(bc)

        td_row=self._row(bc,"Toast Duration","How long notifications stay visible")
        self._td_slider=SliderWidget(td_row,1000,8000,
                                     SETTINGS.get("toast_duration",3500),
                                     on_change=lambda v:(SETTINGS.update({"toast_duration":int(v)}),save_settings(SETTINGS)),
                                     width=200,label_fmt="{:.0f}ms",bg=CARD)
        self._td_slider.pack()

        self._divider(bc)

        tp=self._row(bc,"Toast Position","Where notifications appear")
        for pos in ("Bottom Right","Bottom Left","Top Right","Top Left"):
            sel=SETTINGS.get("toast_pos","Bottom Right")==pos
            b=tk.Frame(tp,bg=ACCENT if sel else BORDER,cursor="hand2",
                       highlightthickness=1,highlightbackground=ACCENT if sel else BORDER)
            b.pack(side="left",padx=(0,4))
            l=tk.Label(b,text=pos,fg=TEXT if sel else TEXT_DIM,bg=ACCENT if sel else BORDER,
                       font=(FF_BODY(),fs(7)),padx=6,pady=3); l.pack()
            def _sp(p=pos):
                SETTINGS["toast_pos"]=p; save_settings(SETTINGS); self._rebuild()
            b.bind("<Button-1>",lambda _,fn=_sp:fn())
            l.bind("<Button-1>",lambda _,fn=_sp:fn())

        self._divider(bc)

        cc_row=self._row(bc,"Compact Cards","Reduce padding inside fix cards")
        ct=ToggleSwitch(cc_row,SETTINGS.get("compact_cards",False),bg=CARD,
                        on_change=lambda v:(SETTINGS.update({"compact_cards":v}),save_settings(SETTINGS),self._rebuild()))
        ct.pack()

        self._divider(bc)

        tt_row=self._row(bc,"Tooltips","Show helpful tooltips on hover")
        tt=ToggleSwitch(tt_row,SETTINGS.get("show_tooltips",True),bg=CARD,
                        on_change=lambda v:(SETTINGS.update({"show_tooltips":v}),save_settings(SETTINGS)))
        tt.pack()

    def _build_project(self):
        self._section("PROJECT DETECTION")
        pc=self._card()

        auto=self._row(pc,"Auto-Detect Projects","Scan for Unity projects on startup")
        at=ToggleSwitch(auto,SETTINGS.get("auto_scan",True),bg=CARD,
                        on_change=lambda v:(SETTINGS.update({"auto_scan":v}),save_settings(SETTINGS)))
        at.pack()

        self._divider(pc)

        sd=self._row(pc,"Scan Depth","How many folder levels deep to search")
        self._sd_slider=SliderWidget(pc,1,5,SETTINGS.get("scan_depth",2),
                                     on_change=lambda v:(SETTINGS.update({"scan_depth":int(v)}),save_settings(SETTINGS)),
                                     width=300,label_fmt="{:.0f} levels",bg=CARD)
        self._sd_slider.pack(fill="x",padx=dp(20),pady=(0,dp(10)))

        self._divider(pc)

        lp_row=self._row(pc,"Last Project","Remembered project path")
        lp=SETTINGS.get("last_project","") or "None"
        tk.Label(lp_row,text=lp[-50:] if len(lp)>50 else lp,
                 fg=TEXT_DIM,bg=CARD,font=(FF_MONO(),fs(7))).pack(side="left",padx=(0,8))
        OutlineButton(lp_row,"Clear",lambda:(SETTINGS.update({"last_project":""}),save_settings(SETTINGS),self._rebuild()),
                      width=60,height=24,bg=CARD).pack(side="left")

    def _reset_defaults(self):
        SETTINGS.clear(); SETTINGS.update(DEFAULT_SETTINGS)
        apply_theme(); save_settings(SETTINGS)
        self._rebuild()

class AboutPanel(tk.Frame):
    def __init__(self,parent,**kw):
        super().__init__(parent,bg=CONTENT,**kw)

        hdr=tk.Frame(self,bg=CONTENT); hdr.pack(fill="x",padx=dp(28),pady=(dp(24),0))
        tk.Label(hdr,text="About",fg=TEXT,bg=CONTENT,font=(FF_TITLE(),fs(18),"bold")).pack(side="left")
        tk.Frame(self,bg=BORDER,height=1).pack(fill="x",padx=dp(28),pady=(dp(14),0))

        desc_card=tk.Frame(self,bg=CARD,highlightthickness=1,highlightbackground=BORDER_LT)
        desc_card.pack(fill="x",padx=dp(28),pady=(dp(18),0))
        inner=tk.Frame(desc_card,bg=CARD); inner.pack(fill="x",padx=dp(22),pady=dp(18))

        ic_row=tk.Frame(inner,bg=CARD); ic_row.pack(anchor="w",pady=(0,dp(14)))
        ic=tk.Canvas(ic_row,width=42,height=42,bg=CARD,highlightthickness=0); ic.pack(side="left")
        RoundRect.draw(ic,0,0,42,42,r=8,fill=ACCENT_GL,outline="")
        ic.create_text(21,21,text="◉",fill=ACCENT,font=(FF_BODY(),fs(16)))
        tl=tk.Frame(ic_row,bg=CARD); tl.pack(side="left",padx=(12,0))
        tk.Label(tl,text="Euphoria",fg=TEXT,bg=CARD,font=(FF_TITLE(),fs(13),"bold")).pack(anchor="w")
        tk.Label(tl,text="UAR Gap Filler  ·  v2.0",fg=TEXT_MID,bg=CARD,font=(FF_BODY(),fs(8))).pack(anchor="w")

        tk.Frame(inner,bg=BORDER,height=1).pack(fill="x",pady=(0,dp(14)))

        tk.Label(inner,
                 text=("Hello, this is a project @dudeluther1232 and @shxyder are working on!! "
                       "This is a attempt to fulfill the gaps that UAR (UnityAssetRipper) couldn't. "
                       "Have fun"),
                 fg=TEXT,bg=CARD,font=(FF_BODY(),fs(10)),wraplength=640,
                 justify="left",anchor="w").pack(anchor="w")

        tk.Frame(inner,bg=BORDER,height=1).pack(fill="x",pady=(dp(16),dp(12)))
        cr=tk.Frame(inner,bg=CARD); cr.pack(anchor="w")
        tk.Label(cr,text="Contributors:",fg=TEXT_DIM,bg=CARD,font=(FF_BODY(),fs(8))).pack(side="left")
        for h in ("@dudeluther1232","@shxyder"):
            tk.Label(cr,text=h,fg=ACCENT,bg=ACCENT_GL,font=(FF_BODY(),fs(8)),padx=7,pady=2).pack(side="left",padx=(6,0))

        sl=tk.Frame(self,bg=CONTENT); sl.pack(fill="x",padx=dp(28),pady=(dp(22),dp(10)))
        tk.Label(sl,text="FIX ROADMAP",fg=ACCENT,bg=CONTENT,font=(FF_BODY(),fs(8),"bold")).pack(side="left")

        outer=tk.Frame(self,bg=CONTENT); outer.pack(fill="both",expand=True,padx=dp(28),pady=(0,dp(18)))
        cv=tk.Canvas(outer,bg=CONTENT,highlightthickness=0)
        sb=tk.Scrollbar(outer,orient="vertical",command=cv.yview,bg=BORDER)
        sf=tk.Frame(cv,bg=CONTENT)
        sf.bind("<Configure>",lambda e:cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0,0),window=sf,anchor="nw"); cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        cv.bind_all("<MouseWheel>",lambda e:cv.yview_scroll(int(-1*(e.delta/120)),"units"))

        roadmap=[
            ("NPA Text Fix Shader","TextMeshPro · Shader · SDF","ACTIVE",SUCCESS,
             "Replaces the old WASM/Wasmcomfix shader with the clean NPA/NPA Text Fix SDF shader. "
             "Injects NPA_Text_Fix.shader into Assets/Shaders/NPA/ and patches all TMP materials "
             "to reference it. Fixes red boxes and TMP material crashes with a much simpler, "
             "production-quality SDF implementation."),
            ("Broken Shader Auto-Fix","Shader · Material · Pink · Missing","ACTIVE",SUCCESS,
             "Scans all .mat files in Assets for broken shader references (pink/magenta objects). "
             "Indexes every .shader file in the project and remaps materials by property-signature "
             "matching. Falls back to built-in Standard if no project shader matches. Run this then "
             "reimport Assets in Unity — no more pink meshes from UAR exports."),
            ("Script GUID Stability","GUID · MonoScript · Prefab · Meta","ACTIVE",SUCCESS,
             "Derives script asset GUIDs deterministically from MD5(namespace+classname), matching Unity's "
             "own algorithm. All m_Script references in Prefabs/Scenes resolve across re-exports."),
            ("Missing Reference Fixer","GameObject · MonoBehaviour · Script · GUID","ACTIVE",SUCCESS,
             "Scans all .unity / .prefab / .asset files for MonoBehaviour components with a missing or "
             "all-zero m_Script GUID (the dreaded 'No reference found'). Builds a full field index of "
             "every .cs script in the project and scores each broken block against every script by "
             "serialised-field overlap and class-name hints. Best match is automatically re-linked. "
             "Run after Script GUID Stability for best results."),
        ]

        for i,(title,tags_str,status,sc,desc) in enumerate(roadmap):
            c=tk.Frame(sf,bg=CARD,highlightthickness=1,highlightbackground=BORDER)
            c.pack(fill="x",pady=(0,dp(8)))
            top=tk.Frame(c,bg=CARD); top.pack(fill="x",padx=dp(18),pady=(dp(12),0))
            nb=tk.Canvas(top,width=26,height=26,bg=CARD,highlightthickness=0); nb.pack(side="left",anchor="n",pady=2)
            RoundRect.draw(nb,1,1,25,25,r=6,fill=ACCENT_DK,outline="")
            nb.create_text(13,13,text=str(i+1),fill=TEXT,font=(FF_BODY(),fs(8),"bold"))
            tf=tk.Frame(top,bg=CARD); tf.pack(side="left",fill="x",expand=True,padx=(10,0))
            tr=tk.Frame(tf,bg=CARD); tr.pack(fill="x",anchor="w")
            tk.Label(tr,text=title,fg=TEXT,bg=CARD,font=(FF_TITLE(),fs(10),"bold"),anchor="w").pack(side="left")
            tk.Label(tr,text=status,fg=sc,bg=CARD,font=(FF_BODY(),fs(7),"bold"),padx=6,pady=1).pack(side="left",padx=(8,0))
            tk.Label(tf,text=tags_str,fg=TEXT_DIM,bg=CARD,font=(FF_BODY(),fs(7)),anchor="w").pack(anchor="w",pady=(1,0))
            tk.Frame(c,bg=BORDER,height=1).pack(fill="x",padx=dp(18),pady=(dp(8),0))
            tk.Label(c,text=desc,fg=TEXT_MID,bg=CARD,font=(FF_BODY(),fs(8)),
                     wraplength=660,justify="left",anchor="w").pack(fill="x",padx=dp(18),pady=(dp(8),dp(12)))

NAV_ITEMS=[
    ("unity_fixes","⬡","Unity Fixes"),
    ("settings",   "⚙","Settings"),
    ("about",      "◉","About"),
]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Euphoria")
        self.configure(bg=BG)
        self.geometry("980x660")
        self.minsize(820,540)
        self.resizable(True,True)
        if IS_WIN:
            try: self.attributes("-transparentcolor","")
            except Exception: pass
        self._toast=Toast(self)
        self._panels={}
        self._outer=None
        self._active_key="unity_fixes"
        self._build()
        self.update_idletasks()
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        w,h=self.winfo_width(),self.winfo_height()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
        if SETTINGS.get("auto_scan",True) and SETTINGS.get("last_project",""):
            lp=Path(SETTINGS["last_project"])
            if lp.exists() and (lp/"Assets").exists():
                panel=self._panels.get("unity_fixes")
                if panel: panel._set_project(lp)

    def _build(self):
        if self._outer:
            try: self._outer.destroy()
            except Exception: pass
        self._panels={}
        self.configure(bg=BORDER)
        self._outer=tk.Frame(self,bg=BG)
        self._outer.pack(fill="both",expand=True,padx=1,pady=1)

        self._sidebar=Sidebar(self._outer,NAV_ITEMS,self._switch_panel)
        self._sidebar.pack(side="left",fill="y")
        tk.Frame(self._outer,bg=BORDER,width=1).pack(side="left",fill="y")

        cw=tk.Frame(self._outer,bg=CONTENT)
        cw.pack(side="left",fill="both",expand=True)

        fixes=UnityFixesPanel(cw,self._toast)
        settings=SettingsPanel(cw,rebuild_cb=self.rebuild)
        about=AboutPanel(cw)

        self._panels={"unity_fixes":fixes,"settings":settings,"about":about}
        self._panels[self._active_key].pack(fill="both",expand=True)

    def rebuild(self):
        key=self._active_key
        self._build()
        self._active_key=key
        for k,p in self._panels.items():
            if k==key: p.pack(fill="both",expand=True)
            else: p.pack_forget()
        self._sidebar.set_active(key)

    def _switch_panel(self,key):
        if key==self._active_key: return
        self._panels[self._active_key].pack_forget()
        self._active_key=key
        self._panels[key].pack(fill="both",expand=True)

if __name__=="__main__":
    App().mainloop()
