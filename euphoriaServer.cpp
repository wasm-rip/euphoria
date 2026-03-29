/*
 * euphoriaServer.cpp
 * Native C++ to build to a dll that hosts Euphoria on http://localhost:8000
 * Requires: Windows, MSVC or MinGW, links against httpapi.lib ws2_32.lib
 *
 * Build (MSVC):
 *   cl /LD /EHsc /std:c++17 euphoriaServer.cpp /link /OUT:euphoriaServer.dll
 *
 * Build (MinGW):
 *   g++ -shared -O2 -o euphoriaServer.dll euphoriaServer.cpp -lhttpapi -lws2_32 -static-libgcc -static-libstdc++
 *
 * Usage from Python:
 *   import ctypes, subprocess
 *   dll = ctypes.WinDLL("euphoriaServer.dll")
 *   dll.EuphoriaStart()
 *   input("press enter to stop")
 *   dll.EuphoriaStop()
 */

#define WIN32_LEAN_AND_MEAN
#define UNICODE
#include <windows.h>
#include <http.h>
#include <shlwapi.h>
#include <string>
#include <vector>
#include <map>
#include <sstream>
#include <fstream>
#include <thread>
#include <atomic>
#include <mutex>
#include <functional>
#include <algorithm>
#include <regex>
#include <filesystem>

#include <shlobj.h>
#include <shellapi.h>
#include <wincrypt.h>
#include <set>

#pragma comment(lib, "httpapi.lib")
#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "Ole32.lib")
#pragma comment(lib, "Shell32.lib")
#pragma comment(lib, "Crypt32.lib")
#pragma comment(lib, "advapi32.lib")

namespace fs = std::filesystem;

static HANDLE           g_hReqQueue  = nullptr;
static std::thread      g_serverThread;
static std::atomic<bool> g_running   { false };
static std::mutex       g_logMutex;

// per-operation log buffer (op_id -> lines)
static std::map<std::string, std::vector<std::string>> g_logs;
static std::map<std::string, std::string>               g_results;   // op_id -> json result
static std::mutex g_opMutex;

//json
static std::string JsonStr(const std::string& s) {
    std::string out = "\"";
    for (char c : s) {
        if      (c == '"')  out += "\\\"";
        else if (c == '\\') out += "\\\\";
        else if (c == '\n') out += "\\n";
        else if (c == '\r') out += "";
        else if (c == '\t') out += "\\t";
        else                out += c;
    }
    out += "\"";
    return out;
}

static std::string JsonArr(const std::vector<std::string>& v) {
    std::string out = "[";
    for (size_t i = 0; i < v.size(); i++) {
        if (i) out += ",";
        out += JsonStr(v[i]);
    }
    out += "]";
    return out;
}

static std::string MakeOpId() {
    static std::atomic<uint64_t> counter { 0 };
    SYSTEMTIME st; GetSystemTime(&st);
    char buf[64];
    snprintf(buf, sizeof(buf), "%04d%02d%02d%02d%02d%02d%04llu",
             st.wYear, st.wMonth, st.wDay,
             st.wHour, st.wMinute, st.wSecond,
             (unsigned long long)counter.fetch_add(1));
    return std::string(buf);
}

//regex
static std::string RegexReplace(const std::string& src,
                                 const std::string& pattern,
                                 const std::string& replacement,
                                 int maxCount = 0) {
    std::regex re(pattern);
    if (maxCount == 1) {
        return std::regex_replace(src, re, replacement,
                                  std::regex_constants::format_first_only);
    }
    return std::regex_replace(src, re, replacement);
}

static bool RegexContains(const std::string& src, const std::string& pattern) {
    std::regex re(pattern);
    return std::regex_search(src, re);
}

static std::string RegexCapture(const std::string& src,
                                 const std::string& pattern,
                                 size_t group = 1) {
    std::regex re(pattern);
    std::smatch m;
    if (std::regex_search(src, m, re) && m.size() > group)
        return m[group].str();
    return "";
}

//file utils
static std::string ReadFile(const fs::path& p) {
    std::ifstream f(p, std::ios::binary);
    if (!f) return "";
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

static bool WriteFile(const fs::path& p, const std::string& content) {
    std::ofstream f(p, std::ios::binary | std::ios::trunc);
    if (!f) return false;
    f << content;
    return f.good();
}

static std::string ToLower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    return s;
}

//unity proj finder
static std::vector<fs::path> FindUnityProjects(int depth = 2) {
    std::vector<fs::path> candidates;
    wchar_t homeW[MAX_PATH];
    SHGetFolderPathW(nullptr, CSIDL_PROFILE, nullptr, 0, homeW);
    fs::path home(homeW);

    std::vector<fs::path> roots = {
        home / "Documents" / "Unity",
        home / "Unity",
        home / "Desktop",
        home / "dev",
        home / "projects",
        home / "Projects",
        "C:/Users"
    };

    std::function<void(const fs::path&, int)> scan = [&](const fs::path& root, int d) {
        if (d < 0 || !fs::exists(root)) return;
        try {
            for (auto& entry : fs::directory_iterator(root)) {
                if (!entry.is_directory()) continue;
                if (fs::exists(entry.path() / "Assets"))
                    candidates.push_back(entry.path());
                else if (d > 0)
                    scan(entry.path(), d - 1);
            }
        } catch (...) {}
    };

    for (auto& r : roots) scan(r, depth);

    std::vector<fs::path> out;
    std::set<fs::path> seen;
    for (auto& p : candidates) {
        if (!seen.count(p)) { seen.insert(p); out.push_back(p); }
        if (out.size() >= 25) break;
    }
    return out;
}

//shaders
static const char* SHADER_CONTENT =
"Shader \"WASMCOM/WASMCOMFIX\"\n"
"{\n"
"    Properties\n"
"    {\n"
"        _MainTex(\"Font Atlas (SDF)\", 2D) = \"white\" {}\n"
"        _FaceColor(\"Face Color\", Color) = (1,1,1,1)\n"
"        _OutlineColor(\"Outline Color\", Color) = (0,0,0,1)\n"
"        _OutlineWidth(\"Outline Thickness\", Range(0,1)) = 0\n"
"        _OutlineSoftness(\"Outline Softness\", Range(0,1)) = 0\n"
"        _GradientScale(\"Gradient Scale\", float) = 5.0\n"
"        _Sharpness(\"Sharpness\", Range(-1,1)) = 1\n"
"        _Weight(\"Text Weight\", Range(-0.5,0.5)) = 0.5\n"
"    }\n"
"    SubShader\n"
"    {\n"
"        Tags { \"Queue\"=\"Transparent\" \"IgnoreProjector\"=\"True\" \"RenderType\"=\"Transparent\" }\n"
"        ZWrite Off Lighting Off Cull Off\n"
"        Blend One OneMinusSrcAlpha\n"
"        Pass\n"
"        {\n"
"            CGPROGRAM\n"
"            #pragma vertex vert\n"
"            #pragma fragment frag\n"
"            #include \"UnityCG.cginc\"\n"
"            sampler2D _MainTex; float4 _MainTex_ST;\n"
"            float4 _FaceColor, _OutlineColor;\n"
"            float _OutlineWidth, _OutlineSoftness, _GradientScale, _Sharpness, _Weight;\n"
"            struct a { float4 v:POSITION; float2 u:TEXCOORD0; float4 c:COLOR; };\n"
"            struct v { float4 p:SV_POSITION; float2 u:TEXCOORD0; float4 c:COLOR; };\n"
"            v vert(a i) { v o; o.p=UnityObjectToClipPos(i.v); o.u=TRANSFORM_TEX(i.u,_MainTex); o.c=i.c; return o; }\n"
"            fixed4 frag(v i):SV_Target {\n"
"                float s=tex2D(_MainTex,i.u).a, sc=_GradientScale*(_Sharpness+1);\n"
"                float d=(s*sc-0.5)-(_Weight*sc), aa=fwidth(d);\n"
"                float ol=_OutlineWidth*sc, sf=max(_OutlineSoftness*sc+1e-4,aa);\n"
"                float al=smoothstep(-sf,sf,d), oa=smoothstep(-sf-ol,sf-ol,d);\n"
"                fixed4 c=lerp(_OutlineColor,_FaceColor,al); c.a=max(al,oa); return c*i.c;\n"
"            }\n"
"            ENDCG\n"
"        }\n"
"    }\n"
"}"
; // end SHADER_CONTENT

