# Viewer helper: keep the Gazebo GUI window on top (so a desktop recording shows it) and write its rectangle to rect.txt. Does not touch the simulation.
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r); public struct RECT { public int L, T, R, B; } }
"@
$out = $args[0]
for ($i = 0; $i -lt 400; $i++) {
  $p = Get-Process msrdc -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*Gazebo Sim*' } | Select-Object -First 1
  if ($p -and $p.MainWindowHandle -ne 0) {
    [W]::SetWindowPos($p.MainWindowHandle, [IntPtr](-1), 0, 0, 0, 0, 0x0043) | Out-Null
    Start-Sleep -Milliseconds 500
    $r = New-Object W+RECT; [W]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null
    "$($r.L),$($r.T),$($r.R - $r.L),$($r.B - $r.T)" | Set-Content $out
    break
  }
  Start-Sleep -Milliseconds 500
}
