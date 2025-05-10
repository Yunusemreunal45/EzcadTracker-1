# Building the C# Bridge Application

This guide explains how to build the C# Bridge application that interfaces with EZCAD2's MarkEzd.dll.

## Prerequisites

- Windows operating system
- Visual Studio (2019 or newer) or Visual Studio Build Tools
- .NET Framework 4.8 SDK
- EZCAD2 software installed

## Build Steps

1. Open a command prompt as administrator
2. Navigate to the EZCADIntegration directory
3. Use the following command to build the project:

```
dotnet build -c Release
```

Alternatively, you can open the project in Visual Studio and build it from there.

## Installation

After building, you need to copy the MarkEzd.dll file from your EZCAD2 installation directory to the bridge application's output directory.

1. Locate the EZCADBridge.exe in the `bin\Release\net48` directory
2. Copy the MarkEzd.dll file from your EZCAD2 installation directory (typically `C:\EzCad2`) to the same directory as EZCADBridge.exe

## Testing the Bridge

To verify the bridge is working correctly:

1. Open a command prompt
2. Navigate to the directory containing EZCADBridge.exe
3. Run the following command:

```
EZCADBridge.exe info
```

You should see system information and confirmation that MarkEzd.dll was found.

## Troubleshooting

If you encounter issues:

1. Ensure MarkEzd.dll is in the same directory as EZCADBridge.exe
2. Make sure you're using the correct version of .NET Framework (4.8)
3. Check if EZCAD2 is properly installed and working
4. Run the bridge application in debug mode to get more detailed error information

## Bridge Commands

The bridge supports the following commands:

- `info` - Display system information and status
- `open <ezd_file>` - Open an EZD template file
- `list` - List all entities in the current template
- `update <entity> <text>` - Update the text of an entity
- `mark` - Execute marking for all entities
- `mark <entity>` - Mark a specific entity
- `red <x> <y>` - Position the red light pointer
- `save <output_file>` - Save the current template to a new file