//inject shader
static void FixInjectShader(const fs::path& proj,
                             const std::string& opId,
                             std::function<void(const std::string&)> log) {
    fs::path shaderDir  = proj / "Assets" / "Shaders" / "WASMCOM";
    fs::path shaderFile = shaderDir / "Wasmcomfix.shader";
    fs::path metaFile   = shaderFile;
    metaFile += ".meta";

    std::error_code ec;
    fs::create_directories(shaderDir, ec);

    WriteFile(shaderFile, SHADER_CONTENT);
    log("  Injected " + shaderFile.string());

    if (!fs::exists(metaFile)) {
        GUID g; CoCreateGuid(&g);
        char guidStr[40];
        snprintf(guidStr, sizeof(guidStr),
                 "%08lx%04x%04x%02x%02x%02x%02x%02x%02x%02x%02x",
                 g.Data1, g.Data2, g.Data3,
                 g.Data4[0], g.Data4[1], g.Data4[2], g.Data4[3],
                 g.Data4[4], g.Data4[5], g.Data4[6], g.Data4[7]);
        std::string metaContent =
            std::string("fileFormatVersion: 2\nguid: ") + guidStr +
            "\nShaderImporter:\n  externalObjects: {}\n  defaultTextures: []\n"
            "  nonModifiableTextures: []\n  preprocessorOverride: 0\n"
            "  userData: \n  assetBundleName: \n  assetBundleVariant: \n";
        WriteFile(metaFile, metaContent);
        log("  Created .meta: " + std::string(guidStr));
    }

    //patch tmps
    std::string shaderGuid = RegexCapture(ReadFile(metaFile), R"(guid:\s*([0-9a-f]{32}))");
    if (shaderGuid.empty()) {
        log("  ERROR: could not read shader GUID from .meta");
        return;
    }

    static const char* TMP_MARKERS[] = {
        "_FaceColor","_GradientScale","_FaceDilate","_WeightNormal","_OutlineColor", nullptr
    };

    int patched = 0;
    for (auto& entry : fs::recursive_directory_iterator(proj / "Assets")) {
        if (entry.path().extension() != ".mat") continue;
        std::string src = ReadFile(entry.path());
        bool hasTmp = false;
        for (int i = 0; TMP_MARKERS[i]; i++)
            if (src.find(TMP_MARKERS[i]) != std::string::npos) { hasTmp = true; break; }
        if (!hasTmp) continue;

        std::string txt = src;
        std::string newShader = "m_Shader: {fileID: 4800000, guid: " + shaderGuid + ", type: 3}";
        txt = RegexReplace(txt, R"(m_Shader:\s*\{[^}]*\})", newShader, 1);

        if (txt != src) {
            WriteFile(entry.path(), txt);
            patched++;
            log("  Patched: " + entry.path().filename().string());
        }
    }
    log("  Patched " + std::to_string(patched) + " TMP material(s)");
}

//fix broken shaders
static void FixBrokenShaders(const fs::path& proj,
                              const std::string& opId,
                              std::function<void(const std::string&)> log) {
    std::map<std::string, fs::path> guidToShader;
    std::map<std::string, std::string> nameToGuid;

    for (auto& entry : fs::recursive_directory_iterator(proj / "Assets")) {
        if (entry.path().extension() != ".shader") continue;
        fs::path meta = entry.path(); meta += ".meta";
        if (!fs::exists(meta)) continue;
        std::string g = RegexCapture(ReadFile(meta), R"(guid:\s*([0-9a-f]{32}))");
        if (g.empty()) continue;
        guidToShader[g] = entry.path();
        std::string firstLine = ReadFile(entry.path()).substr(0, 200);
        std::string name = RegexCapture(firstLine, "Shader\\s+\"([^\"]+)\"");
        if (!name.empty()) nameToGuid[ToLower(name)] = g;
    }
    log("  Indexed " + std::to_string(guidToShader.size()) + " shader(s)");

    int fixed = 0, skipped = 0;
    for (auto& entry : fs::recursive_directory_iterator(proj / "Assets")) {
        if (entry.path().extension() != ".mat") continue;
        std::string src = ReadFile(entry.path());
        std::string curGuid = RegexCapture(src,
            R"(m_Shader:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-f]{32}))");
        if (curGuid.empty() || guidToShader.count(curGuid)) { skipped++; continue; }
        if (curGuid == "0000000000000000f000000000000000") { skipped++; continue; }

        std::string newFileId = "46", newGuid = "0000000000000000f000000000000000", newType = "0";
        std::string matName = ToLower(RegexCapture(src, R"(m_Name:\s*(.+))"));

        bool found = false;
        for (auto& [sname, sg] : nameToGuid) {
            if (matName.find(sname) != std::string::npos || sname.find(matName) != std::string::npos) {
                newFileId = "4800000"; newGuid = sg; newType = "3"; found = true;
                log("  Matched: " + entry.path().filename().string() + " -> " + sname);
                break;
            }
        }
        if (!found) {
            log("  Fallback Standard: " + entry.path().filename().string());
        }

        std::string patched = RegexReplace(src,
            R"(m_Shader:\s*\{fileID:\s*\d+,\s*guid:\s*[0-9a-f]{32},\s*type:\s*\d+\})",
            "m_Shader: {fileID: " + newFileId + ", guid: " + newGuid + ", type: " + newType + "}",
            1);
        WriteFile(entry.path(), patched);
        fixed++;
    }
    log("  Fixed " + std::to_string(fixed) + " material(s), skipped " + std::to_string(skipped));
}

//fix guid stability
static std::string MD5Hex(const std::string& input) {
    // use windows cryptoapi
    HCRYPTPROV hProv = 0; HCRYPTHASH hHash = 0;
    std::string result(32, '0');
    if (!CryptAcquireContextA(&hProv, nullptr, nullptr, PROV_RSA_FULL, CRYPT_VERIFYCONTEXT))
        return result;
    if (!CryptCreateHash(hProv, CALG_MD5, 0, 0, &hHash)) {
        CryptReleaseContext(hProv, 0); return result;
    }
    CryptHashData(hHash, (BYTE*)input.data(), (DWORD)input.size(), 0);
    BYTE hash[16]; DWORD len = 16;
    CryptGetHashParam(hHash, HP_HASHVAL, hash, &len, 0);
    char buf[33];
    for (int i = 0; i < 16; i++) snprintf(buf + i*2, 3, "%02x", hash[i]);
    result = buf;
    CryptDestroyHash(hHash); CryptReleaseContext(hProv, 0);
    return result;
}

