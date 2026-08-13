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

        // ── DateTime extraction mode ──────────────────────────────────────────
        if (filterTerm == "~datetime~")
        {
            bool success = false;
            foreach (Device dev in KnownDevices)
            {
                int count;
                try { count = rawFile.GetInstrumentCountOfType(dev); }
                catch { continue; }

                for (int inst = 1; inst <= count; inst++)
                {
                    try
                    {
                        rawFile.SelectInstrument(dev, inst);
                        
                        string creationDate = "N/A";
                        string startTime = "N/A";
                        string endTime = "N/A";
                        
                        // Get creation date
                        try
                        {
                            if (rawFile.CreationDate != DateTime.MinValue)
                                creationDate = rawFile.CreationDate.ToString("yyyy-MM-dd HH:mm:ss");
                        }
                        catch { }
                        
                        // Try RunHeaderEx times (these are doubles representing minutes from start)
                        try
                        {
                            if (rawFile.RunHeaderEx != null)
                            {
                                double startTimeMinutes = rawFile.RunHeaderEx.StartTime;
                                double endTimeMinutes = rawFile.RunHeaderEx.EndTime;
                                
                                if (startTimeMinutes > 0)
                                    startTime = rawFile.CreationDate.AddMinutes(startTimeMinutes).ToString("yyyy-MM-dd HH:mm:ss");
                                if (endTimeMinutes > 0)
                                    endTime = rawFile.CreationDate.AddMinutes(endTimeMinutes).ToString("yyyy-MM-dd HH:mm:ss");
                            }
                        }
                        catch { }
                        
                        // Alternative: try to get start/end from status log timestamps
                        if (startTime == "N/A" || endTime == "N/A")
                        {
                            try
                            {
                                int entryCount = rawFile.GetStatusLogEntriesCount();
                                if (entryCount > 0)
                                {
                                    // Get first entry time
                                    var firstEntry = rawFile.GetStatusLogValues(0, false);
                                    if (firstEntry != null && startTime == "N/A")
                                    {
                                        // Start time = creation date + first retention time (in minutes)
                                        startTime = rawFile.CreationDate.AddMinutes(firstEntry.RetentionTime).ToString("yyyy-MM-dd HH:mm:ss");
                                    }
                                    
                                    // Get last entry time
                                    var lastEntry = rawFile.GetStatusLogValues(entryCount - 1, false);
                                    if (lastEntry != null && endTime == "N/A")
                                    {
                                        // End time = creation date + last retention time (in minutes)
                                        endTime = rawFile.CreationDate.AddMinutes(lastEntry.RetentionTime).ToString("yyyy-MM-dd HH:mm:ss");
                                    }
                                }
                            }
                            catch { }
                        }
                        
                        Console.WriteLine("creation_date,start_time,end_time");
                        Console.WriteLine($"{creationDate},{startTime},{endTime}");
                        success = true;
                        break;
                    }
                    catch { continue; }
                }
                if (success) break;
            }
            
            if (!success)
            {
                Console.Error.WriteLine("ERROR: Could not extract datetime from any device");
            }
            return;
        }

        // ── Status Log extraction mode ────────────────────────────────────────
        if (filterTerm == "~statuslog~")
        {
            // Collect status logs from ALL devices/instruments, not just the first one
            var allEntries = new System.Collections.Generic.List<string>();
            var allHeaders = new System.Collections.Generic.HashSet<string>();
            bool foundAny = false;
            
            // First pass: collect all unique column headers
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

                    if (entryCount == 0) continue;
                    
                    for (int i = 0; i < headers.Length; i++)
                        allHeaders.Add(headers[i].Label.Replace(",", ";"));
                    
                    foundAny = true;
                }
            }
            
            if (!foundAny)
            {
                Console.Error.WriteLine("ERROR: Could not extract status log from any device");
                return;
            }
            
            // Create ordered list of headers
            var orderedHeaders = new System.Collections.Generic.List<string>(allHeaders);
            orderedHeaders.Sort();
            
            // Output header
            Console.Write("device,instrument,timestamp,retention_time_min");
            foreach (var h in orderedHeaders)
                Console.Write("," + h);
            Console.WriteLine();
            
            // Second pass: collect all entries from all devices
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

                    if (entryCount == 0) continue;
                    
                    // Create mapping of header label to index
                    var headerMap = new System.Collections.Generic.Dictionary<string, int>();
                    for (int i = 0; i < headers.Length; i++)
                        headerMap[headers[i].Label.Replace(",", ";")] = i;
                    
                    // Output all entries for this device/instrument
                    for (int i = 0; i < entryCount; i++)
                    {
                        var vals = rawFile.GetStatusLogValues(i, false);
                        
                        // Calculate timestamp = creation date + retention time
                        DateTime entryTimestamp = rawFile.CreationDate.AddMinutes(vals.RetentionTime);
                        
                        Console.Write(dev.ToString());
                        Console.Write("," + inst);
                        Console.Write("," + entryTimestamp.ToString("yyyy-MM-dd HH:mm:ss"));
                        Console.Write("," + vals.RetentionTime.ToString("G10"));
                        
                        // Output values for all headers (in sorted order)
                        foreach (var h in orderedHeaders)
                        {
                            string value = "";
                            if (headerMap.ContainsKey(h))
                            {
                                int idx = headerMap[h];
                                value = vals.Values[idx]?.ToString() ?? "";
                            }
                            // Properly escape CSV: quote if contains comma, quote, or newline
                            if (value.Contains(",") || value.Contains("\"") || value.Contains("\n") || value.Contains("\r"))
                            {
                                value = "\"" + value.Replace("\"", "\"\"") + "\"";
                            }
                            Console.Write("," + value);
                        }
                        Console.WriteLine();
                    }
                }
            }
            
            return;
        }

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
