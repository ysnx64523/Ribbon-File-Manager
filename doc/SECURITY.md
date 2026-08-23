# Security, permissions and privilege escalation

This document describes how RibbonFM deals with file permissions and how it
elevates privileges. **It is also the authoritative statement of the app's
security model.**

## Guiding principle

> The application **never** runs with elevated privileges.

RibbonFM is a regular user process. Everything it can do must be possible with the
current user's rights. When an operation needs more (writing a protected path,
changing ownership, mounting, deleting system files), the app asks the OS secure
mechanism to perform **that single action** and immediately returns to
unprivileged execution.

## The permission module

All permission logic is isolated in [`ribbonfm/core/perm.py`](../src/ribbonfm/core/perm.py):

* `is_root()` – is the current process root? (never true in normal operation).
* `is_admin()` – does the process hold administrator/high-integrity rights
  (Windows) or euid 0 (Linux/macOS)?
* `inspect(path)` – returns a `PermHint` with the POSIX mode (`rwx`, octal),
  owner, group, writability and a machine-readable reason. It never raises.
* `can_no_privilege(path)` – can the current user write without elevation?
* `chmod(path, mode)` / `chown(path, uid, gid)` – try directly, then escalate via
  `pkexec` (Linux), UAC `runas` helper (Windows) or Authorization Services
  (macOS) through the common `_escalate_tokens()` contract.

### Why `777` is allowed

A directory with mode `777` (world-writable) is **not refused**. The user may
legitimately want it (e.g. a public share). RibbonFM performs the operation if
the filesystem permits it, but shows a **security warning** in the properties
dialog (`PermHint.is_777` and `PermHint.warning`).

### Unreadable / read-only locations

* A read-only mount is detected via `inspect()` / writability checks and the
  status bar shows **"Read only"**; destructive ribbon actions are still shown
  but will present a clear error if they are not permitted.
* Opening a folder without read permission shows a friendly `Gtk.MessageDialog`
  instead of a crash.

## Linux escalation (`pkexec`)

Privileged operations run a *controlled* command line through **pkexec**:

```python
_escalate_tokens(["/bin/chmod", "755", "/path"])
```

Security measures:

* Token list is passed directly (**no shell**), so paths cannot inject commands.
* The target is canonicalized with `os.path.realpath()` **before** use.
* The helper is `/bin/chmod`, `/bin/chown`, `/bin/touch` — no arbitrary programs.
* Timeout (120 s) and return code handling translate to friendly messages.
* Authentication cancellations and rejections are detected and explained.

### Known limitation

`pkexec` **cannot double-fork**; a long-running privileged process (e.g. a mount
daemon) is out of scope. This module is strictly for short, well-scoped actions.

## Windows escalation (UAC)

The app triggers the UAC prompt with the `runas` verb via `ShellExecuteW`. The
privileged helper [`pack/windows/runas_helper.py`](../pack/windows/runas_helper.py)
performs **one** action and exits, so the privilege is not retained.

## macOS

macOS integrates with the TCC privacy model for Desktop/Documents/Downloads and
uses Authorization Services / `osascript` for elevation. The contract is stubbed
in `perm.py`; a production backend should use SMAppService or a signed privileged
XPC helper rather than the deprecated
`AuthorizationExecuteWithPrivileges`.

## Threat considerations

* The interpreter and helper are invoked as **argument lists**, never through
  `shell=True`, preventing shell injection from file/path contents.
* No secrets are read or logged. The log domain `ribbonfm` only records errors.
* Elevation prompts are tied to the specific pending operation, not automatic.
* The app is *not* installed setuid/setgid and does not request `sudo`.

## Reporting

Security issues should be reported privately to the project maintainers. When
overprivilege is unavoidable, prefer a dedicated privileged helper (DBus service)
over `pkexec`/`runas`.
