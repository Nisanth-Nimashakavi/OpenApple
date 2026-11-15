param([string]$Action, [string]$Payload = '')
$ErrorActionPreference = 'Stop'
$value = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Payload))
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class AppleWindows {
  public delegate bool Callback(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(Callback c, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder b, int n);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [StructLayout(LayoutKind.Sequential)] public struct KEY { public ushort vk, scan; public uint flags, time; public UIntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct MOUSE { public int x,y; public uint data,flags,time; public UIntPtr extra; }
  [StructLayout(LayoutKind.Explicit)] public struct UNION { [FieldOffset(0)] public KEY key; [FieldOffset(0)] public MOUSE mouse; }
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public UNION data; }
  [DllImport("user32.dll", SetLastError=true)] public static extern uint SendInput(uint n, INPUT[] inputs, int size);
  public static void Key(ushort code, bool unicode) {
    var inputs = new INPUT[2];
    for (int i=0;i<2;i++) { inputs[i].type=1; inputs[i].data.key.vk=unicode?(ushort)0:code; inputs[i].data.key.scan=unicode?code:(ushort)0; inputs[i].data.key.flags=(unicode?4u:0u)|(i==1?2u:0u); }
    if (SendInput(2,inputs,Marshal.SizeOf(typeof(INPUT))) != 2) throw new Exception("Windows blocked input delivery");
  }
}
'@
function Get-WindowRecord([IntPtr]$Handle) {
  [uint32]$processId = 0
  [void][AppleWindows]::GetWindowThreadProcessId($Handle, [ref]$processId)
  $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
  if (!$process) { return $null }
  $title = New-Object Text.StringBuilder 4096
  [void][AppleWindows]::GetWindowText($Handle, $title, 4096)
  return @{ address = $Handle.ToInt64().ToString(); pid = $processId; class = $process.ProcessName.ToLowerInvariant(); title = $title.ToString(); mapped = $true }
}
switch ($Action) {
  'active' { Get-WindowRecord ([AppleWindows]::GetForegroundWindow()) | ConvertTo-Json -Compress }
  'list' {
    $records = New-Object 'System.Collections.Generic.List[object]'
    $callback = [AppleWindows+Callback]{ param($handle, $unused)
      if ([AppleWindows]::IsWindowVisible($handle)) { $record = Get-WindowRecord $handle; if ($record) { $records.Add($record) } }
      return $true
    }
    [void][AppleWindows]::EnumWindows($callback, [IntPtr]::Zero)
    ConvertTo-Json -InputObject @($records.ToArray()) -Compress
  }
  'focus' {
    $target = $value | ConvertFrom-Json
    $handle = [IntPtr][long]$target.address
    [void][AppleWindows]::ShowWindow($handle, 9)
    if (![AppleWindows]::SetForegroundWindow($handle)) { throw 'Windows could not focus the selected terminal' }
  }
  'type' { foreach ($character in $value.ToCharArray()) { [AppleWindows]::Key([uint16]$character, $true) } }
  'enter' { [AppleWindows]::Key(13, $false) }
  default { throw 'Unknown delivery action' }
}
