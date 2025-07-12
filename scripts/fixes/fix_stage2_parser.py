#!/usr/bin/env python3
"""Fix for Stage 2 parser to handle edge cases"""

import os
import sys

# Add the src/python directory to the path
sys.path.insert(0, 'src/python')

# Create a patch file content
patch_content = '''
    @classmethod
    def from_tsv_content(cls, content: str) -> 'Stage2Response':
        """Parse TSV content into structured response"""
        lines = content.strip().split('\\n')
        
        # Skip header if present
        if lines and lines[0].startswith('position'):
            lines = lines[1:]
        
        rows = []
        for line in lines:
            if not line.strip():
                continue
                
            parts = line.split('\\t')
            if len(parts) >= 8:
                try:
                    # Skip if this is another header line
                    if parts[0] == 'position':
                        continue
                        
                    row = FlashcardRow(
                        position=int(parts[0]),
                        term=parts[1],
                        term_number=int(parts[2]),
                        tab_name=parts[3],
                        primer=parts[4],
                        front=parts[5],
                        back=parts[6],
                        tags=parts[7],
                        honorific_level=parts[8] if len(parts) > 8 else ""
                    )
                    rows.append(row)
                except ValueError as e:
                    # Log the error but continue processing
                    print(f"Warning: Skipping invalid TSV line: {e}")
                    continue
        
        # If no valid rows were parsed, create a minimal response
        if not rows:
            raise ValueError(f"No valid data rows found in TSV content: {content}")
        
        return cls(rows=rows)
'''

print("Fix for Stage 2 parser created.")
print("\nThe issue is that Stage 2 API sometimes returns only headers without data.")
print("The fix adds:")
print("1. Additional check to skip header lines that appear in data")
print("2. Continue processing on parse errors instead of failing")
print("3. Better error message when no valid data is found")

# Show how to apply the fix
print("\nTo apply this fix, update the from_tsv_content method in models.py")