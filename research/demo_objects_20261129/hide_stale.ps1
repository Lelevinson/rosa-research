# Hide leftover (dead) Gazebo Sim windows from earlier viewer runs so a new viewer window is the visible one. Windows only; no effect on the simulation.
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public class E { public delegate bool CB(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] static extern bool EnumWindows(CB cb, IntPtr l);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int c);
 [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
 public static int Hide() { int n = 0; EnumWindows((h, l) => { var s = new StringBuilder(256); GetWindowText(h, s, 256);
   if (s.ToString().Contains("Gazebo Sim")) { SetWindowPos(h, (IntPtr)(-2), 0, 0, 0, 0, 0x0043); ShowWindow(h, 0); n++; } return true; }, IntPtr.Zero); return n; } }
"@
"hidden: " + [E]::Hide()
