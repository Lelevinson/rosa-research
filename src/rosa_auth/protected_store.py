"""Optional Windows-current-user DPAPI storage, usable from Windows or WSL.

No secrets in argv, environment, logs, exceptions or source files. A private pipe
carries records to an owned helper. A Windows named mutex leases the profile for
the entire helper lifetime, including token refresh, across WSL processes.
"""
import base64
import json
import os
import queue
import re
import shutil
import subprocess
import threading

from .oauth import SafeError


_HELPER = r'''
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Security
$lease = $null
$held = $false
try {
    $hello = [Console]::ReadLine() | ConvertFrom-Json
    $storeName = [string]$hello.profile
    if ($storeName -notmatch '\A[a-zA-Z0-9_-]{1,48}\z') { throw 'invalid_profile' }
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $lease = New-Object Threading.Mutex($false, ('Local\ROSAResearchOAuth_' + $sid.Value + '_' + $storeName))
    try { $held = $lease.WaitOne(0) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) {
        [Console]::WriteLine('{"ok":false,"code":"credential_profile_in_use"}')
        exit 2
    }
    $storeDir = Join-Path $env:LOCALAPPDATA 'ROSAResearch\OAuth'
    [IO.Directory]::CreateDirectory($storeDir) | Out-Null
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner($sid)
    $inheritance = [Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'
    foreach ($principal in @($sid, (New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))) {
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($principal, 'FullControl', $inheritance, 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    [IO.Directory]::SetAccessControl($storeDir, $acl)
    $storePath = Join-Path $storeDir ($storeName + '.dpapi')
    [Console]::WriteLine('{"ok":true}')
    while ($null -ne ($line = [Console]::ReadLine())) {
        $request = $line | ConvertFrom-Json
        switch ([string]$request.op) {
            'load' {
                if (-not [IO.File]::Exists($storePath)) {
                    [Console]::WriteLine('{"ok":true,"record":null}')
                } else {
                    $plain = [Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($storePath), $null, 'CurrentUser')
                    try {
                        $record = [Text.Encoding]::UTF8.GetString($plain) | ConvertFrom-Json
                        [Console]::WriteLine((@{ok=$true; record=$record} | ConvertTo-Json -Compress -Depth 12))
                    } finally { [Array]::Clear($plain, 0, $plain.Length) }
                }
            }
            'save' {
                $plain = [Text.Encoding]::UTF8.GetBytes(($request.record | ConvertTo-Json -Compress -Depth 12))
                try { $encrypted = [Security.Cryptography.ProtectedData]::Protect($plain, $null, 'CurrentUser') }
                finally { [Array]::Clear($plain, 0, $plain.Length) }
                $temporary = Join-Path $storeDir ($storeName + '.' + [Guid]::NewGuid().ToString('N') + '.tmp')
                try {
                    [IO.File]::WriteAllBytes($temporary, $encrypted)
                    if ([IO.File]::Exists($storePath)) {
                        # PowerShell's binder turns the third $null into an empty
                        # backup path. Reflection preserves a true CLR null, so
                        # replacement stays atomic without a credential backup.
                        $replace = [IO.File].GetMethod('Replace', [type[]]@([string], [string], [string]))
                        $replace.Invoke($null, [object[]]@([string]$temporary, [string]$storePath, $null))
                    }
                    else { [IO.File]::Move($temporary, $storePath) }
                } finally { if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) } }
                [Console]::WriteLine('{"ok":true}')
            }
            'delete' {
                if ([IO.File]::Exists($storePath)) { [IO.File]::Delete($storePath) }
                [Console]::WriteLine('{"ok":true}')
            }
            'close' { [Console]::WriteLine('{"ok":true}'); exit 0 }
            default { throw 'unsupported_operation' }
        }
        $request = $null
        $line = $null
        $record = $null
    }
} catch {
    [Console]::WriteLine('{"ok":false,"code":"protected_storage_failure"}')
    exit 1
} finally {
    if ($held) { $lease.ReleaseMutex() }
    if ($null -ne $lease) { $lease.Dispose() }
}
'''


class WindowsCredentialStore:
    """Encrypted per-user local storage; no plaintext fallback, no credentials repr."""

    def __init__(self, profile='research'):
        if not isinstance(profile, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', profile):
            raise ValueError('invalid_credential_profile')
        executable = shutil.which('powershell.exe')
        if executable is None:
            raise SafeError('windows_protected_storage_unavailable')
        self.profile = profile
        self._responses = queue.Queue()
        encoded = base64.b64encode(_HELPER.encode('utf-16le')).decode('ascii')
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        self._child = subprocess.Popen([executable, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=flags)
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        try:
            self._request({'profile': profile})
        except BaseException:
            self.close()
            raise

    def __repr__(self):
        return '<WindowsCredentialStore protected local profile>'

    def _read_loop(self):
        for line in self._child.stdout:
            self._responses.put(line)
        self._responses.put(None)

    def _request(self, request):
        try:
            self._child.stdin.write((json.dumps(request) + '\n').encode('utf-8'))
            self._child.stdin.flush()
            line = self._responses.get(timeout=30)
            if line is None:
                raise SafeError('protected_storage_unavailable')
            response = json.loads(line)
        except (OSError, ValueError, queue.Empty):
            raise SafeError('protected_storage_unavailable') from None
        if response.get('ok') is not True:
            code = response.get('code')
            raise SafeError(code if code in ('credential_profile_in_use', 'protected_storage_failure')
                            else 'protected_storage_failure')
        return response

    def load(self):
        return self._request({'op': 'load'}).get('record')

    def save(self, record):
        self._request({'op': 'save', 'record': record})

    def delete(self):
        self._request({'op': 'delete'})

    def close(self):
        if self._child.poll() is None:
            try:
                self._request({'op': 'close'})
                self._child.wait(3)
            except (SafeError, OSError, subprocess.TimeoutExpired):
                self._child.terminate()
                try: self._child.wait(3)
                except subprocess.TimeoutExpired:
                    self._child.kill()
                    self._child.wait(3)
        for stream in (self._child.stdin, self._child.stdout):
            if stream:
                try: stream.close()
                except OSError: pass  # Do not mask the original safe storage error.

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
