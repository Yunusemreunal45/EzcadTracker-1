#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EZCAD Integration Module

This module integrates the Excel data processor with the EZCAD2 bridge to enable
automated laser marking based on Excel data sources.
"""

import os
import sys
import logging
import pandas as pd
import time
from pathlib import Path

from excel_handler import ExcelHandler
from ezcad_bridge import EZCADBridge

class EZCADIntegration:
    """Integrates Excel data processing with EZCAD2 marking"""
    
    def __init__(self, config_manager, logger=None):
        """
        Initialize the EZCAD integration
        
        Args:
            config_manager: Configuration manager instance
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger('EZCADAutomation.Integration')
        self.config = config_manager
        
        # Initialize components
        self.excel_handler = ExcelHandler(self.logger)
        
        # Initialize bridge
        self.bridge = None
        self._init_bridge()
    
    def _init_bridge(self):
        """Initialize the EZCAD Bridge component"""
        try:
            bridge_exe = self.config.get('Paths', 'ezcad_bridge_exe', fallback=None)
            self.bridge = EZCADBridge(bridge_exe, self.logger)
            self.logger.info("EZCAD Bridge initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize EZCAD Bridge: {str(e)}")
            self.bridge = None
    
    def process_excel_file(self, excel_file, ezd_template, output_path=None, entity_mappings=None):
        """
        Process Excel data and send to EZCAD for marking
        
        Args:
            excel_file: Path to Excel file with data
            ezd_template: Path to EZD template file
            output_path: Optional path to save the resulting EZD file
            entity_mappings: Optional dict mapping Excel columns to EZD entity names
            
        Returns:
            dict: Processing statistics
        """
        if not self.bridge:
            self.logger.error("EZCAD Bridge not initialized")
            return {"success": False, "error": "EZCAD Bridge not initialized"}
            
        if not os.path.exists(excel_file):
            self.logger.error(f"Excel file not found: {excel_file}")
            return {"success": False, "error": "Excel file not found"}
            
        if not os.path.exists(ezd_template):
            self.logger.error(f"EZD template file not found: {ezd_template}")
            return {"success": False, "error": "EZD template file not found"}
            
        # Load Excel data
        df = self.excel_handler.load_excel(excel_file)
        if df is None:
            return {"success": False, "error": "Failed to load Excel file"}
            
        # Get column mappings
        if entity_mappings is None:
            # Default mapping: use column names as entity names
            entity_mappings = {col: col for col in df.columns}
            
        # Process batch
        self.logger.info(f"Processing {len(df)} rows from Excel")
        
        # Convert DataFrame rows to list of dictionaries
        data_items = []
        for _, row in df.iterrows():
            item = {"id": str(row.get("ID", f"Row {_ + 1}"))}
            for excel_col, entity_name in entity_mappings.items():
                if excel_col in row:
                    item[entity_name] = row[excel_col]
            data_items.append(item)
            
        # Process data through bridge
        start_time = time.time()
        result = self.bridge.process_data(ezd_template, data_items, output_path)
        
        # Add processing statistics
        result["total_rows"] = len(df)
        result["duration"] = time.time() - start_time
        
        # Update Excel with processing status
        if self.config.getboolean('Settings', 'update_excel_status', fallback=True):
            try:
                processed_rows = list(range(len(df)))  # All rows processed
                self.excel_handler.save_processed_status(processed_rows)
                self.logger.info(f"Updated processing status in Excel file")
            except Exception as e:
                self.logger.error(f"Failed to update Excel status: {str(e)}")
                
        return result
    
    def list_entities_in_template(self, ezd_template):
        """
        List all entities in an EZD template file
        
        Args:
            ezd_template: Path to EZD template file
            
        Returns:
            list: List of entity names
        """
        if not self.bridge:
            self.logger.error("EZCAD Bridge not initialized")
            return []
            
        if not os.path.exists(ezd_template):
            self.logger.error(f"EZD template file not found: {ezd_template}")
            return []
            
        # Open the template
        if not self.bridge.open_ezd_file(ezd_template):
            self.logger.error(f"Failed to open template: {ezd_template}")
            return []
            
        # Get entities
        entities = self.bridge.list_entities()
        return entities
        
    def test_integration(self, ezd_template):
        """
        Test the integration by opening a template and listing entities
        
        Args:
            ezd_template: Path to EZD template file
            
        Returns:
            bool: Success state
        """
        if not self.bridge:
            self.logger.error("EZCAD Bridge not initialized")
            return False
            
        # Get bridge info
        info = self.bridge.get_bridge_info()
        self.logger.info(f"Bridge info: {info}")
        
        # Try to open template
        if not os.path.exists(ezd_template):
            self.logger.error(f"EZD template file not found: {ezd_template}")
            return False
            
        if not self.bridge.open_ezd_file(ezd_template):
            self.logger.error(f"Failed to open template: {ezd_template}")
            return False
            
        # List entities
        entities = self.bridge.list_entities()
        self.logger.info(f"Entities in template: {entities}")
        
        return True


def main():
    """Command line interface for EZCAD Integration"""
    import argparse
    from config_manager import ConfigManager
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger("EZCADIntegration")
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="EZCAD Integration Tool")
    parser.add_argument("--config", help="Path to config file", default="ezcad_config.ini")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # test command
    test_parser = subparsers.add_parser("test", help="Test integration")
    test_parser.add_argument("template", help="Path to EZD template")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List entities in template")
    list_parser.add_argument("template", help="Path to EZD template")
    
    # process command
    process_parser = subparsers.add_parser("process", help="Process Excel data")
    process_parser.add_argument("excel", help="Path to Excel file")
    process_parser.add_argument("template", help="Path to EZD template")
    process_parser.add_argument("--output", help="Output path for resulting EZD file")
    process_parser.add_argument("--mappings", help="JSON file with column to entity mappings")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Load config
    config = ConfigManager(args.config)
    
    # Create integration instance
    integration = EZCADIntegration(config, logger)
    
    if args.command == "test":
        success = integration.test_integration(args.template)
        print(f"Integration test: {'Success' if success else 'Failed'}")
        
    elif args.command == "list":
        entities = integration.list_entities_in_template(args.template)
        print("Template entities:")
        for entity in entities:
            print(f"  - {entity}")
            
    elif args.command == "process":
        # Load mappings if provided
        mappings = None
        if args.mappings:
            import json
            try:
                with open(args.mappings, 'r') as f:
                    mappings = json.load(f)
            except Exception as e:
                print(f"Error loading mappings file: {str(e)}")
                return
                
        result = integration.process_excel_file(args.excel, args.template, args.output, mappings)
        print(f"Processing result: {'Success' if result.get('success', False) else 'Failed'}")
        print(f"Processed {result.get('success', 0)}/{result.get('total', 0)} items")
        print(f"Duration: {result.get('duration', 0):.2f} seconds")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
            
    else:
        print("Please specify a command. Use --help for options.")


if __name__ == "__main__":
    main()