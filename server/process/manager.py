"""
Process Manager Module
Handles process enumeration, attachment, and management
Cross-platform version supporting both Windows and Linux
"""

import psutil
import logging
import platform
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Detect platform
IS_WINDOWS = platform.system() == 'Windows'

# Windows-specific imports
if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes
    
    # Windows API constants
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    PROCESS_VM_WRITE = 0x0020
    PROCESS_VM_OPERATION = 0x0008
    PROCESS_ALL_ACCESS = 0x1F0FFF

@dataclass
class ProcessInfo:
    """Process information structure"""
    pid: int
    name: str
    exe_path: str
    architecture: str
    memory_usage: int
    handle: Optional[int] = None
    access_level: str = "none"

class ProcessManager:
    """Manages process attachment and operations"""
    
    def __init__(self):
        self.current_process: Optional[ProcessInfo] = None
        if IS_WINDOWS:
            self.kernel32 = ctypes.windll.kernel32
        else:
            self.kernel32 = None
        
    def list_processes(self) -> List[Dict[str, Any]]:
        """Enumerate all running processes"""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'memory_info']):
                try:
                    info = proc.info
                    if info['name'] and info['pid'] > 0:
                        # Get architecture info
                        arch = self._get_process_architecture(info['pid'])
                        
                        processes.append({
                            'pid': info['pid'],
                            'name': info['name'],
                            'exe_path': info['exe'] or 'N/A',
                            'architecture': arch,
                            'memory_usage': info['memory_info'].rss if info['memory_info'] else 0
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            logger.error(f"Error enumerating processes: {e}")
            
        return sorted(processes, key=lambda x: x['name'].lower())
    
    def _get_process_architecture(self, pid: int) -> str:
        """Determine process architecture (32-bit or 64-bit)"""
        try:
            if IS_WINDOWS:
                handle = self.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
                if not handle:
                    return "Unknown"
                
                try:
                    # Check if process is WOW64 (32-bit on 64-bit Windows)
                    is_wow64 = ctypes.wintypes.BOOL()
                    if self.kernel32.IsWow64Process(handle, ctypes.byref(is_wow64)):
                        if is_wow64.value:
                            return "x86"
                        else:
                            # Check system architecture
                            if platform.machine().endswith('64'):
                                return "x64"
                            else:
                                return "x86"
                    return "Unknown"
                finally:
                    self.kernel32.CloseHandle(handle)
            else:
                # Linux: Use /proc filesystem
                try:
                    with open(f'/proc/{pid}/exe', 'rb') as f:
                        exe_path = f.read()
                    # Check if executable path contains 32-bit indicators
                    if b'32' in exe_path or b'x86' in exe_path:
                        return "x86"
                    # Check system architecture
                    if platform.machine().endswith('64'):
                        return "x64"
                    return "x86"
                except (FileNotFoundError, PermissionError):
                    return "Unknown"
        except Exception as e:
            logger.error(f"Error getting process architecture: {e}")
            return "Unknown"
    
    def attach_process(self, pid: int) -> ProcessInfo:
        """Attach to a process"""
        try:
            proc = psutil.Process(pid)
            
            process_info = ProcessInfo(
                pid=pid,
                name=proc.name(),
                exe_path=proc.exe() or 'N/A',
                architecture=self._get_process_architecture(pid),
                memory_usage=proc.memory_info().rss,
                handle=pid if not IS_WINDOWS else None,
                access_level="full" if IS_WINDOWS else "limited"
            )
            
            self.current_process = process_info
            logger.info(f"Attached to process {pid} ({process_info.name})")
            return process_info
            
        except psutil.NoSuchProcess:
            raise Exception(f"Process {pid} not found")
        except psutil.AccessDenied:
            raise Exception(f"Access denied to process {pid}")
        except Exception as e:
            raise Exception(f"Failed to attach to process {pid}: {e}")
    
    def detach_process(self) -> bool:
        """Detach from current process"""
        try:
            if self.current_process:
                if IS_WINDOWS and self.current_process.handle:
                    self.kernel32.CloseHandle(self.current_process.handle)
                self.current_process = None
                logger.info("Detached from process")
                return True
            return False
        except Exception as e:
            logger.error(f"Error detaching from process: {e}")
            return False
    
    def get_process_info(self, pid: int) -> Dict[str, Any]:
        """Get detailed information about a process"""
        try:
            proc = psutil.Process(pid)
            
            return {
                'pid': pid,
                'name': proc.name(),
                'exe': proc.exe() or 'N/A',
                'cwd': proc.cwd() or 'N/A',
                'cmdline': proc.cmdline(),
                'create_time': proc.create_time(),
                'status': proc.status(),
                'username': proc.username(),
                'memory_info': {
                    'rss': proc.memory_info().rss,
                    'vms': proc.memory_info().vms
                },
                'cpu_percent': proc.cpu_percent(),
                'num_threads': proc.num_threads(),
                'architecture': self._get_process_architecture(pid),
                'platform': platform.system()
            }
        except psutil.NoSuchProcess:
            raise Exception(f"Process {pid} not found")
        except Exception as e:
            raise Exception(f"Failed to get process info: {e}")