static void FixScriptGuids(const fs::path& proj,
                            const std::string& opId,
                            std::function<void(const std::string&)> log) {
    int fixed = 0, skipped = 0;
    for (auto& entry : fs::recursive_directory_iterator(proj / "Assets")) {
        if (entry.path().extension() != ".cs") continue;
        std::string src = ReadFile(entry.path());
        std::string ns  = RegexCapture(src, R"(namespace\s+([\w.]+))");
        std::string cl  = RegexCapture(src, R"((?:class|struct|interface)\s+(\w+))");
        if (cl.empty()) cl = entry.path().stem().string();
        std::string key  = ns.empty() ? cl : ns + "." + cl;
        std::string guid = MD5Hex(key);

        fs::path meta = entry.path(); meta += ".meta";
        if (fs::exists(meta)) {
            std::string old = ReadFile(meta);
            std::string updated = RegexReplace(old, R"(guid: [0-9a-f]{32})", "guid: " + guid, 1);
            if (updated != old) {
                WriteFile(meta, updated);
                log("  Updated: " + entry.path().filename().string() + " -> " + guid);
                fixed++;
            } else skipped++;
        } else {
            std::string content =
                "fileFormatVersion: 2\nguid: " + guid + "\nMonoImporter:\n"
                "  externalObjects: {}\n  serializedVersion: 2\n"
                "  defaultReferences: []\n  executionOrder: 0\n"
                "  icon: {instanceID: 0}\n  userData: \n"
                "  assetBundleName: \n  assetBundleVariant: \n";
            WriteFile(meta, content);
            log("  Created .meta: " + entry.path().filename().string() + " -> " + guid);
            fixed++;
        }
    }
    log("  Updated " + std::to_string(fixed) + " GUIDs, skipped " + std::to_string(skipped));
}

//missing reference fixer
static void FixMissingRefs(const fs::path& proj,
                            const std::string& opId,
                            std::function<void(const std::string&)> log) {
    //build script index
    struct ScriptInfo { std::string className; std::set<std::string> fields; };
    std::map<std::string, ScriptInfo> guidMap;

    for (auto& entry : fs::recursive_directory_iterator(proj / "Assets")) {
        if (entry.path().extension() != ".cs") continue;
        fs::path meta = entry.path(); meta += ".meta";
        if (!fs::exists(meta)) continue;
        std::string g = RegexCapture(ReadFile(meta), R"(guid:\s*([0-9a-f]{32}))");
        if (g.empty()) continue;
        std::string src = ReadFile(entry.path());
        std::string cl  = RegexCapture(src, R"((?:class|struct)\s+(\w+))");
        if (cl.empty()) cl = entry.path().stem().string();

        ScriptInfo info;
        info.className = cl;
        std::istringstream ss(src);
        std::string line;
        std::regex fieldRe(R"((?:public|protected|private)\s+\S+\s+(\w+)\s*[;=\[])");
        std::smatch m;
        while (std::getline(ss, line)) {
            if (std::regex_search(line, m, fieldRe)) info.fields.insert(m[1]);
        }
        guidMap[g] = std::move(info);
    }
    log("  Script index: " + std::to_string(guidMap.size()) + " scripts");

    static const char* EXTS[] = { ".unity", ".prefab", ".asset", nullptr };
    int fixed = 0, skipped = 0;

    for (auto& entry : fs::recursive_directory_iterator(proj / "Assets")) {
        bool match = false;
        for (int i = 0; EXTS[i]; i++)
            if (entry.path().extension() == EXTS[i]) { match = true; break; }
        if (!match) continue;

        std::string src = ReadFile(entry.path());
        std::string out = src;
        int hits = 0;

        //split with yaml
        std::vector<std::string> blocks;
        size_t pos = 0;
        std::string sep = "\n--- ";
        while (true) {
            size_t found = src.find(sep, pos);
            if (found == std::string::npos) {
                blocks.push_back(src.substr(pos));
                break;
            }
            blocks.push_back(src.substr(pos, found - pos));
            pos = found + 1;
        }

        for (auto& block : blocks) {
            if (block.find("MonoBehaviour:") == std::string::npos) continue;

            std::string existing = RegexCapture(block,
                R"(m_Script:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-f]{32}))");
            if (!existing.empty() && existing != std::string(32, '0') && guidMap.count(existing)) {
                skipped++; continue;
            }
            if (!existing.empty() && !guidMap.count(existing) && existing != std::string(32, '0')) {
                skipped++; continue;
            }

            //collect keys
            std::set<std::string> blockKeys;
            std::regex keyRe(R"(^\s{2,}(\w+):)");
            std::istringstream bss(block);
            std::string bline;
            while (std::getline(bss, bline)) {
                std::smatch km;
                if (std::regex_search(bline, km, keyRe)) blockKeys.insert(km[1]);
            }

            std::string bestGuid; int bestScore = 0;
            for (auto& [g, info] : guidMap) {
                int score = 0;
                if (ToLower(block).find(ToLower(info.className)) != std::string::npos) score += 5;
                for (auto& f : info.fields)
                    if (blockKeys.count(f)) score++;
                if (score > bestScore) { bestScore = score; bestGuid = g; }
            }

            if (bestGuid.empty() || bestScore < 1) { skipped++; continue; }

            std::string newRef = "m_Script: {fileID: 11500000, guid: " + bestGuid + ", type: 3}";
            std::string patched = RegexReplace(block, R"(m_Script:\s*\{[^}]*\})", newRef, 1);
            if (patched != block) {
                out.replace(out.find(block), block.size(), patched);
                hits++;
                log("  Linked: " + entry.path().filename().string() +
                    " -> " + guidMap[bestGuid].className +
                    " (score " + std::to_string(bestScore) + ")");
            }
        }

        if (hits) { WriteFile(entry.path(), out); fixed += hits; }
    }
    log("  Re-linked " + std::to_string(fixed) + " reference(s), skipped " + std::to_string(skipped));
}

