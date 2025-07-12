#!/usr/bin/env python3
"""
Korean Flashcard Processor - Simple CLI Tool
Process Korean vocabulary into detailed flashcards using AI
"""

import asyncio
import csv
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict
import json
from datetime import datetime

try:
    import typer
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.prompt import Prompt, IntPrompt
    from rich.table import Table
    from rich import print as rprint
    import httpx
    from pydantic import BaseModel, Field
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Initialize Rich console and Typer app
console = Console()
app = typer.Typer(
    name="flashcard-processor",
    help="Process Korean vocabulary into AI-generated flashcards"
)

# Constants
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"
DEFAULT_CONCURRENT = 5
DEFAULT_OUTPUT_FORMAT = "tsv"
API_BASE_URL = "https://openrouter.ai/api/v1"

# Simple data models
class VocabularyItem(BaseModel):
    """Input vocabulary item"""
    position: int
    term: str
    type: str = "unknown"

class ProcessingResult(BaseModel):
    """Result of processing a vocabulary item"""
    success: bool
    item: VocabularyItem
    flashcards: List[Dict] = []
    error: Optional[str] = None
    tokens_used: int = 0

class SimpleAPIClient:
    """Simplified API client for OpenRouter"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def process_item(self, item: VocabularyItem) -> ProcessingResult:
        """Process a single vocabulary item"""
        try:
            # Stage 1: Analyze the term
            stage1_prompt = f"""Analyze this Korean term and provide detailed linguistic information:
Term: {item.term}
Type: {item.type}

Provide a JSON response with:
- term_number: {item.position}
- term: the Korean term with IPA pronunciation
- ipa: IPA pronunciation
- pos: part of speech
- primary_meaning: main definition
- other_meanings: other definitions
- usage_notes: how it's used
"""
            
            stage1_response = await self._make_request(stage1_prompt)
            if not stage1_response["success"]:
                return ProcessingResult(
                    success=False,
                    item=item,
                    error=stage1_response.get("error", "Stage 1 failed")
                )
            
            # Stage 2: Create flashcards
            stage2_prompt = f"""Create memory palace flashcards for this Korean term:
{stage1_response['content']}

Create 2-3 flashcards using vivid imagery and metaphors. Include:
- Scene cards with architectural metaphors
- Usage comparison cards
- Etymology/Hanja cards if applicable

