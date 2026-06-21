param(
  [string]$Version = "",
  [string]$FullKitZip = "",
  [string]$DistDir = "",
  [string]$OutputExe = "",
  [switch]$RunSmoke,
  [switch]$KeepWorkDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PackageJson = Get-Content -LiteralPath (Join-Path $RepoRoot "package.json") -Raw | ConvertFrom-Json
if (-not $Version) { $Version = $PackageJson.version }
if (-not $DistDir) { $DistDir = Join-Path $RepoRoot "dist" }
if (-not $FullKitZip) { $FullKitZip = Join-Path $DistDir "DreamSeed-Code-$Version-Windows-Full.zip" }
if (-not $OutputExe) { $OutputExe = Join-Path $DistDir "DreamSeed-Code-$Version-Setup.exe" }

if (-not (Test-Path -LiteralPath $FullKitZip)) {
  throw "Full kit zip not found: $FullKitZip. Run scripts\build-windows-full-kit.ps1 first."
}

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Remove-Tree {
  param([string]$Path)
  if ($Path -and (Test-Path -LiteralPath $Path)) {
    Remove-Item -LiteralPath $Path -Recurse -Force
  }
}

function Resolve-CSharpCompiler {
  $candidates = @(
    (Join-Path $env:SystemRoot "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
    (Join-Path $env:SystemRoot "Microsoft.NET\Framework\v4.0.30319\csc.exe"),
    (Join-Path $env:SystemRoot "Microsoft.NET\Framework64\v3.5\csc.exe"),
    (Join-Path $env:SystemRoot "Microsoft.NET\Framework\v3.5\csc.exe")
  )
  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
  }
  $cmd = Get-Command csc.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  throw "C# compiler not found. Expected Windows .NET Framework csc.exe."
}

function Invoke-SetupSmoke {
  param([string]$ExePath)
  Write-Step "Running isolated Setup.exe smoke"
  $SmokeRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("dreamseed-setup-smoke-" + [guid]::NewGuid().ToString("N"))
  $env:DREAMSEED_SETUP_BASE = Join-Path $SmokeRoot "DreamSeedCode"
  $env:DREAMSEED_SETUP_INSTALL_ROOT = Join-Path $SmokeRoot "DreamSeed"
  $env:DREAMSEED_SETUP_NO_DESKTOP_SHORTCUT = "1"
  $env:DREAMSEED_SETUP_NO_PATH_UPDATE = "1"
  $env:DREAMSEED_SETUP_SILENT = "1"
  try {
    $proc = Start-Process -FilePath $ExePath -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
      throw "Setup.exe smoke failed with exit code $($proc.ExitCode)."
    }
    $DreamSeedCmd = Join-Path $env:DREAMSEED_SETUP_INSTALL_ROOT "bin\dreamseed.cmd"
    if (-not (Test-Path -LiteralPath $DreamSeedCmd)) {
      throw "Smoke install did not create dreamseed.cmd: $DreamSeedCmd"
    }
    & $DreamSeedCmd --help | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "Smoke dreamseed --help failed with exit code $LASTEXITCODE."
    }
    Write-Host "Setup.exe smoke passed." -ForegroundColor Green
  } finally {
    Remove-Item Env:\DREAMSEED_SETUP_BASE -ErrorAction SilentlyContinue
    Remove-Item Env:\DREAMSEED_SETUP_INSTALL_ROOT -ErrorAction SilentlyContinue
    Remove-Item Env:\DREAMSEED_SETUP_NO_DESKTOP_SHORTCUT -ErrorAction SilentlyContinue
    Remove-Item Env:\DREAMSEED_SETUP_NO_PATH_UPDATE -ErrorAction SilentlyContinue
    Remove-Item Env:\DREAMSEED_SETUP_SILENT -ErrorAction SilentlyContinue
    Remove-Tree $SmokeRoot
  }
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
$WorkDir = Join-Path ([System.IO.Path]::GetTempPath()) ("dreamseed-setup-build-" + [guid]::NewGuid().ToString("N"))
$ProgramCs = Join-Path $WorkDir "DreamSeedSetup.cs"
$Bootstrap = Join-Path $RepoRoot "scripts\setup-bootstrap.ps1"
$Compiler = Resolve-CSharpCompiler