//ui
static std::string GetHtmlPage() {
    //under 16kb for coencitation (BRUH I CANT FUCKING SPELL)
    static std::string cached;
    if (!cached.empty()) return cached;

    const char* S0 = "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n<title>Euphoria - UAR Gap Filler</title>\n<style>\n";
    const char* S1 = ":root{--bg:#05070d;--panel:#070a11;--card:#0c1018;--card2:#111620;--border:#151d2e;--border2:#1e2d47;--accent:#1a6fff;--accent2:#0d4adb;--text:#dde3f0;--dim:#4a5570;--mid:#8892aa;--ok:#0ec97a;--err:#ff4a6e;--warn:#f0a030;--mono:'Consolas','Menlo',monospace}\n"
                    "*{box-sizing:border-box;margin:0;padding:0}\n"
                    "html,body{height:100%;background:var(--bg);color:var(--text);font-family:'Segoe UI','Helvetica Neue',sans-serif}\n"
                    "#app{display:flex;height:100%}\n"
                    "#sidebar{width:200px;background:var(--panel);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:12px 0;flex-shrink:0}\n"
                    ".logo{padding:14px 18px 18px;border-bottom:1px solid var(--border)}\n"
                    ".logo-name{font-size:16px;font-weight:700;color:var(--text)}\n"
                    ".logo-sub{font-size:10px;color:var(--dim);font-family:var(--mono);margin-top:2px}\n"
                    ".nav-sec{font-size:9px;color:var(--dim);letter-spacing:.1em;padding:14px 18px 4px;font-family:var(--mono)}\n"
                    ".nav-item{display:flex;align-items:center;gap:9px;padding:10px 18px;cursor:pointer;color:var(--mid);font-size:13px;font-weight:600;border-left:2px solid transparent;transition:all .12s}\n"
                    ".nav-item:hover{background:var(--card);color:var(--text)}\n"
                    ".nav-item.active{background:rgba(26,111,255,.08);color:var(--text);border-left-color:var(--accent)}\n"
                    ".nav-icon{font-size:14px;width:16px;text-align:center}\n"
                    "#main{flex:1;overflow:hidden;display:flex;flex-direction:column}\n"
                    ".panel{display:none;flex:1;overflow-y:auto;padding:28px 32px;flex-direction:column}\n"
                    ".panel.active{display:flex}\n"
                    ".panel-title{font-size:22px;font-weight:800;margin-bottom:6px}\n"
                    ".panel-sub{font-size:12px;color:var(--mid);font-family:var(--mono);margin-bottom:20px}\n"
                    ".divider{height:1px;background:var(--border);margin:0 0 20px}\n"
                    "#proj-bar{display:flex;align-items:center;gap:8px;background:var(--card);border:1px solid var(--border);border-radius:6px;padding:8px 14px;margin-bottom:16px}\n"
                    ".proj-lbl{font-family:var(--mono);font-size:10px;color:var(--dim)}\n"
                    "#proj-name{font-family:var(--mono);font-size:11px;color:var(--text);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n"
                    ".btn-sm{background:var(--card2);border:1px solid var(--border2);color:var(--mid);font-family:var(--mono);font-size:10px;padding:4px 10px;border-radius:4px;cursor:pointer;transition:all .12s}\n"
                    ".btn-sm:hover{border-color:var(--accent);color:var(--text)}\n";
    const char* S2 = ".fix-card{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:10px;transition:border-color .15s}\n"
                    ".fix-card:hover{border-color:var(--border2)}\n"
                    ".fix-card.running{border-color:var(--warn)}\n"
                    ".fix-card.done-ok{border-color:var(--ok)}\n"
                    ".fix-card.done-err{border-color:var(--err)}\n"
                    ".fix-top{display:flex;align-items:center;gap:12px;padding:14px 16px}\n"
                    ".fix-icon{width:32px;height:32px;border-radius:6px;background:rgba(26,111,255,.1);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}\n"
                    ".fix-meta{flex:1}\n"
                    ".fix-title{font-size:13px;font-weight:700;margin-bottom:2px}\n"
                    ".fix-sub{font-size:11px;color:var(--mid);font-family:var(--mono)}\n"
                    ".fix-status{font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.07em;padding:2px 7px;border-radius:3px}\n"
                    ".s-idle{background:var(--card2);color:var(--dim)}\n"
                    ".s-run{background:rgba(240,160,48,.15);color:var(--warn)}\n"
                    ".s-ok{background:rgba(14,201,122,.15);color:var(--ok)}\n"
                    ".s-err{background:rgba(255,74,110,.15);color:var(--err)}\n"
                    ".fix-actions{display:flex;align-items:center;gap:10px;padding:0 16px 10px}\n"
                    ".btn-run{background:var(--accent);color:#fff;border:none;font-size:12px;font-weight:700;padding:7px 16px;border-radius:5px;cursor:pointer;transition:background .12s}\n"
                    ".btn-run:hover{background:var(--accent2)}\n"
                    ".btn-run:disabled{opacity:.4;cursor:not-allowed}\n"
                    ".fix-summary{font-family:var(--mono);font-size:10px;color:var(--mid);flex:1}\n"
                    ".prog-track{height:2px;background:var(--border);margin:0 16px 0;border-radius:1px;overflow:hidden}\n"
                    ".prog-fill{height:100%;background:var(--accent);width:0%;transition:width .3s}\n"
                    ".prog-fill.ind{width:40%;animation:ind 1.2s ease-in-out infinite}\n"
                    "@keyframes ind{0%{transform:translateX(-200%)}100%{transform:translateX(400%)}}\n"
                    ".log-toggle{font-family:var(--mono);font-size:10px;color:var(--dim);padding:6px 16px 8px;cursor:pointer;user-select:none}\n"
                    ".log-toggle:hover{color:var(--text)}\n"
                    ".log-box{display:none;margin:0 16px 10px;background:#04080f;border:1px solid var(--border);border-radius:4px;padding:8px;font-family:var(--mono);font-size:11px;line-height:1.65;color:var(--mid);max-height:160px;overflow-y:auto}\n"
                    ".log-box.open{display:block}\n"
                    ".log-ok{color:var(--ok)}.log-err{color:var(--err)}.log-warn{color:var(--warn)}\n";
    const char* S3 = ".diff-box{display:none;margin:0 16px 10px;border:1px solid var(--border);border-radius:4px;overflow:hidden}\n"
                    ".diff-box.open{display:block}\n"
                    ".diff-bar{background:#070a11;padding:6px 10px;display:flex;align-items:center;gap:8px;border-bottom:1px solid var(--border)}\n"
                    ".diff-bar select{background:#0c1018;border:1px solid var(--border2);color:var(--text);font-family:var(--mono);font-size:10px;padding:2px 6px;border-radius:3px}\n"
                    ".diff-stat{font-family:var(--mono);font-size:10px;margin-left:auto}\n"
                    ".diff-content{background:#04080f;overflow:auto;max-height:200px;font-family:var(--mono);font-size:11px}\n"
                    "table.diff{border-collapse:collapse;width:100%}\n"
                    "table.diff td{padding:1px 10px;white-space:pre;vertical-align:top}\n"
                    ".d-ln{width:40px;text-align:right;color:var(--dim);border-right:1px solid var(--border);user-select:none}\n"
                    ".d-add{background:rgba(14,201,122,.08);color:#4dff88}\n"
                    ".d-add .d-ln{background:rgba(14,201,122,.05);color:rgba(14,201,122,.4)}\n"
                    ".d-rem{background:rgba(255,74,110,.08);color:#ff6070}\n"
                    ".d-rem .d-ln{background:rgba(255,74,110,.05);color:rgba(255,74,110,.4)}\n"
                    ".d-hdr{background:rgba(26,111,255,.07);color:var(--accent)}\n"
                    ".d-ctx{color:#2a3545}\n"
                    ".hist-bar{display:flex;gap:8px;margin-bottom:12px}\n"
                    "#hist-list{background:var(--card);border:1px solid var(--border);border-radius:6px;overflow-y:auto;max-height:200px;margin-bottom:12px}\n"
                    ".hist-row{display:flex;align-items:center;gap:10px;padding:8px 14px;border-bottom:1px solid var(--border);cursor:pointer;font-family:var(--mono);font-size:11px;color:var(--mid);transition:background .1s}\n"
                    ".hist-row:hover{background:var(--card2);color:var(--text)}\n"
                    ".hist-row:last-child{border-bottom:none}\n"
                    ".hist-op{flex:1;color:var(--text)}.hist-ts{color:var(--dim);font-size:10px}\n"
                    "#modal{display:none;position:fixed;inset:0;background:rgba(4,6,13,.85);backdrop-filter:blur(4px);z-index:100;align-items:center;justify-content:center}\n"
                    "#modal.open{display:flex}\n"
                    "#modal-box{background:var(--card);border:1px solid var(--border2);border-radius:10px;width:440px;max-height:80vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.6)}\n"
                    "#modal-hdr{padding:16px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}\n"
                    "#modal-hdr h3{font-size:14px;font-weight:700}\n"
                    "#modal-close{background:none;border:none;color:var(--dim);font-size:18px;cursor:pointer;line-height:1}\n"
                    "#modal-close:hover{color:var(--text)}\n"
                    "#modal-body{padding:14px 18px;overflow-y:auto;flex:1}\n"
                    ".modal-proj{background:var(--card2);border:1px solid var(--border);border-radius:5px;padding:9px 12px;cursor:pointer;margin-bottom:6px;transition:border-color .1s}\n"
                    ".modal-proj:hover{border-color:var(--accent)}\n"
                    ".modal-proj-name{font-weight:700;font-size:13px}\n"
                    ".modal-proj-path{font-family:var(--mono);font-size:10px;color:var(--dim);margin-top:1px}\n"
                    "#modal-ftr{padding:10px 18px;border-top:1px solid var(--border);display:flex;gap:8px}\n"
                    "#modal-custom{flex:1;background:var(--panel);border:1px solid var(--border2);color:var(--text);font-family:var(--mono);font-size:11px;padding:6px 10px;border-radius:4px;outline:none}\n"
                    "#modal-custom:focus{border-color:var(--accent)}\n"
                    "#toast{position:fixed;bottom:20px;right:20px;background:var(--card);border:1px solid var(--border2);border-radius:7px;padding:10px 14px;display:flex;align-items:center;gap:10px;min-width:240px;box-shadow:0 8px 28px rgba(0,0,0,.5);transform:translateY(60px);opacity:0;transition:all .22s;z-index:200;pointer-events:none}\n"
                    "#toast.show{transform:translateY(0);opacity:1}\n"
                    ".toast-bar{width:3px;border-radius:2px;align-self:stretch;flex-shrink:0}\n"
                    ".toast-title{font-size:12px;font-weight:700}\n"
                    ".toast-body{font-family:var(--mono);font-size:10px;color:var(--mid)}\n"
                    "::-webkit-scrollbar{width:4px;height:4px}\n"
                    "::-webkit-scrollbar-track{background:transparent}\n"
                    "::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px}\n"
                    "</style>\n</head>\n<body>\n";
    const char* S4 =
        "<div id=\"app\">\n"
        "<nav id=\"sidebar\">\n"
        "  <div class=\"logo\"><div class=\"logo-name\">Euphoria</div><div class=\"logo-sub\">UAR Gap Filler v2.1</div></div>\n"
        "  <div class=\"nav-sec\">MODULES</div>\n"
        "  <div class=\"nav-item active\" onclick=\"nav('fixes')\"><span class=\"nav-icon\">F</span>Unity Fixes</div>\n"
        "  <div class=\"nav-item\" onclick=\"nav('history')\"><span class=\"nav-icon\">H</span>History</div>\n"
        "  <div class=\"nav-item\" onclick=\"nav('about')\"><span class=\"nav-icon\">A</span>About</div>\n"
        "</nav>\n"
        "<div id=\"main\">\n"
        "<div id=\"panel-fixes\" class=\"panel active\">\n"
        "  <div class=\"panel-title\">Unity Fixes</div>\n"
        "  <div class=\"panel-sub\">Patches for UAR-extracted projects</div>\n"
        "  <div class=\"divider\"></div>\n"
        "  <div id=\"proj-bar\">\n"
        "    <span class=\"proj-lbl\">PROJECT</span>\n"
        "    <span id=\"proj-name\">None selected</span>\n"
        "    <button class=\"btn-sm\" onclick=\"openModal()\">Change</button>\n"
        "  </div>\n"
        "  <div id=\"cards\"></div>\n"
        "</div>\n"
        "<div id=\"panel-history\" class=\"panel\">\n"
        "  <div class=\"panel-title\">History</div>\n"
        "  <div class=\"panel-sub\">Undo / redo per-operation file changes</div>\n"
        "  <div class=\"divider\"></div>\n"
        "  <div class=\"hist-bar\"><button class=\"btn-sm\" onclick=\"doUndo()\">Undo</button><button class=\"btn-sm\" onclick=\"doRedo()\">Redo</button></div>\n"
        "  <div id=\"hist-list\"><div style=\"padding:12px 14px;font-family:var(--mono);font-size:11px;color:var(--dim)\">No operations yet.</div></div>\n"
        "  <div id=\"hist-diff-box\" class=\"diff-box open\" style=\"margin:0\">\n"
        "    <div class=\"diff-bar\"><span style=\"font-family:var(--mono);font-size:10px;color:var(--dim)\">Select an operation to view its diff</span></div>\n"
        "    <div class=\"diff-content\" id=\"hist-diff-view\" style=\"min-height:80px\"></div>\n"
        "  </div>\n"
        "</div>\n"
        "<div id=\"panel-about\" class=\"panel\">\n"
        "  <div class=\"panel-title\">About</div>\n"
        "  <div class=\"panel-sub\">UAR Gap Filler - @dudeluther1232 - @shxyder</div>\n"
        "  <div class=\"divider\"></div>\n"
        "  <div style=\"font-size:13px;line-height:1.7;color:var(--mid);max-width:560px\">\n"
        "    Hello, this is a project <strong style=\"color:var(--text)\">@dudeluther1232</strong> and <strong style=\"color:var(--text)\">@shxyder</strong> are working on.\n"
        "    This is an attempt to fulfill the gaps that UAR (UnityAssetRipper) could not.\n"
        "    All fixes run locally. The DLL hosts this page on <code style=\"font-family:var(--mono);color:var(--accent)\">localhost:8000</code> using the Windows HTTP Server API with no external dependencies.\n"
        "    <br><br><strong style=\"color:var(--text)\">Have fun.</strong>\n"
        "  </div>\n"
        "</div>\n"
        "</div></div>\n"
        "<div id=\"modal\" onclick=\"closeModalOutside(event)\">\n"
        "  <div id=\"modal-box\">\n"
        "    <div id=\"modal-hdr\"><h3>Select Unity Project</h3><button id=\"modal-close\" onclick=\"closeModal()\">X</button></div>\n"
        "    <div id=\"modal-body\"><div style=\"font-family:var(--mono);font-size:11px;color:var(--dim)\">Scanning...</div></div>\n"
        "    <div id=\"modal-ftr\"><input id=\"modal-custom\" type=\"text\" placeholder=\"Or paste project path...\"><button class=\"btn-sm\" onclick=\"useCustomPath()\">Use Path</button></div>\n"
        "  </div>\n"
        "</div>\n"
        "<div id=\"toast\"><div class=\"toast-bar\" id=\"toast-bar\"></div><div><div class=\"toast-title\" id=\"toast-title\"></div><div class=\"toast-body\" id=\"toast-body\"></div></div></div>\n";
    const char* S5 =
        "<script>\n"
        "const FIXES=[\n"
        "  {id:'shader',  icon:'S', title:'TMP Shader Fix',         sub:'Inject SDF shader + patch TMP materials'},\n"
        "  {id:'broken',  icon:'B', title:'Broken Shader Auto-Fix', sub:'Remap pink / missing .mat shader refs'},\n"
        "  {id:'guid',    icon:'G', title:'Script GUID Stability',  sub:'Deterministic .meta GUIDs from class name'},\n"
        "  {id:'ref_fix', icon:'R', title:'Missing Reference Fixer',sub:'Re-link zeroed m_Script MonoBehaviours'},\n"
        "];\n"
        "let currentProject=null,history=[],undoStack=[],redoStack=[],fixLogs={},fixDiffs={};\n"
        "const cardsEl=document.getElementById('cards');\n"
        "FIXES.forEach(f=>{\n"
        "  cardsEl.innerHTML+=`<div class=\"fix-card\" id=\"card-${f.id}\"><div class=\"fix-top\"><div class=\"fix-icon\">${f.icon}</div><div class=\"fix-meta\"><div class=\"fix-title\">${f.title}</div><div class=\"fix-sub\">${f.sub}</div></div><span class=\"fix-status s-idle\" id=\"status-${f.id}\">IDLE</span></div><div class=\"prog-track\"><div class=\"prog-fill\" id=\"prog-${f.id}\"></div></div><div class=\"fix-actions\"><button class=\"btn-run\" id=\"btn-${f.id}\" onclick=\"runFix('${f.id}')\">Run</button><span class=\"fix-summary\" id=\"sum-${f.id}\"></span></div><div class=\"log-toggle\" onclick=\"toggleLog('${f.id}')\">log / diff</div><div class=\"log-box\" id=\"log-${f.id}\"></div><div class=\"diff-box\" id=\"diff-${f.id}\"><div class=\"diff-bar\"><select id=\"dsel-${f.id}\" onchange=\"renderDiff('${f.id}')\"></select><span class=\"diff-stat\" id=\"dstat-${f.id}\"></span></div><div class=\"diff-content\" id=\"dview-${f.id}\"></div></div></div>`;\n"
        "});\n"
        "function nav(p){document.querySelectorAll('.panel').forEach(el=>el.classList.remove('active'));document.querySelectorAll('.nav-item').forEach(el=>el.classList.remove('active'));document.getElementById('panel-'+p).classList.add('active');event.currentTarget.classList.add('active');if(p==='history')refreshHistory();}\n"
        "async function openModal(){document.getElementById('modal').classList.add('open');const body=document.getElementById('modal-body');body.innerHTML='<div style=\"font-family:var(--mono);font-size:11px;color:var(--dim)\">Scanning...</div>';const data=await fetch('/api/projects').then(r=>r.json());if(!data.length){body.innerHTML='<div style=\"font-family:var(--mono);font-size:11px;color:var(--dim)\">No projects found.</div>';return;}body.innerHTML='';data.forEach(p=>{const el=document.createElement('div');el.className='modal-proj';el.innerHTML=`<div class=\"modal-proj-name\">${p.name}</div><div class=\"modal-proj-path\">${p.path}</div>`;el.onclick=()=>{setProject(p.path);closeModal();};body.appendChild(el);});}\n"
        "function closeModal(){document.getElementById('modal').classList.remove('open');}\n"
        "function closeModalOutside(e){if(e.target===document.getElementById('modal'))closeModal();}\n"
        "function useCustomPath(){const p=document.getElementById('modal-custom').value.trim();if(p){setProject(p);closeModal();}}\n"
        "function setProject(p){currentProject=p;const parts=p.replace(/\\\\/g,'/').split('/');document.getElementById('proj-name').textContent=parts[parts.length-1]||p;showToast('Project set',parts[parts.length-1],true);}\n"
        "function toggleLog(id){const log=document.getElementById('log-'+id);const diff=document.getElementById('diff-'+id);const tog=document.querySelector('#card-'+id+' .log-toggle');const open=log.classList.toggle('open');diff.classList.toggle('open',open);tog.textContent=(open?'v ':'')+' log / diff';}\n";
    const char* S6 =
        "async function runFix(id){\n"
        "  if(!currentProject){openModal();return;}\n"
        "  const btn=document.getElementById('btn-'+id);\n"
        "  if(btn.disabled)return;\n"
        "  btn.disabled=true;\n"
        "  fixLogs[id]=[];fixDiffs[id]=[];\n"
        "  document.getElementById('log-'+id).innerHTML='';\n"
        "  document.getElementById('dview-'+id).innerHTML='';\n"
        "  document.getElementById('dsel-'+id).innerHTML='';\n"
        "  document.getElementById('dstat-'+id).textContent='';\n"
        "  document.getElementById('sum-'+id).textContent='';\n"
        "  setCardState(id,'running');\n"
        "  if(!document.getElementById('log-'+id).classList.contains('open'))toggleLog(id);\n"
        "  const prog=document.getElementById('prog-'+id);\n"
        "  prog.classList.add('ind');prog.style.width='40%';\n"
        "  const resp=await fetch('/api/run/'+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:currentProject})});\n"
        "  if(!resp.ok){setCardState(id,'err');btn.disabled=false;prog.classList.remove('ind');return;}\n"
        "  const {op_id}=await resp.json();\n"
        "  let lastLog=0;\n"
        "  const poll=setInterval(async()=>{\n"
        "    const d=await fetch('/api/poll/'+op_id).then(r=>r.json());\n"
        "    const newLines=d.logs.slice(lastLog);lastLog=d.logs.length;\n"
        "    fixLogs[id]=d.logs;\n"
        "    const logEl=document.getElementById('log-'+id);\n"
        "    newLines.forEach(line=>{const div=document.createElement('div');const t=line.trim();if(t.startsWith('ok'))div.className='log-ok';else if(t.startsWith('ERROR')||t.startsWith('err'))div.className='log-err';else if(t.startsWith('warn'))div.className='log-warn';div.textContent=line;logEl.appendChild(div);logEl.scrollTop=logEl.scrollHeight;});\n"
        "    if(d.result!==null){clearInterval(poll);prog.classList.remove('ind');prog.style.width=d.result.success?'100%':'30%';prog.style.background=d.result.success?'var(--ok)':'var(--err)';setCardState(id,d.result.success?'ok':'err');document.getElementById('sum-'+id).textContent=d.result.summary;btn.disabled=false;fixDiffs[id]=d.result.diffs||[];buildDiffSelector(id);if(d.result.record)addHistory(d.result.record);showToast(d.result.success?'Done':'Error',d.result.summary,d.result.success);}\n"
        "  },350);\n"
        "}\n"
        "function setCardState(id,state){const card=document.getElementById('card-'+id);const status=document.getElementById('status-'+id);card.className='fix-card'+(state==='running'?' running':state==='ok'?' done-ok':state==='err'?' done-err':'');status.className='fix-status '+(state==='running'?'s-run':state==='ok'?'s-ok':state==='err'?'s-err':'s-idle');status.textContent=state==='running'?'RUNNING':state==='ok'?'DONE':state==='err'?'ERROR':'IDLE';}\n"
        "function buildDiffSelector(id){const sel=document.getElementById('dsel-'+id);sel.innerHTML='';(fixDiffs[id]||[]).forEach((d,i)=>{const parts=d.path.replace(/\\\\/g,'/').split('/');const opt=document.createElement('option');opt.value=i;opt.textContent=parts[parts.length-1];sel.appendChild(opt);});if(fixDiffs[id]&&fixDiffs[id].length)renderDiff(id);}\n"
        "function renderDiff(id){const sel=document.getElementById('dsel-'+id);const idx=parseInt(sel.value)||0;const diffs=fixDiffs[id]||[];const view=document.getElementById('dview-'+id);const stat=document.getElementById('dstat-'+id);if(!diffs[idx]||!diffs[idx].diff){view.innerHTML='';return;}const {html,adds,rems}=buildDiffHtml(diffs[idx].diff);view.innerHTML=html;stat.textContent='+'+adds+'  -'+rems;stat.style.color=adds>=rems?'var(--ok)':'var(--err)';}\n"
        "function buildDiffHtml(diffText){let adds=0,rems=0,lnum=0;let html='<table class=\"diff\"><tbody>';diffText.split('\\n').forEach(line=>{lnum++;const esc=line.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');let cls='d-ctx';if(line.startsWith('+++')||line.startsWith('---'))cls='d-hdr';else if(line.startsWith('@@'))cls='d-hdr';else if(line.startsWith('+')){cls='d-add';adds++;}else if(line.startsWith('-')){cls='d-rem';rems++;}html+=`<tr class=\"${cls}\"><td class=\"d-ln\">${lnum}</td><td>${esc}</td></tr>`;});html+='</tbody></table>';return {html,adds,rems};}\n"
        "function addHistory(record){undoStack.push(record);redoStack=[];refreshHistory();}\n"
        "function refreshHistory(){const el=document.getElementById('hist-list');if(!undoStack.length&&!redoStack.length){el.innerHTML='<div style=\"padding:12px 14px;font-family:var(--mono);font-size:11px;color:var(--dim)\">No operations yet.</div>';return;}el.innerHTML='';[...undoStack].reverse().forEach((r)=>{const div=document.createElement('div');div.className='hist-row';div.innerHTML='<span class=\"hist-op\">'+r.op+'</span><span class=\"hist-ts\">'+r.ts+' - '+r.files.length+' file(s)</span>';div.onclick=()=>showHistDiff(r);el.appendChild(div);});redoStack.forEach(r=>{const div=document.createElement('div');div.className='hist-row';div.style.opacity='.5';div.innerHTML='<span class=\"hist-op\">[redo] '+r.op+'</span><span class=\"hist-ts\">'+r.ts+'</span>';el.appendChild(div);});}\n"
        "function showHistDiff(record){if(!record.files||!record.files.length)return;const view=document.getElementById('hist-diff-view');const box=document.getElementById('hist-diff-box');const {html,adds,rems}=buildDiffHtml(record.files[0].diff||'');view.innerHTML=html||'<div style=\"padding:12px;font-family:var(--mono);font-size:11px;color:var(--dim)\">(no diff)</div>';box.querySelector('.diff-bar span').textContent=(record.files[0].path||'').split(/[\\/\\\\]/).pop()+' +'+adds+' -'+rems;}\n"
        "async function doUndo(){if(!undoStack.length){showToast('Nothing to undo','',false);return;}const rec=undoStack.pop();redoStack.push(rec);await fetch('/api/undo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record:rec})});showToast('Undone',rec.op+' restored',true);refreshHistory();}\n"
        "async function doRedo(){if(!redoStack.length){showToast('Nothing to redo','',false);return;}const rec=redoStack.pop();undoStack.push(rec);await fetch('/api/redo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record:rec})});showToast('Redone',rec.op+' re-applied',true);refreshHistory();}\n"
        "let toastTimer;\n"
        "function showToast(title,body,ok){document.getElementById('toast-title').textContent=title;document.getElementById('toast-body').textContent=body;document.getElementById('toast-bar').style.background=ok?'var(--ok)':'var(--err)';const t=document.getElementById('toast');t.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('show'),3200);}\n"
        "</script></body></html>\n";

    cached = std::string(S0)+S1+S2+S3+S4+S5+S6;
    return cached;
}

