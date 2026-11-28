# prints "x,y,w,h" of the visible window whose title contains "Gazebo Sim" (Windows only)
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W { public delegate bool CB(IntPtr h, IntPtr l);
 [StructLayout(LayoutKind.Sequential)] public struct R { public int L, T, Rt, B; }
 [DllImport("user32.dll")] static extern bool EnumWindows(CB cb, IntPtr l);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out R r);
 public static string Find() { string o = ""; EnumWindows((h, l) => { var s = new StringBuilder(256); GetWindowText(h, s, 256);
   if (IsWindowVisible(h) && s.ToString().Contains("Gazebo Sim")) { R r; GetWindowRect(h, out r); o += r.L + "," + r.T + "," + (r.Rt - r.L) + "," + (r.B - r.T) + ";"; } return true; }, IntPtr.Zero); return o; } }
"@
[W]::Find()
