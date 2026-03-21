# Welcome to Euphoria

# Euphoria — UAR Gap Filler

**v2.1** · Python 3.9+ · tkinter (stdlib only)  

**dll**  · Python 3.9+ (64-bit) · ctypes (stdlib only) · Visual Studio 2019/2022 w/ Build Tools and Desktop development with C++ workload · Windows SDK 10.0+ · C++ 17 or later · httpapi.dll · ws2_32.dll · ole32.dll · shell32.dll · shlwapi.dll · advapi32.dll

*@dudeluther1232 · @shxyder*

-----

Euphoria fixes the common breakages that [UnityAssetRipper](https://github.com/AssetRipper/AssetRipper) leaves behind when extracting a Unity project. Run it against your ripped project folder before opening it in Unity and most of the usual pain goes away.

-----

## Requirements

### Python Release
- Python 3.9 or newer
- tkinter (included with standard Python on Windows and macOS; on Linux: `sudo apt install python3-tk`)
- No third-party packages

### Build from C++ to dll
- Python 3.9 or newer
- ctypes (included with stlib)
- Visual Studio 2019/2022 w/ Build Tools and Desktop development with C++ workload
- Windows SDK 10.0+
- C++ 17 or later
(The following are all Windows built-ins)
- httpapi.dll
- ws2_32.dll
- ole32.dll
- shell32.dll
- shlwapi.dll
- advapi32.dll
-----

## Running Python Release

```bash
python Euphoria.py
```

The window opens centered on the screen. Select your Unity project either from the auto-detected list or by browsing manually.

## Running C++ to dll

Download euphoriaServer.cpp and open x64 Native Tools Command Prompt for VS. Then run

```bash
cl /LD /EHsc /std:c++17 euphoriaServer.cpp /link /OUT:euphoriaServer.dll
```

After building from source, run

```python
import ctypes
dll = ctypes.WinDLL(r"euphoriaServer.dll")
dll.EuphoriaStart()
input("press enter to stop...")
dll.EuphoriaStop()
```
This will open a localhost:8000 with Euphoria running in it.

-----

## Fixes

### TMP Shader Fix

Injects `Wasmcomfix.shader` into `Assets/Shaders/WASMCOM/` and rewrites every TextMeshPro material in the project to reference it. Fixes the red/black boxes that appear when TMP can’t locate its SDF shader after a rip. After running, it also scans every `.unity`, `.prefab`, and `.asset` file and reports all TMP component instances found (TextMeshPro, TextMeshProUGUI, TMP_InputField, TMP_Dropdown, TMP_SubMesh, TMP_SubMeshUI, TMP_FontAsset, TMP_SpriteAsset).

A step-by-step tutorial overlay appears after injection to guide you through applying the shader inside Unity.

### Broken Shader Auto-Fix

Scans every `.mat` file in `Assets/` for broken shader references — the cause of pink/magenta meshes. Builds an index of every `.shader` file present in the project and attempts to remap broken materials by:

1. Matching the material name against known shader names
1. Matching standard PBR property keywords (`_Color`, `_MainTex`, `_Glossiness`, `_Metallic`)
1. Scoring property-name overlap between the material and each candidate shader

Falls back to the built-in Unity Standard shader if no project shader matches. Reimport Assets in Unity after running.

### Script GUID Stability

Unity identifies scripts by a GUID stored in their `.meta` file. After a rip, these are often random or missing, which breaks every `m_Script` reference in scenes and prefabs. This fix derives GUIDs deterministically from `MD5(namespace + classname)`, matching Unity’s own algorithm, so GUIDs stay stable across re-exports. Creates `.meta` files for any `.cs` files that are missing one.

### Missing Reference Fixer

Scans every `.unity`, `.prefab`, and `.asset` file for `MonoBehaviour` components whose `m_Script` GUID is all-zeros (the “Missing Script” error in the Unity Inspector). For each broken component, it builds a score against every `.cs` script in the project:

- **+5** if the class name appears in the YAML block
- **+n** for each serialised field name that overlaps between the block and the script

The highest-scoring script is re-linked. Run *Script GUID Stability* first for best results. Reimport Scripts in Unity after running.

-----

## History, Undo & Redo

Every fix records the before and after content of each file it touches. The **History** panel (second item in the sidebar) lists every operation run this session with its timestamp and file count. Clicking an entry shows a full colour-coded unified diff in the right pane.

**↩ Undo** restores all files touched by the most recent operation to their pre-fix state.  
**↪ Redo** re-applies them.

The undo/redo stacks persist for the lifetime of the session. Running a new fix clears the redo stack.

-----

## Diff Viewer

Each fix card has a **▸ log/diff** toggle. Expanding it shows:

- A live scrolling log of what the fix is doing
- A unified diff viewer that populates when the fix completes, with green-highlighted additions and red-highlighted removals
- A file dropdown when multiple files were changed, letting you inspect each one individually
- A `+N -N` line-change summary

-----

## Settings

|Setting             |Description                                                                                          |
|--------------------|-----------------------------------------------------------------------------------------------------|
|Color Theme         |8 built-in themes: Dark Blue, Midnight, Cyberpunk, Blood Red, Deep Purple, Hacker Green, Ocean, Amber|
|Accent Color        |Override any theme’s accent colour with a custom hex value                                           |
|Font Size           |8–16pt, affects all UI text                                                                          |
|UI Density          |Compact / Normal / Comfortable — scales padding throughout                                           |
|Card Style          |Default / Minimal / Outlined                                                                         |
|Custom Fonts        |Override title, body, and mono fonts individually                                                    |
|Animations          |Enable/disable toast slide and fade animations                                                       |
|Toast Duration      |1000–8000ms                                                                                          |
|Toast Position      |Bottom Right / Bottom Left / Top Right / Top Left                                                    |
|Compact Cards       |Reduces internal padding on fix cards                                                                |
|Auto-Detect Projects|Scans common Unity project locations on startup                                                      |
|Scan Depth          |1–5 folder levels deep when searching for projects                                                   |

Settings are saved to `~/.unity_tools_v2.json` and persist across sessions.

-----

## Project Detection

On startup (if Auto-Detect is enabled), Euphoria scans:

- `~/Documents/Unity`
- `~/Unity`
- `~/Desktop`
- `~/dev`, `~/projects`, `~/Projects`
- `C:/Users` (Windows only)

Up to 25 projects are shown in the picker. You can also browse manually to any folder that contains an `Assets/` subdirectory.

-----

## Notes

- All fixes operate directly on files in your project folder. There is no dry-run mode — use the undo stack if something goes wrong.
- The Missing Reference Fixer uses a minimum score of 1 to link a script. Very generic field names (`speed`, `name`) can occasionally cause a wrong match on small projects with many similar scripts.
- Shader and material patching uses regex on YAML. Non-standard or heavily nested YAML from unusual Unity versions may not be matched correctly.
- After any fix that touches `.mat` or scene/prefab files, Unity needs to reimport the changed assets before the fix takes effect in the editor.


# THIS IS IN DEV, EVERYTHING HERE WILL MOST LIKELY CHANGE
