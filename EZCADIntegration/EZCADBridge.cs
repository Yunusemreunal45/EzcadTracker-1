using System;
using System.IO;
using System.Text;
using System.Xml;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using System.Threading;

namespace EZCADBridge
{
    class Program
    {
        // Import MarkEzd.dll functions
        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_Initial(string strEzdFilePath, int nIsNewOrOpen);

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_Close();

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_SaveEntLibToFile(string strFileName);

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_MarkEntity(string strEntName);

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_Mark(bool bFlyMark);

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_GetEntityCount(ref int pEntCount);

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_GetEntityName(int nEntityIndex, StringBuilder pEntName);

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_SetEntityText(string strEntName, string strText);

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_GetEntityType(string strEntName, ref int nEntityType);

        [DllImport("MarkEzd.dll")]
        private static extern bool lmc1_RedLightPoint(double x, double y, bool bMachineCoord);

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_ReadPort(int nPort, ref int nValue);

        [DllImport("MarkEzd.dll")]
        private static extern int lmc1_WritePort(int nPort, int nValue);

        static void Main(string[] args)
        {
            try
            {
                // Print startup information
                Console.WriteLine("EZCAD Bridge Application Starting...");
                Console.WriteLine("Current Directory: " + Directory.GetCurrentDirectory());
                
                if (args.Length == 0)
                {
                    ShowHelp();
                    return;
                }

                string command = args[0].ToLower();
                
                switch (command)
                {
                    case "info":
                        ShowInfo();
                        break;
                    
                    case "open":
                        if (args.Length < 2)
                        {
                            Console.WriteLine("ERROR: Missing EZD file path. Usage: EZCADBridge open <ezd_file_path>");
                            return;
                        }
                        OpenEzdFile(args[1]);
                        break;
                    
                    case "mark":
                        HandleMarkCommand(args);
                        break;
                    
                    case "update":
                        HandleUpdateCommand(args);
                        break;
                    
                    case "list":
                        ListEntities();
                        break;
                    
                    case "red":
                        HandleRedCommand(args);
                        break;

                    case "save":
                        if (args.Length < 2)
                        {
                            Console.WriteLine("ERROR: Missing output file path. Usage: EZCADBridge save <output_file_path>");
                            return;
                        }
                        SaveEzdFile(args[1]);
                        break;

                    default:
                        Console.WriteLine($"ERROR: Unknown command '{command}'");
                        ShowHelp();
                        break;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"ERROR: {ex.Message}");
                Console.WriteLine($"Stack Trace: {ex.StackTrace}");
            }
            finally
            {
                // Clean up
                lmc1_Close();
            }
        }

        static void ShowHelp()
        {
            Console.WriteLine("EZCADBridge - Bridge application for EZCAD2 and MarkEzd.dll");
            Console.WriteLine("--------------------------------------------------------");
            Console.WriteLine("Usage:");
            Console.WriteLine("  EZCADBridge info                          - Display system information");
            Console.WriteLine("  EZCADBridge open <ezd_file_path>          - Open an EZD file");
            Console.WriteLine("  EZCADBridge mark                          - Execute marking");
            Console.WriteLine("  EZCADBridge mark <entity_name>            - Mark specific entity");
            Console.WriteLine("  EZCADBridge update <entity_name> <text>   - Update text for entity");
            Console.WriteLine("  EZCADBridge list                          - List all entities in current file");
            Console.WriteLine("  EZCADBridge red <x> <y>                   - Position red light pointer");
            Console.WriteLine("  EZCADBridge save <output_file_path>       - Save current document to file");
            Console.WriteLine();
            Console.WriteLine("Examples:");
            Console.WriteLine("  EZCADBridge open template.ezd");
            Console.WriteLine("  EZCADBridge update TextObject1 \"Serial: 12345\"");
            Console.WriteLine("  EZCADBridge mark");
            Console.WriteLine();
            Console.WriteLine("Note: MarkEzd.dll must be present in the application directory");
        }