Format as TSV with columns: position, term, term_number, tab_name, primer, front, back, tags, honorific_level"""
            
            stage2_response = await self._make_request(stage2_prompt)
            if not stage2_response["success"]:
                return ProcessingResult(
                    success=False,
                    item=item,
                    error=stage2_response.get("error", "Stage 2 failed")
                )
            
            # Parse flashcards from response
            flashcards = self._parse_flashcards(stage2_response['content'])
            
            return ProcessingResult(
                success=True,
                item=item,
                flashcards=flashcards,
                tokens_used=stage1_response['tokens'] + stage2_response['tokens']
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                item=item,
                error=str(e)
            )
    
    async def _make_request(self, prompt: str) -> Dict:
        """Make API request to OpenRouter"""
        try:
            response = await self.client.post(
                f"{API_BASE_URL}/chat/completions",
                headers=self.headers,
                json={
                    "model": DEFAULT_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}"
                }
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            tokens = data.get('usage', {}).get('total_tokens', 0)
            
            return {
                "success": True,
                "content": content,
                "tokens": tokens
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_flashcards(self, content: str) -> List[Dict]:
        """Parse flashcards from API response"""
        flashcards = []
        lines = content.strip().split('\n')
        
        # Simple TSV parsing
        for line in lines[1:]:  # Skip header
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 9:
                    flashcards.append({
                        "position": parts[0],
                        "term": parts[1],
                        "term_number": parts[2],
                        "tab_name": parts[3],
                        "primer": parts[4],
                        "front": parts[5],
                        "back": parts[6],
                        "tags": parts[7],
                        "honorific_level": parts[8] if len(parts) > 8 else ""
                    })
        
        return flashcards
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

async def process_vocabulary(
    input_file: Path,
    output_file: Path,
    limit: int,
    concurrent: int,
    api_key: str
) -> None:
    """Process vocabulary items concurrently"""
    
    # Read input file
    items = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            try:
                item = VocabularyItem(
                    position=int(row.get('position', i + 1)),
                    term=row['term'],
                    type=row.get('type', 'unknown')
                )
                items.append(item)
            except Exception as e:
                console.print(f"[yellow]Skipping invalid row {i+1}: {e}[/yellow]")
    
    if not items:
        console.print("[red]No valid items found in input file![/red]")
        return
    
    console.print(f"[green]Found {len(items)} items to process[/green]")
    
    # Initialize API client
    client = SimpleAPIClient(api_key)
    
    # Process items with progress bar
    results = []
    failed_items = []
    total_tokens = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task(f"Processing {len(items)} items...", total=len(items))
        
        # Process in batches
        for i in range(0, len(items), concurrent):
            batch = items[i:i + concurrent]
            batch_results = await asyncio.gather(
                *[client.process_item(item) for item in batch],
                return_exceptions=True
            )
            
            for result in batch_results:
                if isinstance(result, Exception):
                    failed_items.append(str(result))
                elif isinstance(result, ProcessingResult):
                    if result.success:
                        results.extend(result.flashcards)
                        total_tokens += result.tokens_used
                    else:
                        failed_items.append(f"{result.item.term}: {result.error}")
                
                progress.update(task, advance=1)
    
    await client.close()
    
    # Write output file
    if results:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            # Write header
            writer.writerow([
                'position', 'term', 'term_number', 'tab_name', 
                'primer', 'front', 'back', 'tags', 'honorific_level'
            ])
            
            # Write flashcards
            for card in results:
                writer.writerow([
                    card.get('position', ''),
                    card.get('term', ''),
                    card.get('term_number', ''),
                    card.get('tab_name', ''),
                    card.get('primer', ''),
                    card.get('front', ''),
                    card.get('back', ''),
                    card.get('tags', ''),
                    card.get('honorific_level', '')
                ])
    
    # Print summary
    console.print("\n[bold green]Processing Complete![/bold green]")
    console.print(f"✓ Processed items: {len(items)}")
    console.print(f"✓ Generated flashcards: {len(results)}")
    console.print(f"✓ Failed items: {len(failed_items)}")
    console.print(f"✓ Total tokens used: {total_tokens:,}")
    console.print(f"✓ Estimated cost: ${total_tokens * 0.000003:.4f}")
    console.print(f"✓ Output saved to: {output_file}")
    
    if failed_items:
        console.print("\n[yellow]Failed items:[/yellow]")
        for error in failed_items[:5]:  # Show first 5 errors
            console.print(f"  - {error}")
        if len(failed_items) > 5:
            console.print(f"  ... and {len(failed_items) - 5} more")

@app.command()
def process(
    input_file: Optional[Path] = typer.Option(
        None,
        "--input", "-i",
        help="Input CSV file with Korean vocabulary"
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output TSV file for flashcards"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit", "-l",
        help="Number of items to process"
    ),
    concurrent: Optional[int] = typer.Option(
        None,
        "--concurrent", "-c",
        help="Number of concurrent API requests"
    )
):
    """Process Korean vocabulary into flashcards"""
    
    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENROUTER_API_KEY not found![/red]")
        console.print("Please set your API key in .env file or environment variable")
        console.print("Get your key at: https://openrouter.ai/keys")
        raise typer.Exit(1)
    
    # Interactive prompts if options not provided
    if not input_file:
        input_path = Prompt.ask(
            "📁 Enter input CSV file path",
            default="vocabulary.csv"
        )
        input_file = Path(input_path)
    
    if not input_file.exists():
        console.print(f"[red]Error: Input file '{input_file}' not found![/red]")
        raise typer.Exit(1)
    
    if not output_file:
        output_path = Prompt.ask(
            "💾 Enter output file path",
            default=f"flashcards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv"
        )
        output_file = Path(output_path)
    
    if not limit:
        limit = IntPrompt.ask(
            "🔢 How many vocabulary items to process?",
            default=10
        )
    
    if not concurrent:
        concurrent = IntPrompt.ask(
            "⚡ Concurrent processing speed (1-20)?",
            default=5
        )
        concurrent = min(max(concurrent, 1), 20)  # Limit between 1-20
    
    # Show configuration
    table = Table(title="Processing Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Input File", str(input_file))
    table.add_row("Output File", str(output_file))
    table.add_row("Items to Process", str(limit))
    table.add_row("Concurrent Requests", str(concurrent))
    table.add_row("API Model", DEFAULT_MODEL)
    
    console.print(table)
    
    # Confirm before processing
    if not typer.confirm("\n🚀 Ready to process?"):
        console.print("[yellow]Processing cancelled[/yellow]")
        raise typer.Exit(0)
    
    # Run the async processing
    console.print("\n[bold blue]Starting flashcard generation...[/bold blue]")
    asyncio.run(process_vocabulary(
        input_file=input_file,
        output_file=output_file,
        limit=limit,
        concurrent=concurrent,
        api_key=api_key
    ))

@app.command()
def test():
    """Test API connection"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENROUTER_API_KEY not found![/red]")
        raise typer.Exit(1)
    
    console.print("🔌 Testing API connection...")
    
    async def test_connection():
        client = SimpleAPIClient(api_key)
        test_item = VocabularyItem(position=1, term="테스트", type="noun")
        result = await client.process_item(test_item)
        await client.close()
        
        if result.success:
            console.print("[green]✓ API connection successful![/green]")
            console.print(f"  Tokens used: {result.tokens_used}")
        else:
            console.print(f"[red]✗ API connection failed: {result.error}[/red]")
    
    asyncio.run(test_connection())

@app.command()
def example():
    """Create an example input file"""
    example_file = Path("example_vocabulary.csv")
    
    with open(example_file, 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['position', 'term', 'type'])
        writer.writerow([1, '안녕하세요', 'phrase'])
        writer.writerow([2, '감사합니다', 'phrase'])
        writer.writerow([3, '사랑', 'noun'])
        writer.writerow([4, '가다', 'verb'])
        writer.writerow([5, '예쁘다', 'adjective'])
    
    console.print(f"[green]✓ Created example file: {example_file}[/green]")
    console.print("You can now run: flashcard-processor process -i example_vocabulary.csv")

if __name__ == "__main__":
    app()