# knowledge/watcher.py
import logging
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class KnowledgeWatcher(FileSystemEventHandler):
    """Watches for new files and triggers processing pipeline."""
    
    def __init__(self, watch_path: Path):
        """Initialize the watcher with the path to monitor."""
        self.watch_path = watch_path
        self.observer: Optional[Observer] = None
        
    def on_created(self, event):
        """Handle new file creation events."""
        if event.is_directory:
            return
            
        logger.info(f"New file detected: {event.src_path}")
        # TODO: Trigger processing pipeline
        
    def start(self):
        """Start watching the specified directory."""
        self.observer = Observer()
        self.observer.schedule(self, str(self.watch_path), recursive=False)
        self.observer.start()
        logger.info(f"Started watching directory: {self.watch_path}")
        
    def stop(self):
        """Stop the file watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped file watcher") 