        static void ShowInfo()
        {
            Console.WriteLine("System Information:");
            Console.WriteLine("-------------------");
            Console.WriteLine($"OS: {Environment.OSVersion}");
            Console.WriteLine($".NET Version: {Environment.Version}");
            Console.WriteLine($"64-bit OS: {Environment.Is64BitOperatingSystem}");
            Console.WriteLine($"64-bit Process: {Environment.Is64BitProcess}");
            Console.WriteLine($"Current Directory: {Directory.GetCurrentDirectory()}");
            
            // Check if MarkEzd.dll exists
            string dllPath = Path.Combine(Directory.GetCurrentDirectory(), "MarkEzd.dll");
            if (File.Exists(dllPath))
            {
                Console.WriteLine($"MarkEzd.dll: Found ({dllPath})");
                try
                {
                    FileInfo fileInfo = new FileInfo(dllPath);
                    Console.WriteLine($"  - Size: {fileInfo.Length:N0} bytes");
                    Console.WriteLine($"  - Created: {fileInfo.CreationTime}");
                    Console.WriteLine($"  - Last Modified: {fileInfo.LastWriteTime}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"  - Error getting file details: {ex.Message}");
                }
            }
            else
            {
                Console.WriteLine($"MarkEzd.dll: Not found at expected location ({dllPath})");
                
                // Try to find it in system paths
                string[] commonPaths = new string[]
                {
                    @"C:\Users\yunus\Desktop\Ezcad2.14.11(20230924)\EzCad2.exe",
                    @"C:\Program Files\EzCad2",
                    @"C:\Program Files (x86)\EzCad2"
                };
                
                foreach (string path in commonPaths)
                {
                    string testPath = Path.Combine(path, "MarkEzd.dll");
                    if (File.Exists(testPath))
                    {
                        Console.WriteLine($"MarkEzd.dll: Found at alternative location ({testPath})");
                        Console.WriteLine("  - Consider copying this file to the application directory");
                        break;
                    }
                }
            }
        }

        static void OpenEzdFile(string filePath)
        {
            if (!File.Exists(filePath))
            {
                Console.WriteLine($"ERROR: File not found - {filePath}");
                return;
            }
            
            Console.WriteLine($"Opening EZD file: {filePath}");
            int result = lmc1_Initial(filePath, 0); // 0 = open existing file
            
            if (result != 0)
            {
                Console.WriteLine($"ERROR: Failed to open file. Error code: {result}");
                return;
            }
            
            Console.WriteLine("File opened successfully.");
            
            // Display entity count
            int entityCount = 0;
            lmc1_GetEntityCount(ref entityCount);
            Console.WriteLine($"Entity count: {entityCount}");
        }

        static void HandleMarkCommand(string[] args)
        {
            if (args.Length > 1)
            {
                // Mark specific entity
                string entityName = args[1];
                Console.WriteLine($"Marking entity: {entityName}");
                int result = lmc1_MarkEntity(entityName);
                
                if (result != 0)
                {
                    Console.WriteLine($"ERROR: Failed to mark entity. Error code: {result}");
                    return;
                }
                
                Console.WriteLine("Entity marking completed.");
            }
            else
            {
                // Mark all
                Console.WriteLine("Executing marking process...");
                int result = lmc1_Mark(false); // false = not fly mark
                
                if (result != 0)
                {
                    Console.WriteLine($"ERROR: Failed to execute marking. Error code: {result}");
                    return;
                }
                
                Console.WriteLine("Marking completed.");
            }
        }

        static void HandleUpdateCommand(string[] args)
        {
            if (args.Length < 3)
            {
                Console.WriteLine("ERROR: Missing parameters. Usage: EZCADBridge update <entity_name> <text>");
                return;
            }
            
            string entityName = args[1];
            string newText = args[2];
            
            // Check if more text parts are provided (in case text contains spaces)
            if (args.Length > 3)
            {
                StringBuilder textBuilder = new StringBuilder(newText);
                for (int i = 3; i < args.Length; i++)
                {
                    textBuilder.Append(" ").Append(args[i]);
                }
                newText = textBuilder.ToString();
            }
            
            Console.WriteLine($"Updating entity: {entityName}");
            Console.WriteLine($"New text: {newText}");
            
            int entityType = 0;
            int result = lmc1_GetEntityType(entityName, ref entityType);
            
            if (result != 0)
            {
                Console.WriteLine($"ERROR: Entity not found or error getting entity type. Error code: {result}");
                return;
            }
            
            Console.WriteLine($"Entity type: {entityType}");
            
            result = lmc1_SetEntityText(entityName, newText);
            
            if (result != 0)
            {
                Console.WriteLine($"ERROR: Failed to update entity text. Error code: {result}");
                return;
            }
            
            Console.WriteLine("Entity updated successfully.");
        }

        static void ListEntities()
        {
            int entityCount = 0;
            int result = lmc1_GetEntityCount(ref entityCount);
            
            if (result != 0)
            {
                Console.WriteLine($"ERROR: Failed to get entity count. Error code: {result}");
                return;
            }
            
            Console.WriteLine($"Entity count: {entityCount}");
            
            if (entityCount == 0)
            {
                Console.WriteLine("No entities found. Make sure an EZD file is opened first.");
                return;
            }
            
            Console.WriteLine("Entities:");
            Console.WriteLine("----------");
            
            for (int i = 0; i < entityCount; i++)
            {
                StringBuilder nameBuilder = new StringBuilder(256);
                result = lmc1_GetEntityName(i, nameBuilder);
                
                if (result != 0)
                {
                    Console.WriteLine($"  [{i}] ERROR: Failed to get entity name. Error code: {result}");
                    continue;
                }
                
                string entityName = nameBuilder.ToString();
                int entityType = 0;
                lmc1_GetEntityType(entityName, ref entityType);
                
                Console.WriteLine($"  [{i}] {entityName} (Type: {entityType})");
            }
        }

        static void HandleRedCommand(string[] args)
        {
            if (args.Length < 3)
            {
                Console.WriteLine("ERROR: Missing parameters. Usage: EZCADBridge red <x> <y>");
                return;
            }
            
            if (!double.TryParse(args[1], out double x) || !double.TryParse(args[2], out double y))
            {
                Console.WriteLine("ERROR: Invalid coordinates. X and Y must be valid numbers.");
                return;
            }
            
            Console.WriteLine($"Positioning red light pointer at: X={x}, Y={y}");
            bool result = lmc1_RedLightPoint(x, y, false); // false = document coordinates (not machine coordinates)
            
            if (!result)
            {
                Console.WriteLine("ERROR: Failed to position red light pointer.");
                return;
            }
            
            Console.WriteLine("Red light positioned successfully.");
        }

        static void SaveEzdFile(string outputPath)
        {
            Console.WriteLine($"Saving to file: {outputPath}");
            int result = lmc1_SaveEntLibToFile(outputPath);
            
            if (result != 0)
            {
                Console.WriteLine($"ERROR: Failed to save file. Error code: {result}");
                return;
            }
            
            Console.WriteLine("File saved successfully.");
        }
    }
}