//https response helpers
static void SendResponse(HANDLE hQueue, const HTTP_REQUEST* req,
                          USHORT statusCode, const char* reason,
                          const std::string& contentType,
                          const std::string& body) {
    HTTP_RESPONSE response = {};
    response.StatusCode   = statusCode;
    response.pReason      = reason;
    response.ReasonLength = (USHORT)strlen(reason);

    HTTP_UNKNOWN_HEADER headers[2];
    USHORT headerCount = 0;

    headers[headerCount].pName      = "Content-Type";
    headers[headerCount].NameLength = 12;
    headers[headerCount].pRawValue  = contentType.c_str();
    headers[headerCount].RawValueLength = (USHORT)contentType.size();
    headerCount++;

    headers[headerCount].pName      = "Access-Control-Allow-Origin";
    headers[headerCount].NameLength = 27;
    headers[headerCount].pRawValue  = "*";
    headers[headerCount].RawValueLength = 1;
    headerCount++;

    response.Headers.pUnknownHeaders   = headers;
    response.Headers.UnknownHeaderCount = headerCount;

    HTTP_DATA_CHUNK chunk = {};
    chunk.DataChunkType           = HttpDataChunkFromMemory;
    chunk.FromMemory.pBuffer      = (PVOID)body.data();
    chunk.FromMemory.BufferLength = (ULONG)body.size();

    response.EntityChunkCount = 1;
    response.pEntityChunks    = &chunk;

    HttpSendHttpResponse(hQueue, req->RequestId, 0, &response,
                         nullptr, nullptr, nullptr, 0, nullptr, nullptr);
}

