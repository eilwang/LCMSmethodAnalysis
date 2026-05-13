using System;
using System.IO;
using ThermoFisher.CommonCore.Data;
using ThermoFisher.CommonCore.Data.Business;
using ThermoFisher.CommonCore.Data.Interfaces;
using ThermoFisher.CommonCore.RawFileReader;

class Program
{
    static Device[] KnownDevices = new Device[]{
        Device.MS, Device.MSAnalog, Device.Analog, Device.UV, Device.Pda, Device.Other
    };

    static void Main(string[] args)
    {
        string rawFilePath = args[0];
        string filterTerm = args.Length > 1 ? args[1].ToLower() : "pump pressure";

        var rawFile = RawFileReaderAdapter.FileFactory(rawFilePath);

        // ── Method extraction mode ────────────────────────────────────────────
        if (filterTerm == "~method~")
        {
            foreach (Device dev in KnownDevices)
            {
                int count;
                try { count = rawFile.GetInstrumentCountOfType(dev); }
                catch { continue; }

                for (int inst = 1; inst <= count; inst++)
                {
                    try { rawFile.SelectInstrument(dev, inst); }
                    catch { continue; }

                    HeaderItem[] headers;
                    int entryCount;
                    try
                    {
                        headers = rawFile.GetStatusLogHeaderInformation();
                        entryCount = rawFile.GetStatusLogEntriesCount();
                    }
                    catch { continue; }

                    bool hasGradient = false;
                    for (int i = 0; i < headers.Length; i++)
                        if (headers[i].Label.ToLower().Contains("gradient")) { hasGradient = true; break; }
                    if (!hasGradient) continue;

                    // Output header
                    Console.Write("entry_rt");
                    for (int i = 0; i < headers.Length; i++)
                        Console.Write("," + headers[i].Label);
                    Console.WriteLine();

                    // Output all rows
                    for (int i = 0; i < entryCount; i++)
                    {
                        var vals = rawFile.GetStatusLogValues(i, false);
                        Console.Write(vals.RetentionTime.ToString("G10"));
                        for (int j = 0; j < headers.Length; j++)
                            Console.Write("," + (vals.Values[j] ?? ""));
                        Console.WriteLine();
                    }
                    return;
                }
            }
            Console.Error.WriteLine("NO_METHOD_DATA");
            return;
        }

        // Scan all device/instrument combinations for matching status log columns
        bool found = false;
        foreach (Device dev in KnownDevices)
        {
            int count;
            try { count = rawFile.GetInstrumentCountOfType(dev); }
            catch { continue; }

            for (int inst = 1; inst <= count; inst++)
            {
                try { rawFile.SelectInstrument(dev, inst); }
                catch { continue; }

                HeaderItem[] headers;
                int entryCount;
                try
                {
                    headers = rawFile.GetStatusLogHeaderInformation();
                    entryCount = rawFile.GetStatusLogEntriesCount();
                }
                catch { continue; }

                Console.Error.WriteLine($"device={dev} inst={inst} entries={entryCount} cols={headers.Length}");

                var matchIdx = new System.Collections.Generic.List<int>();
                var matchNames = new System.Collections.Generic.List<string>();
                for (int i = 0; i < headers.Length; i++)
                {
                    Console.Error.WriteLine($"  col[{i}]: {headers[i].Label}");
                    if (headers[i].Label.ToLower().Contains(filterTerm))
                    {
                        matchIdx.Add(i);
                        matchNames.Add(headers[i].Label);
                    }
                }

                if (matchIdx.Count == 0) continue;

                Console.Error.WriteLine($"  >>> Found {matchIdx.Count} matching columns");

                if (!found)
                {
                    found = true;
                    Console.Write("time_minutes");
                    foreach (var name in matchNames)
                        Console.Write("," + name);
                    Console.WriteLine();

                    for (int i = 0; i < entryCount; i++)
                    {
                        var vals = rawFile.GetStatusLogValues(i, false);
                        double rt = vals.RetentionTime;
                        Console.Write(rt.ToString("G10"));
                        foreach (var idx in matchIdx)
                            Console.Write("," + (vals.Values[idx] ?? ""));
                        Console.WriteLine();
                    }
                }
            }
        }

        if (!found)
            Console.Error.WriteLine($"NO_MATCH for '{filterTerm}'");
    }
}
