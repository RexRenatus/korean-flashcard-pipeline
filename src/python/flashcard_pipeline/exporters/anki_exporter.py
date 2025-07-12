"""
Anki Format Exporter
===================

Exports flashcards in Anki-compatible format (APKG).
Supports note types, media files, and custom fields.
"""

import json
import sqlite3
import zipfile
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib
import time

from ..models import ExportConfig
from ..exceptions import ExportError

logger = logging.getLogger(__name__)


class AnkiExporter:
    """
    Anki APKG format exporter for flashcards.
    
    Features:
    - APKG package generation
    - Custom note types
    - Media file support
    - Tag preservation
    - Deck hierarchy
    - Field customization
    """
    
    # Anki collection schema version
    ANKI_SCHEMA_VERSION = 11
    
    # Default note type for Korean flashcards
    KOREAN_NOTE_TYPE = {
        'id': 1,
        'name': 'Korean Flashcard',
        'fields': [
            {'name': 'Korean', 'ord': 0},
            {'name': 'English', 'ord': 1},
            {'name': 'Romanization', 'ord': 2},
            {'name': 'Explanation', 'ord': 3},
            {'name': 'Tags', 'ord': 4}
        ],
        'templates': [{
            'name': 'Korean → English',
            'qfmt': '{{Korean}}<br><br>{{#Romanization}}<span style="color: #666; font-size: 0.9em;">{{Romanization}}</span>{{/Romanization}}',
            'afmt': '{{FrontSide}}<hr id="answer">{{English}}<br><br>{{#Explanation}}<div style="margin-top: 10px; font-size: 0.9em; color: #555;">{{Explanation}}</div>{{/Explanation}}'
        }],
        'css': """
.card {
    font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
    font-size: 20px;
    text-align: center;
    color: black;
    background-color: white;
    line-height: 1.5;
}

.korean {
    font-size: 28px;
    font-weight: bold;
    color: #0066cc;
}

.tags {
    font-size: 14px;
    color: #999;
    margin-top: 20px;
}
"""
    }
    
    def __init__(self, media_dir: Optional[Path] = None):
        """
        Initialize Anki exporter.
        
        Args:
            media_dir: Directory containing media files to include
        """
        self.media_dir = media_dir
        self.media_files = {}
        self.note_id_counter = int(time.time() * 1000)
        self.card_id_counter = int(time.time() * 1000) + 1000000
    
    def export(
        self,
        export_data: Dict[str, Any],
        config: ExportConfig
    ) -> None:
        """
        Export flashcards to Anki APKG file.
        
        Args:
            export_data: Dictionary containing flashcards and metadata
            config: Export configuration
        """
        try:
            flashcards = export_data.get('flashcards', [])
            if not flashcards:
                logger.warning("No flashcards to export")
                return
            
            # Create temporary directory for package contents
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create Anki collection database
                collection_path = temp_path / "collection.anki2"
                self._create_collection(collection_path, flashcards, config)
                
                # Create media database
                media_db_path = temp_path / "media"
                media_map = self._create_media_db(media_db_path)
                
                # Copy media files if any
                if self.media_files:
                    for idx, (original, _) in self.media_files.items():
                        media_dest = temp_path / str(idx)
                        if Path(original).exists():
                            shutil.copy2(original, media_dest)
                
                # Create APKG package
                self._create_apkg(config.output_path, temp_path)
                
                logger.info(
                    f"Exported {len(flashcards)} flashcards to Anki package: "
                    f"{config.output_path}"
                )
                
        except Exception as e:
            logger.error(f"Anki export failed: {e}")
            raise ExportError(f"Failed to export Anki package: {e}")
    
    def _create_collection(
        self,
        db_path: Path,
        flashcards: List[Dict[str, Any]],
        config: ExportConfig
    ):
        """Create Anki collection database"""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        try:
            # Create schema
            self._create_schema(conn)
            
            # Add default deck
            deck_id = 1
            deck_name = config.filters.get('deck_name', 'Korean Flashcards')
            self._add_deck(conn, deck_id, deck_name)
            
            # Add note type
            model_id = self.KOREAN_NOTE_TYPE['id']
            self._add_note_type(conn, self.KOREAN_NOTE_TYPE)
            
            # Add flashcards
            for flashcard in flashcards:
                note_id = self._add_note(conn, flashcard, model_id, deck_id)
                self._add_card(conn, note_id, model_id, deck_id)
            
            # Update collection metadata
            self._update_collection_meta(conn, len(flashcards))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _create_schema(self, conn: sqlite3.Connection):
        """Create Anki database schema"""
        # Main collection info
        conn.execute("""
            CREATE TABLE col (
                id integer PRIMARY KEY,
                crt integer NOT NULL,
                mod integer NOT NULL,
                scm integer NOT NULL,
                ver integer NOT NULL,
                dty integer NOT NULL,
                usn integer NOT NULL,
                ls integer NOT NULL,
                conf text NOT NULL,
                models text NOT NULL,
                decks text NOT NULL,
                dconf text NOT NULL,
                tags text NOT NULL
            )
        """)
        
        # Notes (facts)
        conn.execute("""
            CREATE TABLE notes (
                id integer PRIMARY KEY,
                guid text NOT NULL,
                mid integer NOT NULL,
                mod integer NOT NULL,
                usn integer NOT NULL,
                tags text NOT NULL,
                flds text NOT NULL,
                sfld text NOT NULL,
                csum integer NOT NULL,
                flags integer NOT NULL,
                data text NOT NULL
            )
        """)
        
        # Cards
        conn.execute("""
            CREATE TABLE cards (
                id integer PRIMARY KEY,
                nid integer NOT NULL,
                did integer NOT NULL,
                ord integer NOT NULL,
                mod integer NOT NULL,
                usn integer NOT NULL,
                type integer NOT NULL,
                queue integer NOT NULL,
                due integer NOT NULL,
                ivl integer NOT NULL,
                factor integer NOT NULL,
                reps integer NOT NULL,
                lapses integer NOT NULL,
                left integer NOT NULL,
                odue integer NOT NULL,
                odid integer NOT NULL,
                flags integer NOT NULL,
                data text NOT NULL
            )
        """)
        
        # Review log
        conn.execute("""
            CREATE TABLE revlog (
                id integer PRIMARY KEY,
                cid integer NOT NULL,
                usn integer NOT NULL,
                ease integer NOT NULL,
                ivl integer NOT NULL,
                lastIvl integer NOT NULL,
                factor integer NOT NULL,
                time integer NOT NULL,
                type integer NOT NULL
            )
        """)
        
        # Graves (deleted items)
        conn.execute("""
            CREATE TABLE graves (
                usn integer NOT NULL,
                oid integer NOT NULL,
                type integer NOT NULL
            )
        """)
        
        # Indexes
        conn.execute("CREATE INDEX idx_notes_mid ON notes (mid)")
        conn.execute("CREATE INDEX idx_notes_guid ON notes (guid)")
        conn.execute("CREATE INDEX idx_cards_nid ON cards (nid)")
        conn.execute("CREATE INDEX idx_cards_did ON cards (did)")
    
    def _add_deck(self, conn: sqlite3.Connection, deck_id: int, name: str):
        """Add deck to collection"""
        decks = {
            str(deck_id): {
                'id': deck_id,
                'name': name,
                'desc': '',
                'mod': int(time.time()),
                'usn': -1,
                'collapsed': False,
                'browserCollapsed': False,
                'dyn': 0,
                'conf': 1,
                'extendNew': 0,
                'extendRev': 0
            }
        }
        
        # Also add default deck
        decks['1'] = decks[str(deck_id)].copy()
        decks['1']['name'] = 'Default'
        
        return json.dumps(decks)
    
    def _add_note_type(self, conn: sqlite3.Connection, note_type: Dict[str, Any]):
        """Add note type (model) to collection"""
        model = {
            str(note_type['id']): {
                'id': note_type['id'],
                'name': note_type['name'],
                'type': 0,
                'mod': int(time.time()),
                'usn': -1,
                'sortf': 0,
                'did': None,
                'tmpls': [],
                'flds': [],
                'css': note_type['css'],
                'latexPre': '',
                'latexPost': '',
                'latexsvg': False,
                'req': [[0, 'none', [0]]]
            }
        }
        
        # Add fields
        for field in note_type['fields']:
            model[str(note_type['id'])]['flds'].append({
                'name': field['name'],
                'ord': field['ord'],
                'sticky': False,
                'rtl': False,
                'font': 'Arial',
                'size': 20,
                'media': []
            })
        
        # Add templates
        for idx, template in enumerate(note_type['templates']):
            model[str(note_type['id'])]['tmpls'].append({
                'name': template['name'],
                'ord': idx,
                'qfmt': template['qfmt'],
                'afmt': template['afmt'],
                'bqfmt': '',
                'bafmt': '',
                'did': None
            })
        
        return json.dumps(model)
    
    def _add_note(
        self,
        conn: sqlite3.Connection,
        flashcard: Dict[str, Any],
        model_id: int,
        deck_id: int
    ) -> int:
        """Add note to collection"""
        note_id = self.note_id_counter
        self.note_id_counter += 1
        
        # Generate unique ID
        guid = self._generate_guid(flashcard)
        
        # Prepare fields
        fields = [
            flashcard.get('korean', ''),
            flashcard.get('english', ''),
            flashcard.get('romanization', ''),
            flashcard.get('explanation', ''),
            ' '.join(flashcard.get('tags', []))
        ]
        
        # Join fields with separator
        flds = '\x1f'.join(str(f) for f in fields)
        
        # Sort field (first field)
        sfld = fields[0]
        
        # Checksum
        csum = self._field_checksum(sfld)
        
        # Tags
        tags = ' '.join(flashcard.get('tags', []))
        if tags:
            tags = f' {tags} '
        
        # Insert note
        conn.execute("""
            INSERT INTO notes (id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_id, guid, model_id, int(time.time()), -1,
            tags, flds, sfld, csum, 0, ''
        ))
        
        return note_id
    
    def _add_card(
        self,
        conn: sqlite3.Connection,
        note_id: int,
        model_id: int,
        deck_id: int
    ):
        """Add card for note"""
        card_id = self.card_id_counter
        self.card_id_counter += 1
        
        conn.execute("""
            INSERT INTO cards (
                id, nid, did, ord, mod, usn, type, queue, due, ivl, factor,
                reps, lapses, left, odue, odid, flags, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card_id, note_id, deck_id, 0, int(time.time()), -1,
            0, 0, 0, 0, 2500, 0, 0, 0, 0, 0, 0, ''
        ))
    
    def _update_collection_meta(self, conn: sqlite3.Connection, note_count: int):
        """Update collection metadata"""
        now = int(time.time())
        
        # Configuration
        conf = {
            'nextPos': note_count + 1,
            'estTimes': True,
            'activeDecks': [1],
            'sortType': 'noteFld',
            'timeLim': 0,
            'sortBackwards': False,
            'addToCur': True,
            'curDeck': 1,
            'newBury': False,
            'newSpread': 0,
            'dueCounts': True,
            'curModel': str(self.KOREAN_NOTE_TYPE['id']),
            'collapseTime': 1200
        }
        
        # Deck configuration
        dconf = {
            '1': {
                'id': 1,
                'name': 'Default',
                'replayq': True,
                'lapse': {'mult': 0.0, 'minInt': 1, 'delays': [10]},
                'rev': {'perDay': 200, 'ease4': 1.3, 'ivlFct': 1.0, 'maxIvl': 36500},
                'timer': 0,
                'maxTaken': 60,
                'usn': 0,
                'new': {'perDay': 20, 'delays': [1, 10], 'separate': True,
                       'ints': [1, 4, 7], 'initialFactor': 2500}
            }
        }
        
        # Insert collection row
        conn.execute("""
            INSERT INTO col (
                id, crt, mod, scm, ver, dty, usn, ls, conf,
                models, decks, dconf, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1, now, now, now, self.ANKI_SCHEMA_VERSION, 0, 0, 0,
            json.dumps(conf),
            self._add_note_type(conn, self.KOREAN_NOTE_TYPE),
            self._add_deck(conn, 1, 'Korean Flashcards'),
            json.dumps(dconf),
            json.dumps({})
        ))
    
    def _generate_guid(self, flashcard: Dict[str, Any]) -> str:
        """Generate unique ID for flashcard"""
        # Use combination of korean and english text
        text = f"{flashcard.get('korean', '')}{flashcard.get('english', '')}"
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:10]
    
    def _field_checksum(self, field: str) -> int:
        """Calculate checksum for sort field"""
        # Simple checksum used by Anki
        if not field:
            return 0
        
        # Strip HTML and get first 8 characters
        stripped = field.strip()[:8]
        
        # Calculate checksum
        csum = 0
        for char in stripped:
            csum += ord(char)
        
        return csum
    
    def _create_media_db(self, db_path: Path) -> Dict[int, str]:
        """Create media mapping file"""
        media_map = {}
        
        # Add any media files referenced in flashcards
        # This is a placeholder - actual implementation would scan
        # flashcard content for media references
        
        # Write media mapping
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(media_map, f)
        
        return media_map
    
    def _create_apkg(self, output_path: Path, content_dir: Path):
        """Create APKG zip file"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add all files from content directory
            for file_path in content_dir.iterdir():
                if file_path.is_file():
                    zf.write(file_path, file_path.name)
        
        logger.info(f"Created APKG package: {output_path}")