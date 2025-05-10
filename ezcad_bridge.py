#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EZCAD Bridge Module

This module provides an interface between Python and EZCAD2 through a C# bridge
application. It handles communication with the bridge application to manage
EZCAD2 functionality like opening ezd files, updating text entities, and
triggering laser marking operations.
"""

import os
import sys
import subprocess
import logging
import tempfile
import shutil
import time
from pathlib import Path

class EZCADBridge:
    """Bridge for communicating with EZCAD2 via C# bridge application"""
    
    def __init__(self, bridge_exe_path=None, logger=None):
        """
        Initialize the EZCAD Bridge
        
        Args:
            bridge_exe_path: Path to the EZCADBridge.exe application
                          If None, it will be searched in standard locations
            logger: Logger instance, if None a new one will be created
        """
        self.logger = logger or logging.getLogger('EZCADAutomation.Bridge')
        
        # Find bridge executable
        if bridge_exe_path is None:
            # Default locations to look for the bridge executable
            current_dir = os.path.dirname(os.path.abspath(__file__))
            possible_locations = [
                os.path.join(current_dir, "EZCADIntegration", "bin", "Release", "EZCADBridge.exe"),
                os.path.join(current_dir, "EZCADIntegration", "bin", "Debug", "EZCADBridge.exe"),
                os.path.join(current_dir, "EZCADBridge.exe"),
            ]
            
            for location in possible_locations:
                if os.path.exists(location):
                    bridge_exe_path = location
                    break
                    
            if bridge_exe_path is None:
                self.logger.error("EZCADBridge.exe not found in standard locations")
                raise FileNotFoundError("EZCADBridge.exe not found. Please build the C# bridge application or specify the path.")
        
        self.bridge_exe_path = bridge_exe_path
        self.logger.info(f"Using bridge executable at: {self.bridge_exe_path}")
        
        # Check if EZCAD bridge exists
        if not os.path.exists(self.bridge_exe_path):
            self.logger.error(f"Bridge executable not found at: {self.bridge_exe_path}")
            raise FileNotFoundError(f"Bridge executable not found at: {self.bridge_exe_path}")
        
        # Verify bridge directory has the required DLL
        bridge_dir = os.path.dirname(self.bridge_exe_path)
        dll_path = os.path.join(bridge_dir, "MarkEzd.dll")
        if not os.path.exists(dll_path):
            self.logger.warning(f"MarkEzd.dll not found at: {dll_path}")
            self.logger.warning("The bridge may not function correctly without this DLL")
        
        # Current ezd file
        self.current_ezd_file = None
    
    def get_bridge_info(self):
        """
        Get information about the bridge environment
        
        Returns:
            dict: Bridge information
        """
        result = self._run_bridge_command(["info"])
        return result
    
    def open_ezd_file(self, ezd_file_path):
        """
        Open an EZD file in EZCAD
        
        Args:
            ezd_file_path: Path to the EZD file
            
        Returns:
            bool: Success state
        """
        if not os.path.exists(ezd_file_path):
            self.logger.error(f"EZD file not found: {ezd_file_path}")
            return False
            
        self.logger.info(f"Opening EZD file: {ezd_file_path}")
        result = self._run_bridge_command(["open", ezd_file_path])
        
        if "successfully" in result.get("output", "").lower():
            self.current_ezd_file = ezd_file_path
            return True
        return False
    
    def update_text(self, entity_name, new_text):
        """
        Update the text of an entity in the current EZD file
        
        Args:
            entity_name: Name of the entity to update
            new_text: New text to set
            
        Returns:
            bool: Success state
        """
        if self.current_ezd_file is None:
            self.logger.error("No EZD file currently open")
            return False
            
        self.logger.info(f"Updating entity '{entity_name}' with text: {new_text}")
        result = self._run_bridge_command(["update", entity_name, new_text])
        
        if "updated successfully" in result.get("output", "").lower():
            return True
        return False
    
    def mark(self, entity_name=None):
        """
        Execute the marking process
        
        Args:
            entity_name: Optional name of entity to mark. If None, all entities are marked
            
        Returns:
            bool: Success state
        """
        if self.current_ezd_file is None:
            self.logger.error("No EZD file currently open")
            return False
            
        if entity_name:
            self.logger.info(f"Marking entity: {entity_name}")
            command = ["mark", entity_name]
        else:
            self.logger.info("Executing marking process for all entities")
            command = ["mark"]
            
        result = self._run_bridge_command(command)
        
        if "completed" in result.get("output", "").lower():
            return True
        return False
    
    def red_light(self, x, y):
        """
        Position the red light pointer
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            bool: Success state
        """
        if self.current_ezd_file is None:
            self.logger.error("No EZD file currently open")
            return False
            
        self.logger.info(f"Positioning red light at ({x}, {y})")
        result = self._run_bridge_command(["red", str(x), str(y)])
        
        if "positioned successfully" in result.get("output", "").lower():
            return True
        return False
    
    def list_entities(self):
        """
        List all entities in the current EZD file
        
        Returns:
            list: List of entity names or empty list if none or error
        """
        if self.current_ezd_file is None:
            self.logger.error("No EZD file currently open")
            return []
            
        self.logger.info("Listing entities in current EZD file")
        result = self._run_bridge_command(["list"])
        
        entities = []
        for line in result.get("output", "").splitlines():
            line = line.strip()
            if line.startswith("[") and "]" in line:
                # Extract entity name
                parts = line.split("]", 1)
                if len(parts) > 1:
                    entity_info = parts[1].strip()
                    name_parts = entity_info.split("(Type:", 1)
                    if name_parts:
                        entity_name = name_parts[0].strip()
                        entities.append(entity_name)
                    
        return entities
    
    def save_ezd_file(self, output_path):
        """
        Save the current EZD file to a new location
        
        Args:
            output_path: Path to save the file
            
        Returns:
            bool: Success state
        """
        if self.current_ezd_file is None:
            self.logger.error("No EZD file currently open")
            return False
            
        self.logger.info(f"Saving EZD file to: {output_path}")
        result = self._run_bridge_command(["save", output_path])
        
        if "saved successfully" in result.get("output", "").lower():
            return True
        return False
    
    def process_data(self, ezd_template, data_items, output_path=None):
        """
        Process a batch of data by updating the template and marking
        
        Args:
            ezd_template: Path to the EZD template file
            data_items: List of dictionaries. Each dict should contain entity names as keys and text values
            output_path: Optional path to save the resulting EZD file
            
        Returns:
            dict: Processing statistics
        """
        if not os.path.exists(ezd_template):
            self.logger.error(f"Template file not found: {ezd_template}")
            return {"success": False, "error": "Template file not found"}
            
        stats = {
            "total": len(data_items),
            "success": 0,
            "errors": 0,
            "start_time": time.time()
        }
        
        # Open the template
        if not self.open_ezd_file(ezd_template):
            return {"success": False, "error": "Failed to open template file"}
            
        # Get available entities
        available_entities = self.list_entities()
        self.logger.info(f"Available entities in template: {available_entities}")
            
        # Process each data item
        for i, data_item in enumerate(data_items):
            try:
                item_id = data_item.get("id", f"Item {i+1}")
                self.logger.info(f"Processing item {i+1}/{len(data_items)}: {item_id}")
                
                # Update each entity
                update_success = True
                for entity_name, text_value in data_item.items():
                    if entity_name != "id":  # Skip the id field
                        if entity_name in available_entities:
                            if not self.update_text(entity_name, str(text_value)):
                                self.logger.error(f"Failed to update entity: {entity_name}")
                                update_success = False
                        else:
                            self.logger.warning(f"Entity not found in template: {entity_name}")
                
                if update_success:
                    # Execute marking
                    if self.mark():
                        stats["success"] += 1
                    else:
                        self.logger.error(f"Failed to mark item: {item_id}")
                        stats["errors"] += 1
                else:
                    stats["errors"] += 1
                    
            except Exception as e:
                self.logger.error(f"Error processing item {i+1}: {str(e)}")
                stats["errors"] += 1
        
        # Save the final file if requested
        if output_path:
            self.save_ezd_file(output_path)
            
        stats["end_time"] = time.time()
        stats["duration"] = stats["end_time"] - stats["start_time"]
        
        return stats
    
    def _run_bridge_command(self, args):
        """
        Run a command through the bridge application
        
        Args:
            args: List of command arguments
            
        Returns:
            dict: Command result with output and return code
        """
        command = [self.bridge_exe_path] + args
        self.logger.debug(f"Running bridge command: {' '.join(command)}")
        
        try:
            # Run the command with UTF-8 encoding to avoid character encoding issues
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'  # Replace invalid characters instead of crashing
            )
            
            # Capture output
            stdout, stderr = process.communicate()
            
            # Log the output
            if stdout:
                self.logger.debug(f"Bridge output: {stdout}")
            if stderr:
                self.logger.error(f"Bridge error: {stderr}")
                
            return {
                "output": stdout,
                "error": stderr,
                "return_code": process.returncode,
                "success": process.returncode == 0
            }
            
        except Exception as e:
            self.logger.error(f"Error running bridge command: {str(e)}")
            return {
                "output": "",
                "error": str(e),
                "return_code": -1,
                "success": False
            }


