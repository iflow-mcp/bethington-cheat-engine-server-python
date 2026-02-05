#!/usr/bin/env python3

import os
import sys
import argparse
import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import Tool

# Import our modules
from server.process.manager import ProcessManager
from server.process.launcher import ApplicationLauncher
from server.utils.validators import validate_address, validate_size
from server.utils.formatters import format_process_info
from server.config.settings import ServerConfig
from server.config.whitelist import ProcessWhitelist

# Try to import Windows-specific modules (will fail on Linux)
try:
    from server.cheatengine.table_parser import CheatTableParser
    from server.cheatengine.ce_bridge import CheatEngineBridge
    CE_ENGINE_AVAILABLE = True
except ImportError as e:
    CE_ENGINE_AVAILABLE = False
    CheatTableParser = None
    CheatEngineBridge = None
    logger = logging.getLogger(__name__)
    logger.warning(f"Cheat Engine modules not available (Windows only): {e}")

import glob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import automation tools for integration
try:
    import sys
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from automation_tools import register_automation_tools
    from gui_automation.tools.mcp_tools import ALL_PYAUTOGUI_TOOLS, PyAutoGUIToolHandler
    from window_automation.tools.mcp_tools import ALL_PYWINAUTO_TOOLS, PyWinAutoToolHandler
    AUTOMATION_AVAILABLE = True
    PYAUTOGUI_AVAILABLE = True
    PYWINAUTO_AVAILABLE = True
    logger.info("Automation tools, PyAutoGUI, and PyWinAuto modules loaded successfully")
except ImportError as e:
    AUTOMATION_AVAILABLE = False
    PYAUTOGUI_AVAILABLE = False
    PYWINAUTO_AVAILABLE = False
    logger.warning(f"Automation tools not available: {e}")
except ImportError as e:
    logger.warning(f"Automation tools not available: {e}")
    AUTOMATION_AVAILABLE = False

# Parse command line arguments
parser = argparse.ArgumentParser(description="MCP Cheat Engine Server")
parser.add_argument(
    "--config", 
    default="config.json", 
    help="Configuration file path"
)
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
parser.add_argument("--read-only", action="store_true", help="Enable read-only mode")
args = parser.parse_args()

# Initialize server
mcp = FastMCP("cheat-engine-server")

# Global state
server_config = ServerConfig()
process_manager = ProcessManager()
process_whitelist = ProcessWhitelist()

# Initialize application launcher
app_launcher = None

# Initialize PyAutoGUI handler
pyautogui_handler = None
if PYAUTOGUI_AVAILABLE:
    try:
        pyautogui_handler = PyAutoGUIToolHandler()
        logger.info("PyAutoGUI handler initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize PyAutoGUI handler: {e}")
        PYAUTOGUI_AVAILABLE = False

# Initialize PyWinAuto handler
pywinauto_handler = None
if PYWINAUTO_AVAILABLE:
    try:
        pywinauto_handler = PyWinAutoToolHandler()
        logger.info("PyWinAuto handler initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize PyWinAuto handler: {e}")
        PYWINAUTO_AVAILABLE = False

# Current attached process
current_process = None

# Cheat Engine bridge (Windows only)
ce_bridge = None
if CE_ENGINE_AVAILABLE:
    try:
        ce_bridge = CheatEngineBridge()
        logger.info("Cheat Engine bridge initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Cheat Engine bridge: {e}")
        CE_ENGINE_AVAILABLE = False

# ==========================================
# PROCESS MANAGEMENT TOOLS
# ==========================================

