// Launcher do pacote da Microsoft Store: o MSIX precisa de um .exe por
// entrada (menu Iniciar, StartupTask, alias do terminal) e não passa
// argumentos fixos. O build.ps1 compila este arquivo três vezes, com o
// csc.exe do .NET Framework (vem em todo Windows):
//
//   Mexerica.exe         pythonw -X utf8 -m mexerica ARGS...
//   MexericaService.exe  pythonw -X utf8 -m mexerica daemon (/define:SERVICE)
//   mexerica-cli.exe     python  -X utf8 -m mexerica ARGS... (/define:CONSOLE,
//                        espera e devolve o código de saída)
//
// O Python fica na mesma pasta (runtime\bin) e acha o pacote mexerica no
// próprio site-packages.
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

static class Launcher
{
    [DllImport("user32.dll")]
    static extern bool AllowSetForegroundWindow(int pid);

    // subcomandos do __main__.py; outro primeiro argumento é um arquivo
    // ("Abrir com" do Explorer), que vira "open ARQUIVO"
    static readonly string[] Commands = { "open", "daemon", "list", "run", "doctor" };

    static int Main(string[] args)
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
#if CONSOLE
        string python = Path.Combine(dir, "python.exe");
#else
        string python = Path.Combine(dir, "pythonw.exe");
#endif
        var line = new StringBuilder("-X utf8 -m mexerica");
#if SERVICE
        line.Append(" daemon");
#elif !CONSOLE
        if (args.Length > 0 && !args[0].StartsWith("-")
                && Array.IndexOf(Commands, args[0]) < 0)
            line.Append(" open");
#endif
        foreach (string arg in args)
            line.Append(' ').Append(Quote(arg));

        var info = new ProcessStartInfo(python, line.ToString());
        info.UseShellExecute = false;
#if SERVICE
        info.EnvironmentVariables["MEXERICA_STARTUP"] = "1";
#endif
        Process child = Process.Start(info);
#if CONSOLE
        child.WaitForExit();
        return child.ExitCode;
#else
        // o Explorer deu o foco a este processo; o Python herda
        AllowSetForegroundWindow(child.Id);
        return 0;
#endif
    }

    // regra do CommandLineToArgvW: aspas em volta e barras antes de aspas dobradas
    static string Quote(string arg)
    {
        if (arg.Length > 0 && arg.IndexOfAny(new[] { ' ', '\t', '"' }) < 0)
            return arg;
        var sb = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in arg)
        {
            if (c == '\\') { slashes++; continue; }
            sb.Append('\\', c == '"' ? slashes * 2 + 1 : slashes);
            slashes = 0;
            sb.Append(c);
        }
        sb.Append('\\', slashes * 2).Append('"');
        return sb.ToString();
    }
}