def main():
    """Command line interface for the EZCAD Bridge"""
    import argparse
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        encoding='utf-8'
    )
    
    logger = logging.getLogger("EZCADBridge")
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="EZCAD Bridge Python Interface")
    parser.add_argument("--bridge", help="Path to EZCADBridge.exe", default=None)
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # info command
    info_parser = subparsers.add_parser("info", help="Get bridge information")
    
    # open command
    open_parser = subparsers.add_parser("open", help="Open an EZD file")
    open_parser.add_argument("ezd_file", help="Path to the EZD file")
    
    # update command
    update_parser = subparsers.add_parser("update", help="Update text entity")
    update_parser.add_argument("entity", help="Entity name")
    update_parser.add_argument("text", help="New text")
    
    # mark command
    mark_parser = subparsers.add_parser("mark", help="Execute marking")
    mark_parser.add_argument("entity", nargs="?", help="Optional entity name")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List entities")
    
    # red command
    red_parser = subparsers.add_parser("red", help="Position red light")
    red_parser.add_argument("x", type=float, help="X coordinate")
    red_parser.add_argument("y", type=float, help="Y coordinate")
    
    # save command
    save_parser = subparsers.add_parser("save", help="Save EZD file")
    save_parser.add_argument("output", help="Output file path")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Create bridge instance
    try:
        bridge = EZCADBridge(args.bridge, logger)
        
        if args.command == "info":
            result = bridge.get_bridge_info()
            print(result.get("output", "No information available"))
            
        elif args.command == "open":
            success = bridge.open_ezd_file(args.ezd_file)
            print(f"Open result: {'Success' if success else 'Failed'}")
            
        elif args.command == "update":
            success = bridge.update_text(args.entity, args.text)
            print(f"Update result: {'Success' if success else 'Failed'}")
            
        elif args.command == "mark":
            success = bridge.mark(args.entity)
            print(f"Mark result: {'Success' if success else 'Failed'}")
            
        elif args.command == "list":
            entities = bridge.list_entities()
            print("Entities:")
            for entity in entities:
                print(f"  - {entity}")
                
        elif args.command == "red":
            success = bridge.red_light(args.x, args.y)
            print(f"Red light result: {'Success' if success else 'Failed'}")
            
        elif args.command == "save":
            success = bridge.save_ezd_file(args.output)
            print(f"Save result: {'Success' if success else 'Failed'}")
            
        else:
            print("Please specify a command. Use --help for options.")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()