@mcp.tool()
def list_processes() -> Dict[str, Any]:
    """List all running processes on the system"""
    try:
        processes = process_manager.list_processes()
        return {
            "success": True,
            "processes": processes,
            "count": len(processes)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def attach_to_process(process_id: int) -> Dict[str, Any]:
    """Attach to a specific process by PID"""
    global current_process
    try:
        if not process_whitelist.is_allowed(process_id):
            return {
                "success": False,
                "error": f"Process {process_id} is not in the whitelist"
            }
        
        current_process = process_manager.attach_process(process_id)
        return {
            "success": True,
            "process": current_process,
            "message": f"Successfully attached to process {process_id}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def detach_from_process() -> Dict[str, Any]:
    """Detach from the current process"""
    global current_process
    try:
        if current_process:
            process_manager.detach_process()
            current_process = None
            return {
                "success": True,
                "message": "Successfully detached from process"
            }
        return {
            "success": True,
            "message": "No process was attached"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def get_process_info(process_id: int = None) -> Dict[str, Any]:
    """Get detailed information about a process"""
    try:
        if process_id:
            info = process_manager.get_process_info(process_id)
        elif current_process:
            info = current_process
        else:
            return {
                "success": False,
                "error": "No process specified and no process currently attached"
            }
        return {
            "success": True,
            "info": info
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ==========================================
# MEMORY OPERATIONS TOOLS
# ==========================================

@mcp.tool()
def read_memory_region(address: str, size: int, data_type: str = "bytes") -> Dict[str, Any]:
    """Read memory from a specific address"""
    try:
        addr = validate_address(address)
        sz = validate_size(size)
        
        # This is a placeholder - actual memory reading requires process attachment
        # In a real implementation, this would read from the attached process
        return {
            "success": True,
            "address": hex(addr),
            "size": sz,
            "data_type": data_type,
            "data": f"Memory read from {hex(addr)} (size: {sz}, type: {data_type})",
            "note": "This is a placeholder implementation"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def get_memory_regions() -> Dict[str, Any]:
    """Get memory regions of the attached process"""
    try:
        if not current_process:
            return {
                "success": False,
                "error": "No process attached"
            }
        
        # Placeholder - actual implementation would enumerate memory regions
        return {
            "success": True,
            "regions": [
                {
                    "base_address": "0x140000000",
                    "size": 4096,
                    "protection": "PAGE_EXECUTE_READ"
                }
            ],
            "note": "This is a placeholder implementation"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def scan_memory(pattern: str, start_address: str = None, end_address: str = None) -> Dict[str, Any]:
    """Scan memory for a specific pattern"""
    try:
        # Placeholder - actual implementation would perform memory scan
        return {
            "success": True,
            "pattern": pattern,
            "results": [],
            "note": "This is a placeholder implementation"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ==========================================
# ANALYSIS TOOLS
# ==========================================

@mcp.tool()
def analyze_structure(address: str, size: int) -> Dict[str, Any]:
    """Analyze memory at address for data structures"""
    try:
        addr = validate_address(address)
        sz = validate_size(size)
        
        return {
            "success": True,
            "address": hex(addr),
            "size": sz,
            "analysis": "Structure analysis placeholder",
            "note": "This is a placeholder implementation"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def disassemble_code(address: str, size: int, architecture: str = "x64") -> Dict[str, Any]:
    """Disassemble code at a specific address"""
    try:
        addr = validate_address(address)
        sz = validate_size(size)
        
        return {
            "success": True,
            "address": hex(addr),
            "size": sz,
            "architecture": architecture,
            "disassembly": [],
            "note": "This is a placeholder implementation"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def resolve_pointer_chain(base_address: str, offsets: List[int]) -> Dict[str, Any]:
    """Resolve a multi-level pointer chain"""
    try:
        addr = validate_address(base_address)
        
        return {
            "success": True,
            "base_address": hex(addr),
            "offsets": offsets,
            "final_address": "0x0",
            "note": "This is a placeholder implementation"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ==========================================
# CHEAT ENGINE SPECIFIC TOOLS (Windows only)
# ==========================================

if CE_ENGINE_AVAILABLE:
    @mcp.tool()
    def import_cheat_table(file_path: str) -> Dict[str, Any]:
        """Import a Cheat Engine table (.CT) file"""
        try:
            if not ce_bridge:
                return {
                    "success": False,
                    "error": "Cheat Engine bridge not available"
                }
            
            parser = CheatTableParser()
            entries = parser.parse_ct_file(file_path)
            
            return {
                "success": True,
                "entries": entries,
                "count": len(entries)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp.tool()
    def execute_lua_script(script_content: str, safe_mode: bool = True) -> Dict[str, Any]:
        """Execute a Lua script (Cheat Engine)"""
        try:
            if not ce_bridge:
                return {
                    "success": False,
                    "error": "Cheat Engine bridge not available"
                }
            
            # Placeholder - actual implementation would execute Lua script
            return {
                "success": True,
                "result": "Lua script executed",
                "note": "This is a placeholder implementation"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# ==========================================
# CHEAT TABLE FILESYSTEM TOOLS
# ==========================================

@mcp.tool()
def read_file(path: str) -> str:
    """Read file contents"""
    path_obj = Path(path)

    if not path_obj.exists():
        return f"File not found: {path}"

    if not path_obj.is_file():
        return f"Path is not a file: {path}"

    try:
        with path_obj.open("r", encoding="utf-8") as f:
            content = f.read()

        return f"Contents of {path}:\n{content}"

    except UnicodeDecodeError:
        return f"File is not text or uses unsupported encoding: {path}"

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to a file"""
    path_obj = Path(path)

    try:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with path_obj.open("w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully wrote to {path}"

    except Exception as e:
        return f"Error writing to {path}: {e}"

@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List directory contents"""
    path_obj = Path(path)

    if not path_obj.exists():
        return f"Directory not found: {path}"

    if not path_obj.is_dir():
        return f"Path is not a directory: {path}"

    try:
        items = list(path_obj.iterdir())
        result = f"Contents of {path}:\n"
        for item in sorted(items):
            prefix = "DIR " if item.is_dir() else "FILE"
            result += f"{prefix}: {item.name}\n"

        return result

    except Exception as e:
        return f"Error listing directory {path}: {e}"

# ==========================================
# END CHEAT TABLE FILESYSTEM TOOLS
# ==========================================


def main():
    """Main server entry point"""
    try:
        # Initialize server configuration
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled")
        
        if args.read_only:
            logger.info("Read-only mode enabled")
        
        # Load configuration
        server_config.load_config(args.config)
        
        # Initialize whitelist
        process_whitelist.load_whitelist(server_config.get_whitelist_path())
        
        # Initialize application launcher
        global app_launcher
        app_launcher = ApplicationLauncher(process_whitelist)
        
        # Set session file for persistence (optional)
        session_file = os.path.join(os.path.dirname(server_config.get_whitelist_path()), 'launcher_session.json')
        app_launcher.set_session_file(session_file)
        logger.info("Application launcher initialized")
        
        # Register automation tools if available
        if AUTOMATION_AVAILABLE:
            try:
                automation_tools = register_automation_tools(mcp)
                logger.info(f"Registered {len(automation_tools)} automation tools")
            except Exception as e:
                logger.error(f"Failed to register automation tools: {e}")
        
        logger.info("MCP Cheat Engine Server starting...")
        
        # Run the MCP server
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if current_process:
            try:
                process_manager.detach_process()
                logger.info("Cleaned up process attachment")
            except:
                pass


if __name__ == "__main__":
    main()