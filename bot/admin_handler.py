import os
from datetime import datetime
from pathlib import Path

class AdminHandler:
    """
    SINGLE RESPONSIBILITY: Admin system prompt management
    
    Responsibilities:
    - Password verification
    - System prompt atomic file operations
    - Backup creation with timestamps
    - Admin state management per user
    
    PRESERVE EXACT: Current 3-state flow (idle → await_pwd → await_prompt)
    """
    
    def __init__(self, sys_password: str):
        self.sys_password = sys_password
        self.admin_states: dict[int, str] = {}  # EXACT COPY: Current state management
        
    def handle_sys_command(self, user_id: int) -> str:
        """EXACT COPY: Current /sys command logic"""
        self.admin_states[user_id] = 'await_pwd'
        return "Enter password:"
        
    def handle_admin_message(self, user_id: int, message: str) -> tuple[bool, str]:
        """
        EXACT COPY: Current admin flow interception logic
        Returns (is_admin_message, response)
        """
        admin_state = self.admin_states.get(user_id, 'idle')
        
        if admin_state == 'await_pwd':
            if message == self.sys_password:
                self.admin_states[user_id] = 'await_prompt'
                return (True, 'Password accepted. Send new system prompt:')
            else:
                self.admin_states[user_id] = 'idle'
                return (True, 'Incorrect password. Abort.')
                
        elif admin_state == 'await_prompt':
            self._save_new_system_prompt(message)
            self.admin_states[user_id] = 'idle'
            return (True, 'New system prompt saved.')
            
        return (False, '')  # Not an admin message
        
    def _save_new_system_prompt(self, prompt_text: str):
        """EXACT COPY: Current atomic file operations with backup"""
        prompt_dir = Path('prompts')
        prompt_dir.mkdir(exist_ok=True)
        target = prompt_dir / 'system_prompt.txt'
        if target.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            target.rename(prompt_dir / f'system_prompt_{timestamp}.txt')  # Backup
        # Write new prompt
        tmp_file = prompt_dir / f'.tmp_{os.getpid()}'
        tmp_file.write_text(prompt_text, encoding='utf-8')
        tmp_file.replace(target)  # Atomic replace 