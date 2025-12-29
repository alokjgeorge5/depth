"""
PersonaManager - Knowledge Base Integration for Strategy Council
Loads persona configurations and knowledge base files to generate system prompts.
"""

import json
import os
from pathlib import Path


class PersonaManager:
    """Manages persona configurations and knowledge base loading."""
    
    def __init__(self, config_path="persona.json"):
        """
        Initialize PersonaManager by loading persona configurations.
        
        Args:
            config_path: Path to persona.json file (relative to this file)
        """
        self.base_dir = Path(__file__).parent
        self.config_file = self.base_dir / config_path
        self._kb_cache = {}  # Cache for knowledge base files
        
        # Load persona configurations
        if not self.config_file.exists():
            raise FileNotFoundError(
                f"Persona configuration not found: {self.config_file}\n"
                f"Expected location: {self.config_file.absolute()}"
            )
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.personas = json.load(f)
    
    def load_knowledge_base(self, persona_name):
        """
        Load the knowledge base markdown file for a specific persona.
        Uses caching to avoid re-reading files.
        
        Args:
            persona_name: Name of the persona (e.g., 'MAYA', 'ALEX')
        
        Returns:
            str: Content of the knowledge base file
        
        Raises:
            FileNotFoundError: If the knowledge base file doesn't exist
        """
        # Return cached content if available
        if persona_name in self._kb_cache:
            return self._kb_cache[persona_name]
        
        # Map persona names to knowledge base files
        kb_mapping = {
            'MAYA': 'kb_mom_test.md',
            'ALEX': 'kb_strategy.md',
            'TURING': 'kb_engineering.md',
            'MARCUS': 'kb_risk.md'
        }
        
        if persona_name not in kb_mapping:
            raise ValueError(
                f"Unknown persona: {persona_name}\n"
                f"Available personas: {list(kb_mapping.keys())}"
            )
        
        kb_file = self.base_dir / kb_mapping[persona_name]
        
        if not kb_file.exists():
            raise FileNotFoundError(
                f"Knowledge base file not found for {persona_name}: {kb_file}\n"
                f"Expected location: {kb_file.absolute()}\n"
                f"Please ensure {kb_mapping[persona_name]} exists in the backend directory."
            )
        
        with open(kb_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cache the content
        self._kb_cache[persona_name] = content
        return content
    
    def get_system_prompt(self, persona_name):
        """
        Generate a complete system prompt for the LLM.
        
        Args:
            persona_name: Name of the persona (e.g., 'MAYA', 'ALEX')
        
        Returns:
            str: Complete system prompt with role, philosophy, rules, and knowledge base
        
        Raises:
            ValueError: If persona doesn't exist
            FileNotFoundError: If knowledge base file is missing
        """
        if persona_name not in self.personas:
            raise ValueError(
                f"Persona '{persona_name}' not found in configuration.\n"
                f"Available personas: {list(self.personas.keys())}"
            )
        
        persona = self.personas[persona_name]
        kb_content = self.load_knowledge_base(persona_name)
        
        # Build the system prompt
        prompt_parts = []
        
        # ROLE
        prompt_parts.append(f"# ROLE")
        prompt_parts.append(f"You are {persona_name}, the {persona['role']}.")
        prompt_parts.append("")
        
        # CORE PHILOSOPHY
        prompt_parts.append(f"# CORE PHILOSOPHY")
        prompt_parts.append(persona['core_philosophy'])
        prompt_parts.append("")
        
        # THE ONE RULE (emphasized)
        prompt_parts.append(f"# THE ONE RULE")
        prompt_parts.append(f"**{persona['one_rule'].upper()}**")
        prompt_parts.append("")
        
        # STYLE RULES
        prompt_parts.append(f"# STYLE RULES")
        for i, rule in enumerate(persona['style_rules'], 1):
            prompt_parts.append(f"{i}. {rule}")
        prompt_parts.append("")
        
        # SOURCE MATERIAL
        prompt_parts.append(f"# SOURCE MATERIAL")
        prompt_parts.append(f"Your expertise is grounded in: {persona['source_material']}")
        prompt_parts.append("")
        
        # DEEP KNOWLEDGE
        prompt_parts.append(f"# DEEP KNOWLEDGE")
        prompt_parts.append(f"The following is your complete knowledge base. Use it to inform your responses:")
        prompt_parts.append("")
        prompt_parts.append(kb_content)
        prompt_parts.append("")
        
        # INSTRUCTION
        prompt_parts.append(f"# INSTRUCTION")
        prompt_parts.append(
            "Use the 'Thinking Process' defined at the bottom of your knowledge base "
            "before answering. Follow the step-by-step analysis framework specific to your role."
        )
        prompt_parts.append("")
        prompt_parts.append("Respond concisely (max 3-4 sentences) with concrete, actionable insights.")
        
        return "\n".join(prompt_parts)
    
    def get_all_persona_names(self):
        """Return list of all available persona names."""
        return list(self.personas.keys())


# Convenience function for backward compatibility
def get_persona_prompt(persona_name):
    """
    Get system prompt for a persona (convenience function).
    
    Args:
        persona_name: Name of the persona
    
    Returns:
        str: Complete system prompt
    """
    manager = PersonaManager()
    return manager.get_system_prompt(persona_name)


if __name__ == "__main__":
    # Test the PersonaManager
    manager = PersonaManager()
    
    print("Available personas:", manager.get_all_persona_names())
    print("\n" + "="*80 + "\n")
    
    # Test loading each persona
    for persona_name in manager.get_all_persona_names():
        print(f"Testing {persona_name}...")
        try:
            prompt = manager.get_system_prompt(persona_name)
            print(f"✓ {persona_name} prompt generated ({len(prompt)} characters)")
            print(f"First 200 chars: {prompt[:200]}...")
        except Exception as e:
            print(f"✗ {persona_name} failed: {e}")
        print()