static std::string ReadRequestBody(HANDLE hQueue, const HTTP_REQUEST* req) {
    std::string body;
    if (req->Flags & HTTP_REQUEST_FLAG_MORE_ENTITY_BODY_EXISTS) {
        std::vector<char> buf(4096);
        ULONG bytesRead = 0;
        HTTP_REQUEST_ID reqId = req->RequestId;
        while (true) {
            ULONG ret = HttpReceiveRequestEntityBody(
                hQueue, reqId, 0,
                buf.data(), (ULONG)buf.size(),
                &bytesRead, nullptr);
            if (ret == NO_ERROR || ret == ERROR_HANDLE_EOF) {
                body.append(buf.data(), bytesRead);
                if (ret == ERROR_HANDLE_EOF) break;
            } else break;
        }
    }
    return body;
}

//json value extractor
static std::string JsonGetString(const std::string& json, const std::string& key) {
    std::string pattern = "\"" + key + "\"\\s*:\\s*\"([^\"]+)\"";
    return RegexCapture(json, pattern);
}

//route handlers
static void HandleRequest(HANDLE hQueue, const HTTP_REQUEST* req) {
    //convert url
    std::wstring urlW(req->CookedUrl.pAbsPath,
                      req->CookedUrl.AbsPathLength / sizeof(wchar_t));
    int needed = WideCharToMultiByte(CP_UTF8, 0, urlW.c_str(), (int)urlW.size(), nullptr, 0, nullptr, nullptr);
    std::string url(needed, '\0');
    WideCharToMultiByte(CP_UTF8, 0, urlW.c_str(), (int)urlW.size(), &url[0], needed, nullptr, nullptr);

    size_t q = url.find('?');
    if (q != std::string::npos) url = url.substr(0, q);

    std::string method;
    switch (req->Verb) {
        case HttpVerbGET:  method = "GET";  break;
        case HttpVerbPOST: method = "POST"; break;
        default:           method = "OTHER";
    }

    // GET /
    if (method == "GET" && (url == "/" || url.empty())) {
        SendResponse(hQueue, req, 200, "OK", "text/html; charset=utf-8", GetHtmlPage());
        return;
    }

    // GET /api/projects
    if (method == "GET" && url == "/api/projects") {
        auto projects = FindUnityProjects();
        std::string json = "[";
        for (size_t i = 0; i < projects.size(); i++) {
            if (i) json += ",";
            std::string name = projects[i].filename().string();
            std::string path = projects[i].string();
            json += "{\"name\":" + JsonStr(name) + ",\"path\":" + JsonStr(path) + "}";
        }
        json += "]";
        SendResponse(hQueue, req, 200, "OK", "application/json", json);
        return;
    }

    // POST /api/run/<op>
    if (method == "POST" && url.rfind("/api/run/", 0) == 0) {
        std::string op    = url.substr(9);
        std::string body  = ReadRequestBody(hQueue, req);
        std::string proj  = JsonGetString(body, "project");

        if (proj.empty() || !fs::exists(proj)) {
            SendResponse(hQueue, req, 400, "Bad Request",
                         "application/json", "{\"error\":\"invalid project\"}");
            return;
        }

        std::string opId = MakeOpId();
        {
            std::lock_guard<std::mutex> lk(g_opMutex);
            g_logs[opId]    = {};
            g_results[opId] = "";
        }

        //launch fix
        std::thread([op, proj, opId]() {
            fs::path projPath(proj);
            auto log = [&](const std::string& msg) {
                std::lock_guard<std::mutex> lk(g_opMutex);
                g_logs[opId].push_back(msg);
            };

            //collect files
            struct FileEntry { std::string path, before, after; };
            std::vector<FileEntry> changedFiles;

            bool success = true;
            std::string summary;

            if (op == "shader") {
                FixInjectShader(projPath, opId, log);
                summary = "TMP shader injected and materials patched";
            } else if (op == "broken") {
                FixBrokenShaders(projPath, opId, log);
                summary = "Broken shader references remapped";
            } else if (op == "guid") {
                FixScriptGuids(projPath, opId, log);
                summary = "Script GUIDs stabilised";
            } else if (op == "ref_fix") {
                FixMissingRefs(projPath, opId, log);
                summary = "Missing script references relinked";
            } else {
                success = false;
                summary = "Unknown operation";
            }

            //build json
            std::string logs_json = "[";
            {
                std::lock_guard<std::mutex> lk(g_opMutex);
                auto& lv = g_logs[opId];
                for (size_t i = 0; i < lv.size(); i++) {
                    if (i) logs_json += ",";
                    logs_json += JsonStr(lv[i]);
                }
            }
            logs_json += "]";

            std::string result =
                "{\"success\":" + std::string(success ? "true" : "false") +
                ",\"summary\":" + JsonStr(summary) +
                ",\"diffs\":[]" +
                ",\"record\":{\"op\":" + JsonStr(op) + ",\"ts\":\"now\",\"files\":[]}" +
                "}";

            std::lock_guard<std::mutex> lk(g_opMutex);
            g_results[opId] = result;
        }).detach();

        SendResponse(hQueue, req, 200, "OK",
                     "application/json", "{\"op_id\":" + JsonStr(opId) + "}");
        return;
    }

    // GET /api/poll/<op_id>
    if (method == "GET" && url.rfind("/api/poll/", 0) == 0) {
        std::string opId = url.substr(10);
        std::string logsJson, resultJson;
        {
            std::lock_guard<std::mutex> lk(g_opMutex);
            logsJson   = JsonArr(g_logs.count(opId) ? g_logs[opId] : std::vector<std::string>{});
            resultJson = g_results.count(opId) ? g_results[opId] : "null";
        }
        std::string resp = "{\"logs\":" + logsJson + ",\"result\":" + resultJson + "}";
        SendResponse(hQueue, req, 200, "OK", "application/json", resp);
        return;
    }

    // POST /api/undo  POST /api/redo  (no-op server side - client owns stacks)
    if (method == "POST" && (url == "/api/undo" || url == "/api/redo")) {
        SendResponse(hQueue, req, 200, "OK", "application/json", "{\"ok\":true}");
        return;
    }

    // 404
    SendResponse(hQueue, req, 404, "Not Found", "text/plain", "Not Found");
}

