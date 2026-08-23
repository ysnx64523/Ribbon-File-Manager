# macOS packaging (Homebrew)

RibbonFM can be run from a Homebrew-installed Python + GTK3 environment, or
bundled into an `.app` with `py2app`.

## Run from Homebrew

```sh
brew install python gtk+3 pygobject3 adwaita-icon-theme
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
# Build the .mo translation files before first run:
python tools/gen_po.py
ribbonfm
```

## TCC / sandbox considerations

macOS restricts access to Desktop, Documents, Downloads and the sandboxed
container. RibbonFM requests those folders via the standard **system
authorization** dialog, which surfaces automatically when the user tries to
open them, and it stores preferences under `~/Library/Application Support/`.

## Authorization Services

Actions that need elevation are performed via an `osascript` / Authorization
Services prompt, **not** by running the app as root:

```python
# core/perm.py -> IS_MACOS path
# see the shared _escalate_tokens() contract.
```

A minimal implementation is provided by the platform-independent contract in
`ribbonfm/core/perm.py`; a full macOS backend uses
`AuthorizationCreate`/`AuthorizationExecuteWithPrivileges` (deprecated) or,
preferably, SMAppService / a privileged XPC helper.

## Bundling with py2app

```sh
pip install py2app
```

Use the launcher stub in `pack/macos/app_launcher.py` together with the console
script defined in `pyproject.toml`. Bundle metadata (bundle id, icons, signing)
is configured via the `py2app` options in `setup.cfg` or a small `setup.py`
that only declares the ``app`` entry; codesigning identities go in `Info.plist`.

The application icon and desktop metadata live in `data/` and are shared with
the Flatpak/AppImage builds.