try {
  Write-Step "Generating self-extracting installer source"
  New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
  $source = @'
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;

internal static class DreamSeedSetup
{
    private const string ZipResource = "DreamSeed.PayloadZip";
    private const string BootstrapResource = "DreamSeed.SetupBootstrap";

    private static int Main()
    {
        string tempDir = Path.Combine(Path.GetTempPath(), "dreamseed-setup-" + Guid.NewGuid().ToString("N"));
        try
        {
            Directory.CreateDirectory(tempDir);
            string zipPath = Path.Combine(tempDir, "DreamSeed-Code-Windows-Full.zip");
            string bootstrapPath = Path.Combine(tempDir, "setup-bootstrap.ps1");
            ExtractResource(ZipResource, zipPath);
            ExtractResource(BootstrapResource, bootstrapPath);

            string powershell = ResolvePowerShell();
            ProcessStartInfo info = new ProcessStartInfo();
            info.FileName = powershell;
            info.Arguments = "-NoProfile -ExecutionPolicy Bypass -File \"" + bootstrapPath + "\" -PackageZip \"" + zipPath + "\"";
            info.UseShellExecute = false;
            Process proc = Process.Start(info);
            proc.WaitForExit();
            int code = proc.ExitCode;
            if (code == 0)
            {
                Console.WriteLine();
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("DreamSeed Code setup completed.");
                Console.ResetColor();
            }
            else
            {
                Console.WriteLine();
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("DreamSeed Code setup failed with exit code " + code + ".");
                Console.ResetColor();
            }
            PauseIfInteractive();
            return code;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("DreamSeed Code setup failed: " + ex.Message);
            PauseIfInteractive();
            return 1;
        }
        finally
        {
            try { if (Directory.Exists(tempDir)) Directory.Delete(tempDir, true); } catch { }
        }
    }

    private static void ExtractResource(string name, string destination)
    {
        Assembly assembly = Assembly.GetExecutingAssembly();
        using (Stream input = assembly.GetManifestResourceStream(name))
        {
            if (input == null) throw new InvalidOperationException("Missing embedded resource: " + name);
            using (FileStream output = File.Create(destination))
            {
                input.CopyTo(output);
            }
        }
    }

    private static string ResolvePowerShell()
    {
        string root = Environment.GetEnvironmentVariable("SystemRoot");
        if (!String.IsNullOrEmpty(root))
        {
            string full = Path.Combine(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
            if (File.Exists(full)) return full;
        }
        return "powershell.exe";
    }

    private static void PauseIfInteractive()
    {
        if (String.Equals(Environment.GetEnvironmentVariable("DREAMSEED_SETUP_SILENT"), "1", StringComparison.OrdinalIgnoreCase)) return;
        Console.WriteLine("Press any key to close this installer.");
        try { Console.ReadKey(true); } catch { }
    }
}
'@
  Set-Content -LiteralPath $ProgramCs -Value $source -Encoding ASCII

  Write-Step "Compiling Setup.exe"
  if (Test-Path -LiteralPath $OutputExe) { Remove-Item -LiteralPath $OutputExe -Force }
  $args = @(
    "/nologo",
    "/target:exe",
    "/platform:x64",
    "/optimize+",
    "/out:$OutputExe",
    "/reference:System.IO.Compression.dll",
    "/reference:System.IO.Compression.FileSystem.dll",
    "/resource:$FullKitZip,DreamSeed.PayloadZip",
    "/resource:$Bootstrap,DreamSeed.SetupBootstrap",
    $ProgramCs
  )
  & $Compiler @args
  if ($LASTEXITCODE -ne 0) {
    throw "csc.exe failed with exit code $LASTEXITCODE."
  }
  if (-not (Test-Path -LiteralPath $OutputExe)) {
    throw "Setup.exe was not created: $OutputExe"
  }
  $exe = Get-Item -LiteralPath $OutputExe
  if ($exe.Length -lt 100MB) {
    throw "Setup.exe looks too small: $($exe.Length) bytes"
  }
  Write-Host "Setup.exe ready: $OutputExe" -ForegroundColor Green

  if ($RunSmoke) {
    Invoke-SetupSmoke -ExePath $OutputExe
  }
} finally {
  if ($KeepWorkDir) {
    Write-Host "Keeping setup work dir: $WorkDir" -ForegroundColor Yellow
  } else {
    Remove-Tree $WorkDir
  }
}