//server loop
static void ServerLoop() {
    std::vector<BYTE> buf(16384);

    while (g_running) {
        HTTP_REQUEST* req = reinterpret_cast<HTTP_REQUEST*>(buf.data());
        ULONG bytesRead   = 0;
        ULONG ret         = HttpReceiveHttpRequest(
            g_hReqQueue, HTTP_NULL_ID, 0,
            req, (ULONG)buf.size(), &bytesRead, nullptr);

        if (!g_running) break;

        if (ret == NO_ERROR) {
            HandleRequest(g_hReqQueue, req);
        } else if (ret == ERROR_MORE_DATA) {
            buf.resize(bytesRead + 1024);
        } else if (ret == ERROR_CONNECTION_INVALID ||
                   ret == ERROR_OPERATION_ABORTED) {
            break;
        }
    }
}

//export api
extern "C" {

__declspec(dllexport) int EuphoriaStart() {
    if (g_running) return 0;

    ULONG ret = HttpInitialize(HTTPAPI_VERSION_1, HTTP_INITIALIZE_SERVER, nullptr);
    if (ret != NO_ERROR) return (int)ret;

    ret = HttpCreateHttpHandle(&g_hReqQueue, 0);
    if (ret != NO_ERROR) { HttpTerminate(HTTP_INITIALIZE_SERVER, nullptr); return (int)ret; }

    ret = HttpAddUrl(g_hReqQueue, L"http://localhost:8000/", nullptr);
    if (ret != NO_ERROR) {
        CloseHandle(g_hReqQueue); g_hReqQueue = nullptr;
        HttpTerminate(HTTP_INITIALIZE_SERVER, nullptr);
        return (int)ret;
    }

    g_running     = true;
    g_serverThread = std::thread(ServerLoop);

    //open site
    ShellExecuteA(nullptr, "open", "http://localhost:8000", nullptr, nullptr, SW_SHOWNORMAL);
    return 0;
}

__declspec(dllexport) void EuphoriaStop() {
    if (!g_running) return;
    g_running = false;
    if (g_hReqQueue) {
        HttpRemoveUrl(g_hReqQueue, L"http://localhost:8000/");
        CloseHandle(g_hReqQueue);
        g_hReqQueue = nullptr;
    }
    if (g_serverThread.joinable()) g_serverThread.join();
    HttpTerminate(HTTP_INITIALIZE_SERVER, nullptr);
}

__declspec(dllexport) int EuphoriaIsRunning() {
    return g_running ? 1 : 0;
}

} // extern "C"

//dll entry
BOOL WINAPI DllMain(HINSTANCE, DWORD fdwReason, LPVOID) {
    if (fdwReason == DLL_PROCESS_DETACH) EuphoriaStop();
    return TRUE;
}
